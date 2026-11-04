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
| Entorno validado antes de subir datos, preparar el run y entrenar; versión y GPU comprobadas tras la instalación | primeras dos celdas; [guía del entorno](colab-env-check.md) |
| Parámetros acordados no editados (si difieren, falla) y `ONE_RUN.lock`: un segundo intento falla | cuaderno, nuevo |
| Umbral y motivo obligatorios antes de entrenar; se guardan y reutilizan antes de mostrar predicciones del test | cuaderno, `experiment-config` |
| `TRAIN_STARTED.lock`: no repetir la celda de entrenamiento aunque el intento falle antes de crear `train/` | cuaderno, `train` |
| `error.log` con el traceback si el entrenamiento falla | cuaderno, nuevo |
| `run-manifest.json` con SHA-256 y tamaño de cada archivo, y lista de archivos obligatorios ausentes | cuaderno, nuevo |
| Verificación local del paquete, configuración, identidad del dataset/modelo y carga CPU de `best.pt` y `last.pt` | `scripts/verify_nox_text_results.py` |

El ZIP de resultados incluye `best.pt`, `last.pt`, `args.yaml`, `results.csv`, versiones (`environment.json`, `requirements-resolved.txt`), hashes (`experiment.json` con el del checkpoint preentrenado, `evaluation.json` con el del `best.pt`, `run-manifest.json`), `dataset-manifest.json` y `error.log` si hubo error.

Límites: el bloqueo de un solo run vive junto a los resultados; sin Drive, una sesión nueva lo pierde, y la comprobación de parámetros evita ediciones accidentales, no impide que alguien cambie el cuaderno a propósito. No ejecutar otro ensayo, barrido de hiperparámetros ni repetición sin acuerdo explícito.

## Antes de gastar GPU (bloqueos a resolver)

1. **ZIP real localizado y hash aprobado verificado el 04/11/2026**, con respaldo externo recuperado y comprobado. Consultar el registro de [T04](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/4); los archivos y accesos permanecen fuera de Git. Entregar al cuaderno el ZIP original, no el paquete exterior de respaldo. No regenerarlo ni sustituirlo por otro.
2. **Permisos de reutilización de las fuentes: pendientes de documentar.** La casilla `PERMISSIONS_CONFIRMED` solo se marca si constan por escrito; la aprobación de las cajas no es una licencia.
3. Colab gratuito con GPU asignada. Sin GPU, detenerse. No comprar unidades ni activar servicios de pago.
4. Elegir y justificar el umbral antes del entrenamiento y de observar predicciones del test. `CONFIDENCE_THRESHOLD` empieza en `None` y `CONFIDENCE_RATIONALE` vacío; la configuración se detiene antes de crear el run si no se completan. No se elige un valor por defecto ni se interpreta como precisión.
5. Para la verificación local de pesos, instalar `requirements-inference.txt` en `.venv`. Generar o comprobar el empaquetado con simulaciones no sustituye esta carga real. El script opcional `validate_nox_text_notebook.py` también necesita `nbformat`, que no está en los requisitos fijados; no es necesario para usar el verificador de resultados.

## Pasos para Fer

