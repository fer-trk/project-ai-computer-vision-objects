# T10: evaluación única de imágenes tras T05

Preparado el 03/11/2026. **No se ha ejecutado inferencia real**: falta el `best.pt` de T05. Este documento no demuestra ni la calidad del detector ni el nivel esencial; solo deja listo el procedimiento.

## Qué hace

`scripts/evaluate_nox_text_run.py` es un envoltorio de `scripts/predict_image.py`. No crea otro predictor: llama a `run_inference` una vez por imagen, en CPU, y añade las comprobaciones que hacen la evaluación reproducible.

Se bloquea antes de inferir si:

- falta el checkpoint o no es un `.pt` local;
- no es el `train/weights/best.pt` de un run con `verification.json` completo de T05, sus pesos validados y artefactos cuyos hashes siguen coincidiendo;
- el checkpoint no declara exactamente la clase `0: nox_texto` (se lee el nombre de clases sin ejecutar inferencia);
- el manifiesto no declara solo `0: nox_texto`;
- la imagen o el manifiesto están bajo `data-synthetic/`, o el manifiesto o cualquier entrada están marcados como sintéticos, aunque estén en otra carpeta;
- el manifiesto no tiene `test`, faltan vídeo/grupo o hay cruces por hash, `video_id` o `group_id` entre train, val y test;
- el hash real o las dimensiones de alguna imagen seleccionada difieren del manifiesto; se comprueban todas antes de la primera predicción;
- la identidad de imágenes, etiquetas, cajas y particiones no corresponde al manifiesto empaquetado y verificado en T05; los campos documentales, como rutas originales, pueden diferir;
- falta `--confidence` o su motivo, está fuera de 0–1, o no coincide con la elección registrada antes del entrenamiento en T05;
- ya existe `T10_STARTED.lock` junto a los artefactos de ese run de T05, aunque se elija otra salida;
- la salida no está en `data/review/` o `local-artifacts/`, no está ignorada por Git (se consulta `git check-ignore`) o ya existe.

La partición reservada es solo `test`. `val` no se admite porque sirvió para elegir `best.pt`. Hoy `test` tiene **una imagen** ya inspeccionada y elegida por legibilidad, y el manifiesto la declara `independent_blind_test: false`. El informe lo repite: no es un test ciego.

## Antes de ejecutar: decisiones de Fer

1. **Umbral de confianza.** Fer lo elige y justifica en T05 **antes del entrenamiento y de ver predicciones del test**. Aquí se reutilizan exactamente `confidence_threshold` y `confidence_rationale` de `experiment.json`; no se elige un valor nuevo. La confianza no es precisión.
2. **Una sola ejecución por run conservado de T05.** `T10_STARTED.lock` se crea después de las comprobaciones y antes de inferir; registra la selección, salida y estado (`started`, `completed` o `failed`). Un fallo de inferencia también consume el intento. No se borra para reintentar ni se cambia la salida para eludirlo; cualquier excepción requiere acuerdo explícito y registro. Copiar o eliminar deliberadamente estos archivos queda fuera de la garantía del bloqueo local.
3. **Rutas reales.** Los comandos asumen la estructura que describen los documentos de T04 y T05. Deben comprobarse en el equipo, porque ni los medios ni los pesos están en Git:
   - checkpoint: `local-artifacts/nox-text-runs/<run>/train/weights/best.pt` (lo crea `verify_nox_text_results.py`);
   - imágenes: `data/review/nox-text-dataset-2026-11-03/` (contiene `images/test/...`);
   - manifiesto: `docs/nox-text-dataset-2026-11-03.json`, la copia documental versionada; se contrasta su identidad de datos con `dataset-manifest.json` del run verificado.
4. **Entorno.** Requiere `requirements-inference.txt` (Ultralytics y PyTorch en CPU). Sin ellas, el comando se detiene al leer las clases.
5. **Derechos.** El manifiesto indica que los permisos de reutilización siguen pendientes. Las imágenes y los resultados permanecen locales.

## Comando exacto

Sustituir `<run>` por la carpeta verificada de T05. Si se trabaja desde otro worktree, usar rutas absolutas al run y al dataset: los archivos ignorados no se trasladan entre copias de trabajo. Conservar el run y sus bloqueos en una carpeta escribible.

