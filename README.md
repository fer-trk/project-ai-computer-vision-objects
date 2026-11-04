# El Mozart · análisis local de NOX

Prototipo de visión artificial para detectar propuestas de logos NOX en imágenes
y vídeos de pádel. La aplicación local permite subir un vídeo, consultar el estado,
reproducir el resultado anotado y descargar CSV e informe JSON.

El modelo sigue siendo experimental. La exposición en segundos y porcentajes no
está implementada; las propuestas no equivalen a detecciones revisadas.

## Instalación y aplicación local

Requiere Python 3.11, Git y FFmpeg/FFprobe en PATH. Desde PowerShell:

```powershell
git clone https://github.com/fer-trk/project-ai-computer-vision-objects.git
cd project-ai-computer-vision-objects
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-app.txt
.\.venv\Scripts\python.exe scripts/serve_local.py --model "ruta/al/best.pt"
```

Abrir **http://127.0.0.1:8000**. El checkpoint local debe tener una clase
`nox_texto`. Los pesos y vídeos no se incluyen en Git. La aplicación no descarga
un modelo alternativo y escucha solo en este equipo.

Para la demo en vivo, seleccionar **Desde mi equipo**, cargar un vídeo local e
iniciar el análisis real. El tiempo de procesamiento depende del equipo; no se
promete análisis a la velocidad de reproducción. La descarga directa de TikTok
puede fallar: el recorrido histórico por enlace utilizó una copia local verificada.

[Instalación, límites, API e historial](docs/local-app.md) ·
[Evidencia histórica de la aplicación](docs/local-app-validation-2026-11-03.json)

## Herramientas y pruebas

Para usar solo las herramientas de datos, sin instalar el detector ni la web, crear
un entorno virtual separado e instalar `requirements-tools.txt`. En Git Bash de
Windows se activa con `source .venv/Scripts/activate`; en PowerShell se puede usar
directamente `.\.venv\Scripts\python.exe`. No combinar ambos archivos de requisitos
en un mismo entorno: tienen dependencias fijadas para alcances distintos.

La suite completa, incluida la aplicación, utiliza `requirements-app.txt`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

Las comprobaciones no sustituyen la evaluación independiente del detector. El
entrenamiento de Colab mantiene su entorno separado; no se entrena en CI.

## Estado y documentación

- Dataset real preparado: 23 imágenes y 21 cajas de `nox_texto`; permisos de
  reutilización y suficiencia de la evaluación pendientes.
- Flujo de entrenamiento y verificación T05 preparado; la nueva ejecución real
  sigue pendiente. Existe evidencia de ensayos históricos, sin calidad aceptada.
- Evaluación T10 con validación de integridad y revisión manual preparada.
- Lector y anotación de vídeo, API local e historial SQLite disponibles en el
  prototipo. La persistencia completa con recortes, la medición de exposición,
  el detector multimarca y el despliegue cloud siguen pendientes.

[Especificaciones](docs/specs.md) · [Plan](docs/plan.md) ·
[Guía T05](docs/t05-one-run.md) · [Guía T10](docs/t10-one-run-evaluation.md) ·
[Procesamiento de vídeo](docs/video-predictions.md) ·
[Kanban](https://github.com/users/fer-trk/projects/1)

## Datos y modelos

Datasets reales, vídeos, pesos y resultados permanecen fuera del repositorio.
`local-artifacts/local-app/` contiene vídeos, resultados e historial: no publicarlo.
El respaldo privado verificado cubre el dataset y sus registros; no acredita
respaldo de los vídeos originales ni de modelos históricos.

## Contribución y licencia

Usar ramas breves, Conventional Commits, revisión y pruebas antes de integrar.
No añadir secretos, `.env`, medios sin licencia ni pesos. La licencia del proyecto
y las condiciones completas de distribución de los datos siguen pendientes de
definición; no se declara una licencia que no se haya acordado.
