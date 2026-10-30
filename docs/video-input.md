# Lectura progresiva de vídeo — T06

Primer bloque de T06, autorizado el 30/10/2026. No completa RF-03: todavía no
ejecuta el detector, dibuja cajas ni decide claridad o exposición temporal.

## Ejecutar

Se reutiliza el entorno de `requirements-tools.txt`, con OpenCV. FFprobe debe
estar disponible en PATH; las pruebas de integración también necesitan FFmpeg.
No se instalaron dependencias nuevas en este bloque.

```powershell
.\.venv\Scripts\python.exe scripts/inspect_video.py "ruta/al/video.mp4"
.\.venv\Scripts\python.exe scripts/inspect_video.py "ruta/al/video.mp4" --max-duration-seconds 60 --max-pixels 2073600
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Los límites del segundo ejemplo son ilustrativos y opcionales, no límites de
producto acordados. Una entrada inválida devuelve código 2 sin informe de éxito.
El informe JSON solo se imprime después de una lectura completa validada.

## Reutilizar la lectura

```python
from inspect_video import open_video

with open_video(video_path) as (metadata, frames):
    for frame in frames:
        # Consume this image before requesting the next frame.
        image = frame.image
        timestamp = frame.timestamp_seconds
```

El lector entrega una imagen BGR por vez, índice desde cero, PTS de origen,
timestamp relativo al primer fotograma y duración de fotograma si está declarada.
El consumidor no debe acumular imágenes si quiere mantener memoria acotada.
Salir del contexto, incluso tras un `break`, libera ambos decodificadores.

Los timestamps proceden de `best_effort_timestamp_time` de FFprobe. No se calculan
como índice/FPS: se preservan huecos de frecuencia variable. Se rechazan tiempos
ausentes, no finitos, repetidos o decrecientes. El timestamp relativo normaliza
el primer frame a cero; el PTS original se conserva para trazabilidad.

La duración procede de la pista de vídeo o, si falta, del contenedor, con esa
procedencia indicada. La duración del contenedor puede incluir audio más largo;
este dato aún no constituye el contrato temporal de T11. No se acreditan segundos
de exposición ni se decide cómo tratar el último frame en este bloque.

OpenCV decodifica las imágenes y FFprobe decodifica los tiempos en paralelo.
Esto permite comprobar que ambos producen el mismo número de fotogramas, a
cambio de trabajo de decodificación duplicado. También se contrasta el conteo
de la cabecera cuando existe y se rechazan errores de FFprobe. No se afirma
compatibilidad con todos los contenedores, pistas múltiples o codecs.

## Verificación del bloque

- 8 pruebas nuevas con vídeos sintéticos locales: CFR, VFR con huecos, inicio a
  2 segundos, entrada inexistente/inválida/solo audio, límites explícitos, salida
  anticipada, fallo de CLI y corrupción del flujo.
- 24 pruebas del repositorio correctas en total.
- Los cinco vídeos locales se decodificaron completos: 5.459 fotogramas,
  218,36 segundos de contenido y unos 88,76 segundos de ejecución acumulada.
  Todos son 1080×1920 y sus timestamps presentan pasos de 0,04 segundos.
- [Resultados por vídeo y entorno](video-input-validation-2026-10-30.json).

Los tiempos incluyen ambas lecturas y se midieron parcialmente con pruebas
ejecutándose a la vez. Son una observación local, no un benchmark de inferencia
ni una garantía de tiempo real. No se midió el pico de memoria del proceso.
No se modificaron vídeos, imágenes, etiquetas, datasets ni pesos.

Siguiente bloque pendiente de acordar: conectar un checkpoint fijo y generar
un vídeo con cajas y nombres. T10 sigue siendo requisito para aceptar la calidad
final; este avance de infraestructura no lo da por cumplido.
