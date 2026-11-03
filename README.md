# El Mozart · análisis local de NOX

Prototipo para pegar enlaces de TikTok o subir vídeos, consultar el estado del análisis, reproducir propuestas
NOX y descargar resultados. Modelo experimental: la exposición todavía no se calcula.

## Ejecutar la aplicación

La aplicación está en la rama `feat/local-web-app`. Tras clonar o actualizar el repo:

```powershell
git fetch origin
git switch feat/local-web-app
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-app.txt
.\.venv\Scripts\python.exe scripts/serve_local.py --model "ruta/al/best.pt"
```

Abrir **http://127.0.0.1:8000**. Requiere Python 3.11, FFprobe en PATH y un checkpoint
local de una clase `nox_texto`. Los pesos y vídeos no están incluidos en Git; para
el ensayo actual se utilizan `train/weights/best.pt` del ZIP
`nox-full-20261103-112639-results.zip` entregado por Fernanda.

Pegar un enlace público y pulsar **Analizar TikTok**. La aplicación obtiene el vídeo
y ejecuta el análisis; reutiliza una copia local verificada si ya existe. La descarga
depende de TikTok: en la prueba del 03/11 rechazó una descarga nueva, por lo que se
mantiene **Desde mi equipo** como alternativa. El flujo por enlace se verificó con
una copia local de los vídeos ya utilizados, sin afirmar que se descargó de nuevo.

[Instalación, límites, API y persistencia](docs/local-app.md) ·
[Procesamiento de vídeo](docs/video-predictions.md) ·
[Especificaciones](docs/specs.md) · [Kanban](https://github.com/users/fer-trk/projects/1)

## Comprobaciones

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

Los datos se conservan por defecto en `local-artifacts/local-app/`. No publicar esa
carpeta: contiene vídeos, resultados e historial. El servidor funciona en este equipo;
la publicación online y la aceptación del modelo siguen pendientes.
