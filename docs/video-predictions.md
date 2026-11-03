# Vídeo con detecciones NOX — T06

Integración autorizada el 03/11/2026 para avanzar hacia un entregable funcional.
El modelo sigue siendo experimental. No se declara completado el esencial ni RF-03
aceptado: falta revisión humana y comprobar calidad en vídeo nuevo.

## Ejecutar

Python 3.11; instalar las dependencias CPU y PyAV. FFprobe debe estar en PATH;
FFmpeg también se necesita para las pruebas. No hay entrenamiento en este flujo.

```powershell
python -m pip install -r requirements-video.txt
python scripts/predict_video.py "video.mp4" --model "best.pt" --confidence 0.25 --output "local-artifacts/resultado"
python -m unittest discover -s tests -v
```

El modelo debe ser un checkpoint local existente de una clase `nox_texto`; se carga
una sola vez. CPU, imgsz=640 e IoU de supresión=0,7 por defecto. No se sustituye
por pesos genéricos. El umbral es explícito y configurable, no una regla de claridad.
`--max-duration-seconds` y `--max-pixels` son límites opcionales del comando, no
límites finales de producto acordados. Una carpeta existente no se sobrescribe.

## Qué entrega

- `annotated.mp4`: vídeo H.264 silencioso, con cajas, ID, nombre NOX y confianza
  debajo; aviso visible de revisión. Marco fijo con bandas añadidas, sin estirar
  la imagen. En escenas densas las etiquetas pueden solaparse.
- `frames.jsonl`: una fila por fotograma, incluso sin detecciones. Coordenadas en
  la imagen original, PTS del archivo, tiempo relativo, intervalo y detecciones.
- `detections.csv`: una fila por propuesta con caja, clase, confianza, frame,
  tiempos, evidence_status=unreviewed y support=unknown. Vacío válido con cabecera
  si el modelo no produce propuestas.
- `report.json`: hashes, parámetros, versiones, conteos y tiempos medidos.
- `preview.png` y, si hay propuestas, `first-detection.png` para revisión rápida.

Se consume el vídeo progresivamente y se conserva un máximo de dos imágenes de
entrada para determinar intervalos. No se carga todo el vídeo ni se guarda una
lista de sus detecciones en RAM. PyAV codifica con PTS relativos, conservando ritmo
variable. Se reabre el MP4 y se comprueba cada timestamp frente al JSONL (tolerancia
10 microsegundos) y cada conteo antes de publicar la carpeta atómicamente.

## Validación y límites

Ocho pruebas nuevas: vídeo constante, VFR con origen distinto de cero, salidas
vacías, coherencia de exportaciones, ubicación de etiquetas, fallos de predictor,
clases/scores inválidos, límites, entradas inválidas y protección de resultados.
42 pruebas del conjunto correctas; pip check correcto. El aislamiento de Windows
bloquea algunos renombrados temporales: se verificaron fuera del aislamiento.

Demo real sobre `7700661233569041687.mp4`, completa: 215 frames, 7,166667 s,
107 propuestas en 82 frames, 62,34 s de proceso CPU (34,81 s de inferencia). Estos
conteos no son aciertos medidos. El clip contiene una imagen de train y no demuestra
generalización. Una vista fue inspeccionada; no se revisó la calidad frame a frame.
La salida conserva 215 frames y duración 7,166667 s por FFprobe.

[Registro sin medios ni pesos](video-predictions-validation-2026-11-03.json).

No se calcula exposición ni se decide si un logo es claro, hipótesis o descartable.
La confianza no sustituye esa revisión. No se asigna ropa/pala/cartel automáticamente.
Medios y pesos permanecen en carpetas ignoradas. Siguiente bloque: revisión del
vídeo e interfaz para cargarlo/consultarlo; persistencia y medición siguen abiertas.

Referencias de la nueva dependencia: [PyAV 16.1.0](https://pypi.org/project/av/16.1.0/)
y [PTS y bases de tiempo](https://pyav.basswood.io/docs/stable/api/time.html).
