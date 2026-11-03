"""Start the local application on loopback, with a configurable data directory."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import Settings, create_app
import uvicorn

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Abrir la aplicación local de análisis NOX')
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).resolve().parents[1]/'local-artifacts/local-app')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--max-upload-mb', type=int, default=100)
    parser.add_argument('--max-duration-seconds', type=float, default=60)
    parser.add_argument('--max-pixels', type=int, default=2073600)
    args = parser.parse_args()
    if not args.model.is_file():
        parser.error('Indica un checkpoint .pt local existente con --model')
    settings = Settings(args.model, args.data_dir, args.max_upload_mb*1024*1024,
                        args.max_duration_seconds, args.max_pixels)
    uvicorn.run(create_app(settings), host='127.0.0.1', port=args.port, workers=1)
