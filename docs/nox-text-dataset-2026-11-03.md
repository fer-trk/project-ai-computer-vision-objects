# Lote inicial de texto NOX — 03/11/2026

Fernanda aprueba priorizar el texto NOX para cerrar el esencial y trabajar solo
con esa marca. El símbolo independiente se aplaza; no se añade otra marca ni se
renombra el modelo anterior como si hubiese aprendido clases nuevas.

## Resultado

Se revisaron nueve originales de la tanda de vídeos nuevos: cuatro positivos,
un negativo y cuatro excluidos por ambigüedad, movimiento o logo truncado.
Se anotaron ocho cajas de palabra NOX y se comprobaron en recortes a escala nativa.
Hay texto blanco y naranja, en espalda, pecho, manga, pantalón y calcetines.
El negativo muestra otras marcas: eso no constituye un error de anotación.

También se reinspeccionaron los 13 recortes objetivo del ensayo anterior: todos
corresponden a texto NOX. Se conservan sus cajas y decisiones de imagen completa.
La exportación nueva denomina esa clase `nox_texto`, sin alterar imágenes,
etiquetas, particiones ni checkpoints del ensayo histórico.

| Partición exploratoria | Grupos conservadores | Imágenes | Positivas | Negativas | Cajas |
| --- | --- | ---: | ---: | ---: | ---: |
| train | Milano y Kuwait 2026 provisional | 19 | 15 | 4 | 18 |
| val | Germany | 3 | 1 | 2 | 1 |
| test | Kuwait 2025 provisional | 1 | 1 | 0 | 2 |
| Total | | 23 | 17 | 6 | 21 |

Los cinco ejemplos añadidos están separados por procedencia y no se mezclan
frames del mismo grupo entre particiones. El test es una sola imagen ya
inspeccionada, seleccionada por legibilidad: **no es un test ciego ni evidencia
suficiente de generalización**. La identidad exacta de partidos/sesiones sigue
pendiente. El tamaño del lote no garantiza que el modelo vaya a mejorar.

## Revisar y reproducir

Los medios permanecen locales en `data/review/nox-text-dataset-2026-11-03/`:

- `previews/`: cajas verdes sobre cada imagen para revisión humana.
- `images/` y `labels/`: PNG originales intactos y TXT YOLO normalizados.
- `dataset.yaml`: rutas locales y clase `0: nox_texto`.
- `manifest.json`: hashes, origen, grupos, anotaciones y límites.

ZIP preparado en `data/review/nox-text-dataset-2026-11-03.zip`, con 23 imágenes,
23 etiquetas, manifiesto y YAML para `/content/nox-text-2026-11-03`. No contiene
los previews ni pesos. La inspección CRC del ZIP pasó y tiene 48 entradas.
No se subió ni entrenó en este bloque; los permisos de reutilización siguen
pendientes de documentar. La aceptación humana de las cajas está pendiente.

```powershell
.\.venv\Scripts\python.exe scripts/prepare_nox_text_dataset.py --previous-dataset "ruta/al/nox-exploratory-dataset-2026-10-26"
```

El preparador rechaza sobrescribir la carpeta o el ZIP. Comprueba hashes de
imágenes y etiquetas históricas, dimensiones, duplicados exactos y grupos
disjuntos. La conversión de las cajas a YOLO se reconstruye con tolerancia menor
de 0,001 píxel. La nueva tanda y el dataset anterior permanecen separados.

Se comprobó la carga real con `YOLODataset` de Ultralytics 8.4.189:
train 19 imágenes/18 cajas, val 3/1, test 1/2; **0 corruptos** en cada partición.
Estas son comprobaciones de preparación y carga, no métricas del detector ni
una nueva ejecución de pruebas unitarias.

[Decisiones y cajas nuevas](nox-text-review-2026-11-03.json) ·
[Manifiesto exportado sin medios](nox-text-dataset-2026-11-03.json).

Siguiente bloque: revisar las vistas y ejecutar un nuevo entrenamiento acotado;
conservar las configuraciones y evaluar también las negativas. El modelo antiguo
y su evidencia de errores no se reemplazan por esta preparación.