```powershell
.\.venv\Scripts\python.exe scripts/verify_nox_text_results.py "C:\ruta\nox-text-AAAAMMDD-HHMMSS-results.zip"
if ($LASTEXITCODE -ne 0) { throw "T05 rechazado: no ejecutar T10" }
$run = "local-artifacts/nox-text-runs/<run>"
$experiment = Get-Content "$run/experiment.json" -Raw | ConvertFrom-Json
.\.venv\Scripts\python.exe scripts/evaluate_nox_text_run.py run `
  --checkpoint "$run/train/weights/best.pt" `
  --images-dir "data/review/nox-text-dataset-2026-11-03" `
  --manifest "docs/nox-text-dataset-2026-11-03.json" `
  --output "local-artifacts/t10-evaluation/<run>" `
  --confidence $experiment.confidence_threshold `
  --confidence-rationale $experiment.confidence_rationale
```

Para limitarse a imágenes concretas de `test`, repetir `--image nombre.png`. Un nombre que no sea de `test` o esté repetido bloquea la ejecución.

Si ya se verificó y extrajo T05, no volver a ejecutar el verificador sobre la misma salida: conserva su `verification.json` y continúa desde la lectura de `$experiment`. No se permite sobrescribir un run verificado.

## Qué produce

En la carpeta de salida:

- `images/NNN_<nombre>/annotated.png`, `predictions.json` y `predictions.csv`: salida de `predict_image.py` con hashes de imagen y checkpoint, dimensiones, clase, score y caja `xyxy`;
- `summary.csv`: una fila por imagen, con dimensiones, cajas anotadas en el manifiesto, número de detecciones y estado `detections` o `no_detections`;
- `detections.csv`: una fila por detección en todas las imágenes;
- `run.json`: hashes del checkpoint/manifiesto, referencia a la verificación de T05, parámetros, umbral y motivo, inventario de hashes de resultados, totales y límites;
- `review-template.json`: plantilla para la revisión manual.

No calcula tiempo ni porcentaje de exposición y no interpreta el score.

## Revisión manual e informe

1. Abrir cada `annotated.png` y comparar las cajas con la imagen original a resolución nativa.
2. Copiar `review-template.json` como `review.json` en la misma carpeta y rellenarlo: `reviewed: true`, `reviewer`, un `verdict` por detección (`true_positive`, `false_positive` o `ambiguous`) y `missed_logos` por imagen (entero con logos NOX claros sin detectar; son los falsos negativos). `ambiguous_logos` recoge candidatos inciertos sin detección. La ambigüedad se cuenta aparte y exige explicar el caso en `notes`; no se fuerza a TP/FP/FN.
3. Generar el informe:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_nox_text_run.py report --run-dir "local-artifacts/t10-evaluation/<run>"
```

Se detiene si la revisión está sin completar, si no corresponde al checkpoint/imágenes, si cambió algún artefacto inventariado o si ya existe el informe. Escribe `report.json` y `report.md` con hashes, parámetros, recuentos y límites. Incluye la referencia a T05 y el hash de la revisión manual. No calcula ratios ni exposición ni equipara score con precisión.

## Verificación de esta preparación

Las pruebas de T10 usan un predictor controlado y artefactos de T05 temporales de ejemplo. No tienen un bypass por CLI: las identidades de ejemplo se sustituyen solo dentro de las pruebas. Cubren hashes reales, procedencia, transferencia desde T05, umbral fijado, bloqueo de repeticiones y revisión manual con ambiguos. **Verifican software, no la calidad del modelo.**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_evaluate_nox_text_run.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Límites: la comprobación real de las clases del checkpoint (`read_class_names`) y la inferencia real con Ultralytics no se han ejecutado. La primera ejecución real es la que las valida. El predictor recarga el modelo en cada imagen, lo que es aceptable con una imagen de `test`.

Las comprobaciones de vídeo/grupo prueban separación según la procedencia declarada, no independencia real de partidos o sesiones. El test aprobado continúa siendo una imagen ya inspeccionada y no puede renombrarse como test ciego cambiando una bandera del manifiesto. Los permisos documentados, el checkpoint nuevo válido, la revisión humana y la aceptación del nivel esencial siguen pendientes.

### Corrección comprobada — 04/11/2026

- Rama sincronizada con `dev` y el verificador de T05 del PR #19.
- **103 pruebas completas correctas, sin omisiones**, en CPU, incluidas las de T05 y los preparadores ya integrados. Las **28 pruebas específicas de T10** también pasan tras completar la validación del texto de revisión.
- Datos reales: comprobada localmente la imagen reservada, su hash y dimensiones, la separación declarada y la identidad de datos de la copia documental frente al manifiesto empaquetado aprobado. No se ejecutó predicción sobre esa imagen.
- Pruebas de bloqueo antes de inferir, reintento en otra salida, fallo durante la inferencia, ambiguos con notas e informe con artefactos alterados.
- No se entrenó, no se consumió GPU, no se generaron métricas de calidad reales y no se publicaron imágenes ni pesos.