1. Subir `notebooks/nox_text_training.ipynb` a Colab y elegir **Entorno de ejecución → GPU** (gratuita). Ejecutar sus dos primeras celdas de comprobación y continuar dentro del mismo cuaderno y sesión. El éxito del cuaderno de diagnóstico independiente no garantiza que otro notebook comparta su entorno.
2. Ejecutar las celdas **en orden**. En la celda del dataset, marcar `PERMISSIONS_CONFIRMED` solo si procede y subir el ZIP aprobado. En la configuración, completar `CONFIDENCE_THRESHOLD` y su motivo antes de entrenar. Opcional: `USE_DRIVE = True` conserva resultados y bloqueos tras una desconexión, pero requiere autorizar el montaje; no es obligatorio para usar el cuaderno.
3. Ejecutar **una vez** entrenamiento y evaluación. No cambiar parámetros ni mirar el test para decidir nada.
4. Ejecutar la última celda aunque haya fallado: descarga `nox-text-<fecha>-results.zip`. Guardar también el cuaderno ejecutado (**Archivo → Descargar → .ipynb**).
5. En local, desde la raíz del repositorio, instalar las dependencias de inferencia y verificar:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements-inference.txt
   .\.venv\Scripts\python.exe scripts/verify_nox_text_results.py "C:\ruta\nox-text-AAAAMMDD-HHMMSS-results.zip"
   if ($LASTEXITCODE -ne 0) { throw "Resultados rechazados: revisar la salida y verification.json si existe" }
   ```

   Solo devuelve código 0 y `complete: true` si pasan la integridad, archivos obligatorios, configuración en `args.yaml` y `experiment.json`, modelo de origen YOLO11n, hashes aprobados del dataset y su manifiesto empaquetado, estado coherente del run y selección de umbral registrada. Además carga **ambos** checkpoints en CPU y comprueba detección con la clase única `0: nox_texto`, sin entrenar ni predecir. Un archivo llamado `best.pt` no basta.

   La salida debe estar ignorada por Git; se desempaqueta en `local-artifacts/nox-text-runs/<run>/`, sin sobrescribir. Si el paquete es íntegro pero no aceptable, conserva `verification.json` con `complete: false` y sus errores, y devuelve código 2. Una ruta peligrosa o un hash alterado se rechazan antes de extraer. Ante cualquier error, **no ejecutar T10**. `complete` comprueba el paquete de entrenamiento y los pesos, no la calidad del detector ni el cierre del esencial.
6. Solo tras una verificación correcta, usar el predictor con el **mismo umbral registrado antes del entrenamiento**. Sustituir `<run>`, `<nombre>` y la ruta de imagen:

   ```powershell
   $run = "local-artifacts/nox-text-runs/<run>"
   $experiment = Get-Content "$run/experiment.json" -Raw | ConvertFrom-Json
   .\.venv\Scripts\python.exe scripts/predict_image.py "ruta\imagen.png" --checkpoint "$run/train/weights/best.pt" --output "local-artifacts/predictions/<nombre>" --confidence $experiment.confidence_threshold
   ```

   La salida debe quedar en `local-artifacts/` o `data/review/`. Una detección sin revisar no demuestra exposición, y sin detecciones no se prueba que el logo falte.
7. Registrar en la issue #5 el identificador del run, los hashes y las métricas **tal cual**, junto con las cajas revisadas a escala nativa y los fallos. Las métricas de validación (un solo positivo) son inestables y el test es una imagen ya inspeccionada: no declarar el nivel esencial ni confiabilidad con este resultado. Aceptar o descartar el modelo es una decisión posterior de Fer.

No subir a Git imágenes, ZIP, pesos ni resultados; `local-artifacts/` está excluido.

## Alcance de la verificación

Los hashes de referencia del verificador corresponden al ZIP aprobado y a los bytes exactos de `manifest.json` dentro de ese ZIP. La copia documental del manifiesto puede tener metadatos o saltos de línea distintos y no se usa como sustituto del manifiesto empaquetado. Un cambio de dataset requiere revisar explícitamente la identidad esperada; un ZIP internamente coherente no se acepta automáticamente como el ensayo acordado.

Las pruebas de carga real crean pesos temporales **sin entrenar**, únicamente para comprobar que se pueden abrir y validar las clases. No son un modelo para Mozart ni evidencia de calidad. T05, la evaluación real y la revisión humana siguen pendientes.

## Validación de la corrección — 04/11/2026

- **65 pruebas correctas, sin omisiones**, en CPU con las dependencias de inferencia instaladas. Incluyen veinte pruebas del cuaderno/verificador y tres pruebas de carga real aisladas en procesos separados.
- Rechazo de parámetros distintos aunque el ZIP tenga hashes internos coherentes, identidad del dataset cambiada, pesos ilegibles o con otra clase, y salida CLI distinta de cero para paquetes incompletos.
- Rechazo de rutas de ZIP peligrosas en Windows; salidas ignoradas por Git y sin sobrescritura. Un fallo temprano no permite un segundo intento de entrenamiento sobre el mismo run.
- Prueba de evaluación simulada: reutiliza el umbral guardado antes de entrenar, aunque cambie después la variable de la celda; no hay umbral real seleccionado en esta corrección.
- ZIP real aprobado: comprobadas localmente las 23 imágenes/etiquetas, dimensiones, cajas, grupos y hash del manifiesto empaquetado mediante la celda de validación con una entrada local, sin subida externa.
- Cuaderno regenerado, sintaxis válida, sin salidas guardadas y coincidente con su generador. Sin nuevos pesos o ZIP en Git.
- No se ejecutó el entrenamiento real, no se usó GPU y no se validó aún una sesión real de Colab ni un ZIP de resultados del nuevo ensayo.
