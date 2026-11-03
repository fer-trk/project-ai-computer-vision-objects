"""Download a single public TikTok post without credentials or browser cookies."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

HOSTS = {'tiktok.com', 'www.tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com'}
VIDEO_PATH = re.compile(r'^/@[\w.-]+/video/(\d{15,25})/?$')


def normalize_tiktok_url(value):
    """Accept TikTok posts/share links only; discard tracking query parameters."""
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError('Pega un enlace de vídeo de TikTok válido')
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme not in ('https', 'http') or parsed.hostname not in HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError
    except ValueError:
        raise ValueError('Usa un enlace público de vídeo de tiktok.com') from None
    host, path = parsed.hostname, parsed.path
    if VIDEO_PATH.fullmatch(path) and host in ('tiktok.com', 'www.tiktok.com'):
        return 'https://www.tiktok.com'+path.rstrip('/')
    short = host in ('vm.tiktok.com', 'vt.tiktok.com') and re.fullmatch(r'/[A-Za-z0-9]+/?', path)
    shared = host in ('tiktok.com', 'www.tiktok.com') and re.fullmatch(r'/t/[A-Za-z0-9]+/?', path)
    if short or shared:
        return f'https://{host}{path}'
    raise ValueError('Pega el enlace de una publicación, no el de un perfil o una lista')


class TikTokRedirects(HTTPRedirectHandler):
    """Keep short-link resolution inside TikTok's HTTPS hosts."""
    max_redirections = 5

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            parsed = urlsplit(newurl)
            allowed = parsed.scheme == 'https' and parsed.hostname in HOSTS and parsed.port in (None, 443) and not parsed.username and not parsed.password
        except ValueError:
            allowed = False
        if not allowed:
            raise ValueError('El enlace redirige fuera de TikTok')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def resolve_tiktok_url(url):
    url = normalize_tiktok_url(url)
    if VIDEO_PATH.fullmatch(urlsplit(url).path):
        return url
    with build_opener(TikTokRedirects()).open(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=10) as response:
        canonical = normalize_tiktok_url(response.geturl())
    if not VIDEO_PATH.fullmatch(urlsplit(canonical).path):
        raise ValueError('No se pudo resolver el enlace a una publicación de vídeo')
    return canonical


def validate_metadata(info, expected_id, max_bytes, max_duration, max_pixels):
    """Reject live content and oversized media before download where metadata permits."""
    if info.get('_type') in ('playlist', 'multi_video') or info.get('is_live') or info.get('live_status') in ('is_live', 'is_upcoming'):
        raise ValueError('Solo se admiten publicaciones de vídeo, no directos ni listas')
    if str(info.get('id')) != expected_id:
        raise ValueError('La publicación resuelta no coincide con el enlace')
    duration = info.get('duration')
    if duration is None or not math.isfinite(float(duration)) or not 0 < float(duration) <= max_duration:
        raise ValueError('El vídeo supera la duración permitida o no informa su duración')
    size = info.get('filesize') or info.get('filesize_approx')
    if size and size > max_bytes:
        raise ValueError('El vídeo supera el tamaño de descarga permitido')
    width, height = info.get('width'), info.get('height')
    if width and height and width * height > max_pixels:
        raise ValueError('El vídeo supera la resolución permitida')


