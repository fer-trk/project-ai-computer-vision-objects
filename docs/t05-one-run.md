# T05 — Paquete para un único entrenamiento NOX texto

Estado: **preparado, sin entrenamiento ejecutado**. T05 no está completada; la ejecución real la hace Fer y la issue solo se actualiza con la evidencia resultante. Cuaderno: [nox_text_training.ipynb](../notebooks/nox_text_training.ipynb) (generado por `scripts/build_nox_text_notebook.py`; no editar a mano).

## Qué se entrena

Una sola clase, `nox_texto`, con el ZIP aprobado (SHA-256 `8332c1b07824f7c5a2abac9c43f17c23cc78dfa2d7c92d9953af77b4a9364254`; 23 imágenes: 19 train, 3 val, 1 test exploratorio ya inspeccionado). Configuración acordada, sin cambios: YOLO11n oficial (`yolo11n.pt`), semilla 42, `imgsz=640`, `batch=2`, máximo 50 épocas, parada tras 10 sin mejora, `mosaic=0`, `mixup=0`, sin reflejos. El dataset sintético de la PR #17 **no** se usa ni se mezcla.

## Qué añade este paquete

| Comprobación | Dónde |
| --- | --- |
| Puerta de permisos: la celda del dataset se detiene antes de pedir el ZIP si no se marca `PERMISSIONS_CONFIRMED` | cuaderno, celda `dataset-check` |
| SHA-256 del ZIP, contenido exacto, hashes de imágenes/etiquetas, dimensiones, cajas, grupos disjuntos y 19/3/1 | cuaderno (ya existía) |
| YAML y manifiesto del ZIP solo con `0: nox_texto` | cuaderno, nuevo |
| GPU CUDA obligatoria; sin GPU no se entrena | cuaderno (ya existía) |
| Parámetros acordados no editados (si difieren, falla) y `ONE_RUN.lock`: un segundo intento falla | cuaderno, nuevo |
| `error.log` con el traceback si el entrenamiento falla | cuaderno, nuevo |
| `run-manifest.json` con SHA-256 y tamaño de cada archivo, y lista de archivos obligatorios ausentes | cuaderno, nuevo |
| Verificación y empaquetado local en `local-artifacts/` | `scripts/verify_nox_text_results.py`, nuevo |

El ZIP de resultados incluye `best.pt`, `last.pt`, `args.yaml`, `results.csv`, versiones (`environment.json`, `requirements-resolved.txt`), hashes (`experiment.json` con el del checkpoint preentrenado, `evaluation.json` con el del `best.pt`, `run-manifest.json`), `dataset-manifest.json` y `error.log` si hubo error.

Límites: el bloqueo de un solo run vive junto a los resultados; sin Drive, una sesión nueva lo pierde, y la comprobación de parámetros evita ediciones accidentales, no impide que alguien cambie el cuaderno a propósito. No ejecutar otro ensayo, barrido de hiperparámetros ni repetición sin acuerdo explícito.

## Antes de gastar GPU (bloqueos a resolver)

1. **El ZIP real no está en el equipo donde se preparó este paquete** (`data/review/` no existe allí). Hay que localizar `nox-text-dataset-2026-11-03.zip`; el cuaderno rechaza cualquier archivo cuyo SHA-256 no coincida. No se regeneró ni se sustituyó por otro.
2. **Permisos de reutilización de las fuentes: pendientes de documentar.** La casilla `PERMISSIONS_CONFIRMED` solo se marca si constan por escrito; la aprobación de las cajas no es una licencia.
3. Colab gratuito con GPU asignada. Sin GPU, detenerse. No comprar unidades ni activar servicios de pago.
4. Validación offline con el ZIP real, si se quiere antes de abrir Colab: `python scripts/validate_nox_text_notebook.py ruta/al/zip` (necesita `nbformat`, que no está en los requisitos fijados). **No se ejecutó con el ZIP real**; este paquete se probó con un ZIP de ejemplo.

## Pasos para Fer

1. Subir `notebooks/nox_text_training.ipynb` a Colab y elegir **Entorno de ejecución → GPU** (gratuita).
2. Ejecutar las celdas **en orden**. En la celda del dataset, marcar `PERMISSIONS_CONFIRMED` solo si procede y subir el ZIP aprobado. Opcional: `USE_DRIVE = True` en la celda de configuración para conservar resultados y el bloqueo tras una desconexión.
3. Ejecutar **una vez** entrenamiento y evaluación. No cambiar parámetros ni mirar el test para decidir nada.
4. Ejecutar la última celda aunque haya fallado: descarga `nox-text-<fecha>-results.zip`. Guardar también el cuaderno ejecutado (**Archivo → Descargar → .ipynb**).
5. En local, desde la raíz del repositorio:

   ```powershell
   .\.venv\Scripts\python.exe scripts/verify_nox_text_results.py "C:\ruta\nox-text-AAAAMMDD-HHMMSS-results.zip"
   ```

   Comprueba CRC, hashes del manifiesto, archivos obligatorios y que `args.yaml` coincide con lo acordado; verifica que el destino esté ignorado por Git y desempaqueta en `local-artifacts/nox-text-runs/<run>/` (nunca sobrescribe) con un `verification.json`. Si `complete` es `false`, revisar `missing_required` y `error.log`.
6. Probar el modelo en una imagen con el predictor existente (el umbral no tiene valor por defecto; 0.25 es solo el valor diagnóstico del cuaderno, no un umbral aprobado):

   ```powershell
   .\.venv\Scripts\python.exe scripts/predict_image.py "ruta\imagen.png" --checkpoint "local-artifacts\nox-text-runs\<run>\train\weights\best.pt" --output "local-artifacts\predictions\<nombre>" --confidence 0.25
   ```

   La salida debe quedar en `local-artifacts/` o `data/review/`. Una detección sin revisar no demuestra exposición, y sin detecciones no se prueba que el logo falte.
7. Registrar en la issue #5 el identificador del run, los hashes y las métricas **tal cual**, junto con las cajas revisadas a escala nativa y los fallos. Las métricas de validación (un solo positivo) son inestables y el test es una imagen ya inspeccionada: no declarar el nivel esencial ni confiabilidad con este resultado. Aceptar o descartar el modelo es una decisión posterior de Fer.

No subir a Git imágenes, ZIP, pesos ni resultados; `local-artifacts/` está excluido.
