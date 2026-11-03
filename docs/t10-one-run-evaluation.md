# T10: evaluación única de imágenes tras T05

Preparado el 03/11/2026. **No se ha ejecutado inferencia real**: falta el `best.pt` de T05. Este documento no demuestra ni la calidad del detector ni el nivel esencial; solo deja listo el procedimiento.

## Qué hace

`scripts/evaluate_nox_text_run.py` es un envoltorio de `scripts/predict_image.py`. No crea otro predictor: llama a `run_inference` una vez por imagen, en CPU, y añade las comprobaciones que hacen la evaluación reproducible.

Se bloquea antes de inferir si:

- falta el checkpoint o no es un `.pt` local;
- el checkpoint no declara exactamente la clase `0: nox_texto` (se lee el nombre de clases sin ejecutar inferencia);
- el manifiesto no declara solo `0: nox_texto`;
- la imagen o el manifiesto están bajo `data-synthetic/`, o la entrada está marcada como sintética;
- el manifiesto no tiene partición `test`, o una imagen de `test` comparte `source_sha256` con `train` o `val`;
- falta `--confidence` (no hay valor por defecto) o está fuera de 0–1;
- la salida no está en `data/review/` o `local-artifacts/`, no está ignorada por Git (se consulta `git check-ignore`) o ya existe.

La partición reservada es solo `test`. `val` no se admite porque sirvió para elegir `best.pt`. Hoy `test` tiene **una imagen** ya inspeccionada y elegida por legibilidad, y el manifiesto la declara `independent_blind_test: false`. El informe lo repite: no es un test ciego.

## Antes de ejecutar: decisiones de Fer

1. **Umbral de confianza.** No hay uno aprobado. `0.25` solo se usó en la comprobación funcional de T10. Fer debe elegirlo, fijarlo **antes** de ver el resultado y escribir el motivo en `--confidence-rationale`. No debe ajustarse mirando los resultados de `test`. La confianza no es precisión.
2. **Una sola ejecución.** La salida nueva no se sobrescribe. Repetir con otro umbral sobre la misma imagen convierte `test` en datos de ajuste; si ocurre, hay que registrarlo.
3. **Rutas reales.** Los comandos asumen la estructura que describen los documentos de T04 y T05. Deben comprobarse en el equipo, porque ni los medios ni los pesos están en Git:
   - checkpoint: `local-artifacts/nox-text-runs/<run>/train/weights/best.pt` (lo crea `verify_nox_text_results.py`);
   - imágenes: `data/review/nox-text-dataset-2026-11-03/` (contiene `images/test/...`);
   - manifiesto: `docs/nox-text-dataset-2026-11-03.json`, la copia versionada, cuyo esquema se comprobó con ficheros vacíos de ejemplo.
4. **Entorno.** Requiere `requirements-inference.txt` (Ultralytics y PyTorch en CPU). Sin ellas, el comando se detiene al leer las clases.
5. **Derechos.** El manifiesto indica que los permisos de reutilización siguen pendientes. Las imágenes y los resultados permanecen locales.

## Comando exacto

Sustituir `<run>` por la carpeta verificada de T05 y `<motivo>` por la razón del umbral:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_nox_text_run.py run `
  --checkpoint "local-artifacts/nox-text-runs/<run>/train/weights/best.pt" `
  --images-dir "data/review/nox-text-dataset-2026-11-03" `
  --manifest "docs/nox-text-dataset-2026-11-03.json" `
  --output "local-artifacts/t10-evaluation/<run>" `
  --confidence <umbral-elegido-por-Fer> `
  --confidence-rationale "<motivo>"
```

Para limitarse a imágenes concretas de `test`, repetir `--image nombre.png`. Un nombre que no sea de `test` o esté repetido bloquea la ejecución.

## Qué produce

En la carpeta de salida:

- `images/NNN_<nombre>/annotated.png`, `predictions.json` y `predictions.csv`: salida de `predict_image.py` con hashes de imagen y checkpoint, dimensiones, clase, score y caja `xyxy`;
- `summary.csv`: una fila por imagen, con dimensiones, cajas anotadas en el manifiesto, número de detecciones y estado `detections` o `no_detections`;
- `detections.csv`: una fila por detección en todas las imágenes;
- `run.json`: hashes del checkpoint y del manifiesto, parámetros, umbral y motivo, totales y límites;
- `review-template.json`: plantilla para la revisión manual.

No calcula tiempo ni porcentaje de exposición y no interpreta el score.

## Revisión manual e informe

1. Abrir cada `annotated.png` y comparar las cajas con la imagen original a resolución nativa.
2. Copiar `review-template.json` como `review.json` en la misma carpeta y rellenarlo: `reviewed: true`, `reviewer`, un `verdict` por detección (`true_positive` o `false_positive`) y `missed_logos` por imagen (entero con los logos NOX visibles sin detectar; son los falsos negativos).
3. Generar el informe:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_nox_text_run.py report --run-dir "local-artifacts/t10-evaluation/<run>"
```

Se detiene si la revisión está sin completar, si no corresponde al checkpoint o a las imágenes de la ejecución, o si `report.json` ya existe. Escribe `report.json` y `report.md` con detecciones, imágenes sin detecciones, falsos positivos y falsos negativos. Solo da recuentos, sin ratios ni umbrales de calidad.

## Verificación de esta preparación

Las 15 pruebas nuevas usan un detector simulado y un checkpoint ficticio. Comprueban los bloqueos, imágenes con y sin detecciones, la coherencia entre JSON y CSV, y el informe. **Verifican software, no la calidad del modelo.**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_evaluate_nox_text_run -v
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Límites: la comprobación real de las clases del checkpoint (`read_class_names`) y la inferencia real con Ultralytics no se han ejecutado. La primera ejecución real es la que las valida. El predictor recarga el modelo en cada imagen, lo que es aceptable con una imagen de `test`.
