"""Local NOX application: persistent jobs, one isolated inference process and a browser UI."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from uuid import UUID, uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from filelock import FileLock, Timeout
from starlette.middleware.trustedhost import TrustedHostMiddleware

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).parent / 'static'
ARTIFACTS = {'video': ('annotated.mp4', 'video/mp4'), 'csv': ('detections.csv', 'text/csv'),
             'report': ('report.json', 'application/json'), 'frames': ('frames.jsonl', 'application/x-ndjson'),
             'preview': ('preview.png', 'image/png')}


def utc_now():
    """Use unambiguous timestamps in the persistent history."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Settings:
    model: Path
    data_dir: Path
    max_upload_bytes: int = 100 * 1024 * 1024
    max_duration_seconds: float = 60
    max_pixels: int = 2073600
    job_timeout_seconds: float = 900

    def __post_init__(self):
        if min(self.max_upload_bytes, self.max_duration_seconds, self.max_pixels, self.job_timeout_seconds) <= 0:
            raise ValueError('Los límites deben ser positivos')
        object.__setattr__(self, 'model', Path(self.model).resolve())
        object.__setattr__(self, 'data_dir', Path(self.data_dir).resolve())


class Jobs:
    """Persist state in SQLite and serialize inference independently of HTTP requests."""
    def __init__(self, settings, runner=None):
        self.settings = settings
        self.root = settings.data_dir
        self.jobs_dir = self.root / 'jobs'
        self.database = self.root / 'history.sqlite3'
        self.runner = runner or self.run_process
        self.guard = threading.Lock()
        self.stop = threading.Event()
        self.executor = None
        self.instance_lock = None

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def start(self):
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.instance_lock = FileLock(str(self.root / 'application.lock'))
        try:
            self.instance_lock.acquire(timeout=0)
        except Timeout as error:
            raise RuntimeError('Otra instancia ya está utilizando esta carpeta de historial') from error
        try:
            with self.connect() as db:
                db.execute('PRAGMA journal_mode=WAL')
                db.executescript('''
                    CREATE TABLE IF NOT EXISTS analyses (
                        id TEXT PRIMARY KEY, filename TEXT NOT NULL, confidence REAL NOT NULL,
                        status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                        error TEXT, report TEXT);
                    CREATE TABLE IF NOT EXISTS detections (
                        analysis_id TEXT NOT NULL REFERENCES analyses(id), frame_index INTEGER NOT NULL,
                        timestamp_seconds REAL NOT NULL, source_pts_seconds REAL NOT NULL,
                        detection_id INTEGER NOT NULL, class_name TEXT NOT NULL, confidence REAL NOT NULL,
                        bbox TEXT NOT NULL, evidence_status TEXT NOT NULL, support TEXT NOT NULL);
                    CREATE INDEX IF NOT EXISTS detection_order ON detections(analysis_id, frame_index, detection_id);
                ''')
                db.execute("UPDATE analyses SET status='failed', error=?, updated_at=? WHERE status IN ('queued','running')",
                           ('El análisis se interrumpió al cerrar la aplicación. Puedes volver a subir el vídeo.', utc_now()))
            self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='nox-analysis')
        except BaseException:
            self.instance_lock.release()
            raise

    def close(self):
        self.stop.set()
        if self.executor:
            self.executor.shutdown(wait=True, cancel_futures=True)
        if self.instance_lock:
            self.instance_lock.release()

    def cleanup_upload(self, folder):
        """Remove only an application's newly allocated UUID directory."""
        folder = Path(folder).resolve()
        if folder.parent != self.jobs_dir.resolve() or str(UUID(folder.name)) != folder.name:
            raise ValueError('Ruta de limpieza inválida')
        shutil.rmtree(folder)

    def list(self):
        with self.connect() as db:
            return [self.public(row) for row in db.execute('SELECT * FROM analyses ORDER BY created_at DESC LIMIT 50')]

    @staticmethod
    def public(row):
        data = dict(row)
        data['report'] = json.loads(data['report']) if data['report'] else None
        return data

    def get(self, job_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM analyses WHERE id=?', (job_id,)).fetchone()
        if row is None:
            raise HTTPException(404, 'No existe este análisis')
        return self.public(row)

    def submit(self, job_id, filename, confidence):
        with self.guard:
            if self.stop.is_set():
                raise HTTPException(503, 'La aplicación se está cerrando')
            with self.connect() as db:
                if db.execute("SELECT 1 FROM analyses WHERE status IN ('queued','running')").fetchone():
                    raise HTTPException(409, 'Ya hay un análisis en curso. Espera a que termine.')
                now = utc_now()
                db.execute('INSERT INTO analyses VALUES (?,?,?,?,?,?,?,?)',
                           (job_id, filename, confidence, 'queued', now, now, None, None))
            try:
                self.executor.submit(self.execute, job_id)
            except RuntimeError:
                self.fail(job_id, 'La aplicación se está cerrando. Vuelve a intentar la subida.')
                raise HTTPException(503, 'La aplicación se está cerrando')
        return self.get(job_id)

    def fail(self, job_id, message):
        with self.connect() as db:
            db.execute("UPDATE analyses SET status='failed',error=?,updated_at=? WHERE id=?", (message, utc_now(), job_id))

    def execute(self, job_id):
        with self.connect() as db:
            db.execute("UPDATE analyses SET status='running',updated_at=? WHERE id=?", (utc_now(), job_id))
        try:
            job = self.get(job_id)
            self.runner(job, self.settings, self.stop)
            result_dir = self.jobs_dir / job_id / 'result'
            report = json.loads((result_dir / 'report.json').read_text(encoding='utf-8'))
            if not report.get('complete') or not (result_dir / 'annotated.mp4').is_file():
                raise ValueError('El análisis no generó un resultado completo')
            total = frames = 0
            with self.connect() as db, (result_dir / 'frames.jsonl').open(encoding='utf-8') as lines:
                for line in lines:
                    frame = json.loads(line)
                    frames += 1
                    for detection in frame['detections']:
                        db.execute('INSERT INTO detections VALUES (?,?,?,?,?,?,?,?,?,?)',
                            (job_id, frame['frame_index'], frame['timestamp_seconds'], frame['source_pts_seconds'],
                             detection['detection_id'], detection['class_name'], detection['confidence'],
                             json.dumps(detection['bbox_xyxy']), detection['evidence_status'], detection['support']))
                        total += 1
                if frames != report['frames_processed'] or total != report['detection_count']:
                    raise ValueError('El informe y las detecciones no coinciden')
                db.execute("UPDATE analyses SET status='ready',report=?,updated_at=?,error=NULL WHERE id=?",
                           (json.dumps(report, ensure_ascii=False), utc_now(), job_id))
        except Exception as error:
            message = str(error) if isinstance(error, ValueError) else 'No se pudo completar el análisis. Vuelve a intentarlo.'
            self.fail(job_id, message[:400])

    @staticmethod
    def run_process(job, settings, stop):
        folder = settings.data_dir / 'jobs' / job['id']
        command = [sys.executable, str(ROOT / 'scripts/predict_video.py'), str(folder / 'source.upload'),
                   '--model', str(settings.model), '--output', str(folder / 'result'),
                   '--confidence', str(job['confidence']), '--max-duration-seconds', str(settings.max_duration_seconds),
                   '--max-pixels', str(settings.max_pixels)]
        environment = dict(os.environ, PYTHONUTF8='1', YOLO_OFFLINE='true')
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        with (folder / 'worker.log').open('wb') as log:
            process = subprocess.Popen(command, stdout=log, stderr=log, env=environment, creationflags=flags)
            started = time.monotonic()
            try:
                while process.poll() is None:
                    if stop.wait(.2):
                        raise ValueError('El análisis se interrumpió al cerrar la aplicación.')
                    if time.monotonic() - started > settings.job_timeout_seconds:
                        raise ValueError('Se alcanzó el tiempo máximo de análisis. Prueba con un vídeo más corto.')
                if process.returncode:
                    tail = (folder / 'worker.log').read_text(encoding='utf-8', errors='replace')[-6000:]
                    messages = [line.split('Error de análisis:', 1)[1].strip() for line in tail.splitlines() if 'Error de análisis:' in line]
                    raise ValueError(messages[-1] if messages else 'El archivo no pudo procesarse. Comprueba que sea un vídeo válido.')
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()

    def detections(self, job_id, offset, limit):
        self.get(job_id)
        with self.connect() as db:
            total = db.execute('SELECT COUNT(*) FROM detections WHERE analysis_id=?', (job_id,)).fetchone()[0]
            rows = db.execute('SELECT * FROM detections WHERE analysis_id=? ORDER BY frame_index,detection_id LIMIT ? OFFSET ?',
                              (job_id, limit, offset)).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item['bbox_xyxy'] = json.loads(item.pop('bbox'))
            items.append(item)
        return dict(items=items, total=total, offset=offset, limit=limit)


def create_app(settings, runner=None):
    """Serve a single-machine application with local-only defaults and persistent results."""
    jobs = Jobs(settings, runner)

    @asynccontextmanager
    async def lifespan(app):
        jobs.start()
        app.state.jobs = jobs
        try:
            yield
        finally:
            jobs.close()

    app = FastAPI(title='NOX · análisis local', version='0.1.0', lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]'])

    @app.middleware('http')
    async def local_requests(request: Request, call_next):
        origin = request.headers.get('origin')
        if origin and origin != f"{request.url.scheme}://{request.headers.get('host')}":
            return JSONResponse({'detail': 'Origen de solicitud no permitido'}, status_code=403)
        length = request.headers.get('content-length')
        if length:
            try:
                oversized = int(length) > settings.max_upload_bytes + 65536
            except ValueError:
                return JSONResponse({'detail': 'Tamaño de solicitud inválido'}, status_code=400)
            if oversized:
                return JSONResponse({'detail': 'El archivo supera el tamaño permitido'}, status_code=413)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.get('/', include_in_schema=False)
    async def index():
        return FileResponse(ASSETS / 'index.html')

    app.mount('/assets', StaticFiles(directory=ASSETS), name='assets')

    @app.get('/api/config')
    def config():
        return dict(model_available=settings.model.is_file(), max_upload_bytes=settings.max_upload_bytes,
                    max_duration_seconds=settings.max_duration_seconds, max_pixels=settings.max_pixels,
                    simultaneous_analyses=1, experimental=True, exposure_available=False)

    @app.get('/api/analyses')
    def history():
        return dict(items=jobs.list())

    @app.post('/api/analyses', status_code=202)
    async def upload(video: UploadFile = File(...), confidence: float = Form(.25, ge=0, le=1)):
        if not settings.model.is_file():
            raise HTTPException(503, 'El modelo no está disponible. Revisa la configuración de inicio.')
        job_id = str(uuid4())
        folder = jobs.jobs_dir / job_id
        folder.mkdir(exist_ok=False)
        filename = ''.join(c for c in Path((video.filename or 'video').replace('\\', '/')).name if c.isprintable())[:160] or 'video'
        try:
            size = 0
            with (folder / 'source.upload').open('xb') as target:
                while chunk := await video.read(1024 * 1024):
                    size += len(chunk)
                    if size > settings.max_upload_bytes:
                        raise HTTPException(413, 'El archivo supera el tamaño permitido')
                    target.write(chunk)
            if size == 0:
                raise HTTPException(422, 'Selecciona un vídeo que no esté vacío')
            return jobs.submit(job_id, filename, confidence)
        except BaseException:
            with jobs.connect() as db:
                exists = db.execute('SELECT 1 FROM analyses WHERE id=?', (job_id,)).fetchone()
            if not exists:
                jobs.cleanup_upload(folder)
            raise
        finally:
            await video.close()

    @app.get('/api/analyses/{job_id}')
    def analysis(job_id: UUID):
        return jobs.get(str(job_id))

    @app.get('/api/analyses/{job_id}/detections')
    def detections(job_id: UUID, offset: int = 0, limit: int = 50):
        if offset < 0 or not 1 <= limit <= 100:
            raise HTTPException(422, 'Paginación inválida')
        return jobs.detections(str(job_id), offset, limit)

    @app.get('/api/analyses/{job_id}/files/{artifact}')
    def artifact(job_id: UUID, artifact: str, download: bool = False):
        job = jobs.get(str(job_id))
        if job['status'] != 'ready':
            raise HTTPException(409, 'El resultado todavía no está disponible')
        if artifact not in ARTIFACTS:
            raise HTTPException(404, 'No existe ese archivo')
        filename, media = ARTIFACTS[artifact]
        path = jobs.jobs_dir / str(job_id) / 'result' / filename
        if not path.is_file():
            raise HTTPException(404, 'El archivo ya no está disponible en este equipo')
        return FileResponse(path, media_type=media, filename=filename,
                            content_disposition_type='attachment' if download else 'inline')

    return app