def hash_file(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def download_tiktok(url, folder, *, max_bytes, max_duration, max_pixels, factory=None, cache_dir=None):
    """Bound the transfer and record provenance; never request authentication."""
    folder = Path(folder).resolve()
    if (folder/'source.upload').exists():
        raise ValueError('Ya existe el vídeo de esta ejecución; no sobrescribir')
    try:
        canonical = resolve_tiktok_url(url)
    except ValueError:
        raise
    except Exception:
        raise ValueError('No se pudo resolver el enlace de TikTok. Puedes subir el archivo desde tu equipo.') from None
    video_id = VIDEO_PATH.fullmatch(urlsplit(canonical).path).group(1)
    folder.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(cache_dir).resolve() if cache_dir else None
    if cache_dir:
        cached_video, cached_record = cache_dir/f'{video_id}.mp4', cache_dir/f'{video_id}.json'
        if cached_video.is_file() and cached_record.is_file():
            metadata = json.loads(cached_record.read_text(encoding='utf-8'))
            validate_metadata(dict(id=metadata['video_id'], duration=metadata['duration_seconds'],
                                   filesize=cached_video.stat().st_size, width=metadata.get('width'), height=metadata.get('height')),
                              video_id, max_bytes, max_duration, max_pixels)
            if hash_file(cached_video) != metadata['sha256']:
                raise ValueError('La copia local del vídeo no coincide con su registro; revisa la caché')
            metadata = dict(metadata, acquisition='local_cache')
            shutil.copyfile(cached_video, folder/'source.upload')
            (folder/'source.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
            return metadata
    if factory is None:
        from yt_dlp import YoutubeDL
        factory = YoutubeDL

    def check(info, *, incomplete=False):
        if not incomplete:
            validate_metadata(info, video_id, max_bytes, max_duration, max_pixels)
        return None

    def progress(data):
        if max(data.get('downloaded_bytes') or 0, data.get('total_bytes') or 0) > max_bytes:
            raise ValueError('El vídeo supera el tamaño de descarga permitido')

    options = dict(format='best[ext=mp4]/best', outtmpl=str(folder/'tiktok.%(ext)s'),
                   noplaylist=True, allowed_extractors=['TikTok'], max_downloads=1,
                   max_filesize=max_bytes, socket_timeout=10, retries=1, fragment_retries=1,
                   cachedir=False, cookiefile=None, cookiesfrombrowser=None, usenetrc=False,
                   quiet=True, no_warnings=True, noprogress=True, match_filter=check,
                   progress_hooks=[progress], restrictfilenames=True)
    try:
        with factory(options) as downloader:
            info = downloader.extract_info(canonical, download=True)
            if not info:
                raise ValueError('TikTok no permitió descargar esta publicación')
            validate_metadata(info, video_id, max_bytes, max_duration, max_pixels)
            candidates = [Path(item['filepath']) for item in info.get('requested_downloads', []) if item.get('filepath')]
            candidates.append(Path(downloader.prepare_filename(info)))
        downloaded = next((p.resolve() for p in candidates if p.is_file()), None)
        if downloaded is None or downloaded.parent != folder:
            raise ValueError('No se recibió un archivo de vídeo válido')
        if not 0 < downloaded.stat().st_size <= max_bytes:
            raise ValueError('El vídeo supera el tamaño de descarga permitido o está vacío')
        downloaded.rename(folder/'source.upload')
        title = ''.join(c for c in (info.get('title') or f'TikTok {video_id}') if c.isprintable())[:160]
        metadata = dict(platform='TikTok', url=canonical, video_id=video_id, title=title,
                        uploader=info.get('uploader'), uploader_id=info.get('uploader_id'),
                        duration_seconds=info.get('duration'), downloaded_bytes=(folder/'source.upload').stat().st_size,
                        width=info.get('width'), height=info.get('height'), acquisition='public_download',
                        sha256=hash_file(folder/'source.upload'))
        (folder/'source.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        if cache_dir:
            try:
                cache_dir.mkdir(parents=True, exist_ok=True)
                if not cached_video.exists():
                    shutil.copyfile(folder/'source.upload', cached_video)
                    cached_record.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
            except OSError:
                pass
        return metadata
    except ValueError:
        raise
    except Exception:
        raise ValueError('TikTok no permitió descargar el vídeo. Puede estar restringido, eliminado o bloqueado temporalmente. Puedes subir el archivo desde tu equipo.') from None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Descargar una publicación pública de TikTok para analizarla')
    parser.add_argument('--url', required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--max-bytes', type=int, required=True)
    parser.add_argument('--max-duration', type=float, required=True)
    parser.add_argument('--max-pixels', type=int, required=True)
    parser.add_argument('--cache-dir', type=Path)
    args = parser.parse_args()
    try:
        metadata = download_tiktok(args.url, args.directory, max_bytes=args.max_bytes,
                                   max_duration=args.max_duration, max_pixels=args.max_pixels, cache_dir=args.cache_dir)
    except (ValueError, OSError) as error:
        parser.exit(2, f'Error de TikTok: {error}\n')
    print(json.dumps(metadata, ensure_ascii=True))
