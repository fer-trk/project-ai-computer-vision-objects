"""Exercise local HTTP contracts, persisted history and isolated analysis failures."""
import csv
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import Settings, create_app


class LocalApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.model = self.root / 'fixture.pt'
        self.model.write_bytes(b'controlled application test; not model weights')
        self.settings = Settings(self.model, self.root / 'data', max_upload_bytes=4096)

    @staticmethod
    def completed(job, settings, stop):
        folder = settings.data_dir / 'jobs' / job['id'] / 'result'
        folder.mkdir()
        (folder / 'annotated.mp4').write_bytes(b'controlled-video-file-for-range-test')
        (folder / 'preview.png').write_bytes(b'controlled preview')
        detections = [dict(detection_id=i+1, class_name='nox_texto', confidence=.8,
                          bbox_xyxy=[1, 2, 3, 4], evidence_status='unreviewed', support='unknown') for i in range(3)]
        frames = [dict(frame_index=0, timestamp_seconds=0, source_pts_seconds=2, detections=detections),
                  dict(frame_index=1, timestamp_seconds=.1, source_pts_seconds=2.1, detections=[])]
        (folder / 'frames.jsonl').write_text(''.join(json.dumps(frame)+'\n' for frame in frames))
        (folder / 'detections.csv').write_text('frame_index,confidence\n0,0.8\n')
        (folder / 'report.json').write_text(json.dumps(dict(complete=True, frames_processed=2,
            detection_count=3, elapsed_seconds=.2, source=dict(duration_seconds=.2))))

    def client(self, runner=None, settings=None):
        return TestClient(create_app(settings or self.settings, runner or self.completed), base_url='http://localhost')

    @staticmethod
    def submit(client, data=b'controlled upload', name='match.mp4', confidence='.25'):
        return client.post('/api/analyses', files={'video': (name, data, 'video/mp4')}, data={'confidence': confidence})

    def wait_job(self, client, job_id, status):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            response = client.get('/api/analyses/'+job_id)
            if response.json()['status'] in ('ready', 'failed'):
                self.assertEqual(response.json()['status'], status, response.json())
                return response.json()
            time.sleep(.02)
        self.fail('Analysis did not finish')

    def test_upload_persisted_detections_downloads_and_byte_ranges(self):
        with self.client() as client:
            response = self.submit(client)
            self.assertEqual(response.status_code, 202, response.text)
            job_id = response.json()['id']
            job = self.wait_job(client, job_id, 'ready')
            self.assertEqual(job['filename'], 'match.mp4')
            self.assertEqual(job['report']['detection_count'], 3)
            data = client.get(f'/api/analyses/{job_id}/detections?offset=1&limit=1').json()
            self.assertEqual(data['total'], 3)
            self.assertEqual(data['items'][0]['detection_id'], 2)
            self.assertEqual(data['items'][0]['source_pts_seconds'], 2)
            self.assertEqual(data['items'][0]['evidence_status'], 'unreviewed')
            self.assertEqual(data['items'][0]['bbox_xyxy'], [1, 2, 3, 4])
            response = client.get(f'/api/analyses/{job_id}/files/video', headers={'Range': 'bytes=0-9'})
            self.assertEqual(response.status_code, 206)
            self.assertEqual(len(response.content), 10)
            download = client.get(f'/api/analyses/{job_id}/files/csv?download=true')
            self.assertIn('attachment', download.headers['content-disposition'])
            self.assertEqual(client.get(f'/api/analyses/{job_id}/files/missing').status_code, 404)
            self.assertEqual(client.get(f'/api/analyses/{job_id}/detections?limit=101').status_code, 422)
            self.assertEqual(client.get(f'/api/analyses/{job_id}/detections?offset=-1').status_code, 422)
        with self.client() as restarted:
            self.assertEqual(restarted.get('/api/analyses').json()['items'][0]['status'], 'ready')
            self.assertEqual(restarted.get(f'/api/analyses/{job_id}/detections').json()['total'], 3)

    def test_only_one_analysis_active_and_rejected_upload_cleaned(self):
        release = threading.Event()
        def blocked(job, settings, stop):
            while not release.wait(.02):
                if stop.is_set():
                    raise ValueError('stopped')
            self.completed(job, settings, stop)
        with self.client(blocked) as client:
            job_id = self.submit(client).json()['id']
            try:
                self.assertEqual(self.submit(client).status_code, 409)
                self.assertEqual(len(list((self.settings.data_dir/'jobs').iterdir())), 1)
                self.assertEqual(client.get(f'/api/analyses/{job_id}/files/video').status_code, 409)
            finally:
                release.set()
            self.wait_job(client, job_id, 'ready')

    def test_empty_oversized_and_invalid_confidence_rejected_without_jobs(self):
        with self.client() as client:
            self.assertEqual(self.submit(client, data=b'').status_code, 422)
            self.assertEqual(self.submit(client, data=b'x'*5000).status_code, 413)
            self.assertEqual(self.submit(client, confidence='1.5').status_code, 422)
            self.assertEqual(self.submit(client, confidence='nan').status_code, 422)
            self.assertEqual(client.get('/api/analyses').json()['items'], [])
            self.assertEqual(list((self.settings.data_dir/'jobs').iterdir()), [])

    def test_missing_model_and_unknown_jobs_return_useful_errors(self):
        settings = Settings(self.root/'missing.pt', self.root/'missing-data')
        with self.client(settings=settings) as client:
            self.assertFalse(client.get('/api/config').json()['model_available'])
            self.assertEqual(self.submit(client).status_code, 503)
            self.assertEqual(client.get('/api/analyses/'+str(uuid4())).status_code, 404)
            self.assertEqual(client.get('/api/analyses/not-a-uuid').status_code, 422)

    def test_worker_failure_persisted_without_ready_artifacts(self):
        def fail(job, settings, stop):
            raise ValueError('Vídeo no válido')
        with self.client(fail) as client:
            job_id = self.submit(client).json()['id']
            job = self.wait_job(client, job_id, 'failed')
            self.assertIn('Vídeo no válido', job['error'])
            self.assertEqual(client.get(f'/api/analyses/{job_id}/files/video').status_code, 409)
            self.assertEqual(client.get(f'/api/analyses/{job_id}/detections').json()['total'], 0)

    def test_corrupt_result_rolls_back_detection_import(self):
        def corrupt(job, settings, stop):
            self.completed(job, settings, stop)
            path = settings.data_dir/'jobs'/job['id']/'result'/'report.json'
            report = json.loads(path.read_text());report['detection_count'] = 4;path.write_text(json.dumps(report))
        with self.client(corrupt) as client:
            job_id = self.submit(client).json()['id']
            self.wait_job(client, job_id, 'failed')
            self.assertEqual(client.get(f'/api/analyses/{job_id}/detections').json()['total'], 0)

    def test_restart_recovers_interrupted_jobs(self):
        with self.client() as client:
            job_id = self.submit(client).json()['id']
            self.wait_job(client, job_id, 'ready')
        with sqlite3.connect(self.settings.data_dir/'history.sqlite3') as db:
            db.execute("UPDATE analyses SET status='running' WHERE id=?", (job_id,))
        db.close()
        with self.client() as restarted:
            job = restarted.get('/api/analyses/'+job_id).json()
            self.assertEqual(job['status'], 'failed')
            self.assertIn('interrumpió', job['error'])

    def test_second_application_cannot_recover_a_live_instances_jobs(self):
        with self.client():
            with self.assertRaises(RuntimeError):
                with self.client():
                    self.fail('Second instance started')

    def test_external_origins_hosts_and_path_like_filenames(self):
        with self.client() as client:
            self.assertEqual(client.post('/api/analyses', headers={'Origin':'https://example.org'}).status_code, 403)
            self.assertEqual(client.get('/api/config', headers={'Host':'example.org'}).status_code, 400)
            response = self.submit(client, name='../outside/harmless.mp4')
            self.assertEqual(response.status_code, 202)
            self.assertEqual(response.json()['filename'], 'harmless.mp4')
            self.wait_job(client, response.json()['id'], 'ready')
            self.assertFalse((self.root/'outside').exists())

    def test_local_ui_assets_and_openapi_available(self):
        with self.client() as client:
            self.assertEqual(client.get('/').status_code, 200)
            self.assertIn('Cada aparición', client.get('/').text)
            self.assertEqual(client.get('/assets/app.js').status_code, 200)
            self.assertEqual(client.get('/assets/styles.css').status_code, 200)
            self.assertIn('/api/analyses', client.get('/openapi.json').json()['paths'])

    @unittest.skipUnless(shutil.which('ffprobe'), 'FFprobe required')
    def test_real_worker_rejects_nonvideo_before_loading_model(self):
        with TestClient(create_app(self.settings), base_url='http://localhost') as client:
            response = self.submit(client, data=b'not a video', name='invalid.mp4')
            job = self.wait_job(client, response.json()['id'], 'failed')
            self.assertIn('vídeo', job['error'].lower())


if __name__ == '__main__':
    unittest.main()
