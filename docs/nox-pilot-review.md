# Piloto de revisión y anotación de NOX

21/10/2026. El usuario elige NOX como primera marca del nivel esencial. Referencia de tarea: T04 (datos y anotaciones). Estado: revisión inicial; no es un dataset listo para entrenar.

![Comparación a escala original con cajas propuestas](../data/review/nox-pilot-2026-10-21/nox-pilot-review.png)

La imagen compara recortes de revisión sin redimensionar. Las cajas amarillas son propuestas manuales, no resultados de un detector. Los originales conservan 1080 × 1920; las coordenadas se refieren siempre a ellos, no al recorte. No se han aplicado mejoras de nitidez ni generado detalles.

| ID | Original | Foco | Estado de claridad | Caja propuesta en píxeles |
| --- | --- | --- | --- | --- |
| N01 | [7697671396830317846, 29 s, frame 725](../data/review/player-moments-2026-10-21/frames/7697671396830317846/T03_frame_000725.png) | NOX en pecho | Categoría 1 ya aprobada por el usuario; caja pendiente de revisión | (619, 1564) a (710, 1614) |
| N02 | [7698076371569888534, 23 s, frame 575](../data/review/targeted-2026-10-21/frames/7698076371569888534/T06_frame_000575.png) | NOX en espalda baja | Propuesta de categoría 1, pendiente del usuario | (789, 1044) a (1063, 1125) |
| N03 | [7698076371569888534, 21 s, frame 525](../data/review/targeted-2026-10-21/frames/7698076371569888534/T05_frame_000525.png) | NOX con movimiento | Propuesta de categoría 2 para contrastar el criterio; el usuario puede revisarla | Sin caja positiva propuesta |

Convención: origen arriba a la izquierda; x aumenta a la derecha e y hacia abajo. Caja xyxy con bordes derecho e inferior exclusivos. Ejemplo N01: ancho 91 px, alto 50 px. El objeto que anotamos es el logo visible; no toda la camiseta ni el jugador.

## Decisiones que debe revisar el usuario

1. ¿La caja N01 contiene el logo completo con un margen pequeño adecuado?
2. ¿N02 cumple categoría 1 y su caja encierra correctamente el logo?
3. ¿N03 permite identificar NOX con claridad pese al movimiento, es solo una hipótesis o debe descartarse? La propuesta inicial no sustituye el criterio del usuario.

El archivo [nox-pilot.json](nox-pilot.json) conserva clase, soporte, original, referencia temporal, hash, dimensiones y estados separados para claridad y caja. Las nuevas cajas siguen propuestas. [review-decisions.json](review-decisions.json) conserva intacta la única aprobación previa. No se han exportado etiquetas para entrenamiento.

## Qué sigue tras la revisión

- Incorporar las decisiones explícitas, corregir cajas si hace falta y acordar la herramienta para ampliar la anotación.
- Buscar más ejemplos variados en las fuentes disponibles y comprobar si bastan; incluir negativos revisados sin NOX. No etiquetar un logo dudoso como ausencia de marca ni como positivo claro.
- Revisar los frames completos antes de exportarlos: un recorte de ejemplo no demuestra que todos los logos de la imagen estén anotados. Mantener separados equipación y soportes estáticos.
- Registrar permisos y agrupar por origen antes de particionar. N02 y N03 pertenecen a la misma escena; además, vídeos distintos del mismo partido pueden repetir tomas. Estos tres ejemplos no definen train/validation/test ni permiten estimar rendimiento.

Los PNG de revisión permanecen en data/review, excluidos de Git. Los documentos y referencias son versionables; publicar los documentos no distribuye las imágenes.
