"""Check TikTok URL boundaries, download limits, cache provenance and API persistence."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import Jobs, Settings, create_app
from scripts.download_tiktok import TikTokRedirects, download_tiktok, normalize_tiktok_url, validate_metadata

URL = 'https://www.tiktok.com/@premierpadel/video/7700661233569041687'
VIDEO_ID = '7700661233569041687'


class TikTokDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root/'job'

    def factory(self, options):
        self.assertTrue(options['noplaylist'])
        self.assertIsNone(options['cookiefile']); self.assertIsNone(options['cookiesfrombrowser'])
        folder = self.folder
        class Downloader:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def extract_info(self, url, download=True):
                self.info = dict(id=VIDEO_ID, duration=7.17, width=1080, height=1920, title='Video de prueba', uploader='Premier Padel')
                options['match_filter'](self.info, incomplete=False)
                options['progress_hooks'][0](dict(downloaded_bytes=10, total_bytes=10))
                path = folder/'tiktok.mp4'; path.write_bytes(b'0123456789')
                self.info['requested_downloads'] = [dict(filepath=str(path))]
                return self.info
            def prepare_filename(self, info): return str(folder/'tiktok.mp4')
        return Downloader()

    def download(self, **kwargs):
        return download_tiktok(URL, self.folder, max_bytes=100, max_duration=60, max_pixels=2073600, factory=self.factory, **kwargs)

    def test_normalizes_posts_and_share_links_without_tracking(self):
        self.assertEqual(normalize_tiktok_url(URL+'/?_t=tracking#fragment'), URL)
        self.assertEqual(normalize_tiktok_url('https://vm.tiktok.com/AbCd/?x=1'), 'https://vm.tiktok.com/AbCd/')
        self.assertEqual(normalize_tiktok_url('https://www.tiktok.com/t/AbCd/'), 'https://www.tiktok.com/t/AbCd/')

    def test_rejects_other_hosts_credentials_ports_profiles_and_nonvideo_paths(self):
        for url in ['http://127.0.0.1/video/123', 'https://www.tiktok.com.evil.example/@x/video/'+VIDEO_ID,
                    'https://user:secret@www.tiktok.com/@x/video/'+VIDEO_ID,
                    'https://www.tiktok.com:8000/@x/video/'+VIDEO_ID,
                    'file:///etc/passwd', 'https://www.tiktok.com/@person',
                    'https://www.tiktok.com/@person/photo/'+VIDEO_ID, 'https://www.tiktok.com/redirect?url=http://localhost']:
            with self.subTest(url=url), self.assertRaises(ValueError): normalize_tiktok_url(url)

    def test_short_links_cannot_redirect_outside_tiktok(self):
        with self.assertRaises(ValueError):
            TikTokRedirects().redirect_request(None, None, 302, 'Found', {}, 'http://127.0.0.1/private')
        with self.assertRaises(ValueError):
            TikTokRedirects().redirect_request(None, None, 302, 'Found', {}, 'https://evil.example/video')

    def test_metadata_rejects_live_wrong_id_and_excessive_duration_size_resolution(self):
        base = dict(id=VIDEO_ID, duration=7, width=100, height=100)
        for changed in [dict(is_live=True), dict(id='other'), dict(duration=61), dict(duration=None),
                        dict(filesize=101), dict(width=3000, height=3000), dict(_type='playlist')]:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                validate_metadata(dict(base, **changed), VIDEO_ID, 100, 60, 2073600)

    def test_controlled_download_records_hash_and_cache_reuse_without_network(self):
        cache = self.root/'cache'
        metadata = self.download(cache_dir=cache)
        self.assertEqual(metadata['acquisition'], 'public_download')
        self.assertEqual(metadata['sha256'], hashlib.sha256(b'0123456789').hexdigest())
        self.folder = self.root/'second-job'
        with patch('yt_dlp.YoutubeDL', side_effect=AssertionError('Cache must not make requests')):
            reused = download_tiktok(URL, self.folder, max_bytes=100, max_duration=60, max_pixels=2073600, cache_dir=cache)
        self.assertEqual(reused['acquisition'], 'local_cache')
        self.assertEqual((self.folder/'source.upload').read_bytes(), b'0123456789')

    def test_finished_download_is_not_reported_as_failed_by_the_yt_dlp_counter(self):
        """yt-dlp raises MaxDownloadsReached after a finished download when max_downloads is set."""
        from yt_dlp.utils import MaxDownloadsReached

        def counting(options):
            self.assertEqual(options['playlist_items'], '1')
            downloader = self.factory(options)
            original = downloader.extract_info
            def extract_info(url, download=True):
                info = original(url, download=download)
                if options.get('max_downloads') == 1:
                    raise MaxDownloadsReached()
                return info
            downloader.extract_info = extract_info
            return downloader
        metadata = download_tiktok(URL, self.folder, max_bytes=100, max_duration=60, max_pixels=2073600, factory=counting)
        self.assertEqual(metadata['video_id'], VIDEO_ID)
        self.assertEqual(metadata['acquisition'], 'public_download')
        self.assertTrue((self.folder/'source.upload').is_file())

    def test_corrupt_cache_and_existing_destination_are_rejected(self):
        cache = self.root/'cache'; self.download(cache_dir=cache)
        with self.assertRaises(ValueError): self.download(cache_dir=cache)
        (cache/f'{VIDEO_ID}.mp4').write_bytes(b'corrupt')
        self.folder = self.root/'second-job'
        with self.assertRaisesRegex(ValueError, 'no coincide'): self.download(cache_dir=cache)

    def test_failed_network_reports_fallback_without_fake_result(self):
        def fail(options): raise RuntimeError('controlled network failure')
        with self.assertRaisesRegex(ValueError, 'subir el archivo'):
            download_tiktok(URL, self.folder, max_bytes=100, max_duration=60, max_pixels=2073600, factory=fail)
        self.assertFalse((self.folder/'source.upload').exists())


class TikTokApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.model = self.root/'fixture.pt'; self.model.write_bytes(b'controlled fixture')
        self.settings = Settings(self.model, self.root/'data')

    @staticmethod
    def empty_result(job, settings, stop):
        folder = settings.data_dir/'jobs'/job['id']/'result'; folder.mkdir()
        (folder/'annotated.mp4').write_bytes(b'controlled placeholder')
        (folder/'frames.jsonl').write_text(json.dumps(dict(frame_index=0, timestamp_seconds=0, source_pts_seconds=0, detections=[]))+'\n')
        (folder/'report.json').write_text(json.dumps(dict(complete=True, frames_processed=1, detection_count=0,
                                                        source=dict(duration_seconds=.1), elapsed_seconds=.1)))

    def test_link_submission_is_persisted_and_old_database_history_preserved(self):
        self.settings.data_dir.mkdir()
        database = self.settings.data_dir/'history.sqlite3'
        db = sqlite3.connect(database)
        with db:
            db.execute('CREATE TABLE analyses (id TEXT PRIMARY KEY,filename TEXT,confidence REAL,status TEXT,created_at TEXT,updated_at TEXT,error TEXT,report TEXT)')
            db.execute("INSERT INTO analyses VALUES (?,?,?,?,?,?,?,?)", (str(uuid4()), 'old.mp4', .25, 'failed', '2026-01-01', '2026-01-01', 'old test', None))
        db.close()
        with TestClient(create_app(self.settings, self.empty_result), base_url='http://localhost') as client:
            response = client.post('/api/tiktok', json=dict(url=URL+'?x=tracking', confidence=.25))
            self.assertEqual(response.status_code, 202, response.text)
            job = response.json(); self.assertEqual(job['source_url'], URL); self.assertEqual(job['source_kind'], 'tiktok')
            jobs = client.get('/api/analyses').json()['items']
            self.assertEqual(len(jobs), 2); self.assertEqual(next(j for j in jobs if j['filename']=='old.mp4')['source_kind'], 'upload')
            self.assertEqual(client.post('/api/tiktok', json=dict(url='https://localhost')).status_code, 422)
            self.assertEqual(client.post('/api/tiktok', json=dict(url=URL, confidence=2)).status_code, 422)

    def test_download_stage_and_source_metadata_are_kept_in_report(self):
        jobs = Jobs(self.settings); jobs.start(); self.addCleanup(jobs.close)
        calls = []
        def command(command, log, timeout, stop):
            calls.append(command)
            folder = log.parent
            if log.name == 'download.log':
                self.assertEqual(jobs.get(job_id)['status'], 'downloading')
                (folder/'source.upload').write_bytes(b'downloaded fixture')
                (folder/'source.json').write_text(json.dumps(dict(title='TikTok de prueba', url=URL, acquisition='local_cache')))
            else:
                self.assertEqual(jobs.get(job_id)['status'], 'running')
                self.empty_result(dict(id=job_id), self.settings, stop)
        job_id = str(uuid4()); (jobs.jobs_dir/job_id).mkdir()
        now = '2026-11-03T00:00:00Z'
        with jobs.connect() as db:
            db.execute('INSERT INTO analyses VALUES (?,?,?,?,?,?,?,?,?,?)', (job_id, 'TikTok', .25, 'queued', now, now, None, None, 'tiktok', URL))
        with patch.object(jobs, 'run_command', side_effect=command): jobs.execute(job_id)
        result = jobs.get(job_id)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['filename'], 'TikTok de prueba')
        self.assertEqual(result['report']['source']['publication']['acquisition'], 'local_cache')
        self.assertEqual(len(calls), 2)


if __name__ == '__main__': unittest.main()
