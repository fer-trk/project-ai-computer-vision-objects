# Dataset exploratorio NOX — 26/10/2026

Se creó y verificó localmente un paquete de detección YOLO de una clase (`nox`). Es una preparación de datos para un ensayo; no se ha entrenado ni evaluado un detector.

| Partición | Grupo conservador | Imágenes | Positivas | Negativas | Cajas |
|---|---|---:|---:|---:|---:|
| Entrenamiento | Milano P1 | 15 | 12 | 3 | 12 |
| Validación | Germany P2 | 3 | 1 | 2 | 1 |

De 40 imágenes únicas revisadas se seleccionaron 18 y se excluyeron 22 pendientes/excluidas. Una imagen con una caja clara y otra región pendiente se excluye completa. Las imágenes repetidas en distintas revisiones se exportan una sola vez; para el piloto prevalecen las coordenadas originales guardadas en CVAT.

## Reconstrucción local

Desde la raíz del repositorio, con las imágenes originales y exportaciones locales indicadas por el inventario:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/prepare_nox_dataset.py
```

Dependencias de preparación: Python compatible con `Path.is_relative_to` y Pillow (incluida en `requirements-tools.txt`). La salida predeterminada es `data/review/nox-exploratory-dataset-2026-10-26/`, excluida de Git. El script rechaza sobrescribirla; para repetir, proporcionar otro subdirectorio nuevo con `--output data/review/nombre-nuevo`.

El paquete contiene imágenes PNG intactas, etiquetas TXT, `dataset.yaml`, `manifest.json` y `verification.json`. El YAML utiliza una ruta absoluta local: regenerarlo si se traslada. Las imágenes negativas tienen un archivo de etiquetas vacío. El manifiesto publicado en docs contiene referencias y hashes; los medios permanecen locales.

Las cajas se convierten de píxeles xyxy a centro/anchura/altura normalizados, clase cero, según el [formato oficial de detección de Ultralytics](https://docs.ultralytics.com/datasets/detect/).

## Comprobaciones realizadas

Pasaron las 14 pruebas automatizadas: nueve existentes del preparador del piloto y cinco del nuevo preparador. La generación real verificó las 18 imágenes mediante SHA-256, las 18 etiquetas, los límites de las cajas y su reconstrucción desde TXT con tolerancia de 0,001 píxel. Se comprobó ausencia de hashes de imagen, vídeos o grupos compartidos entre entrenamiento y validación. No se ha probado aún la carga mediante Ultralytics.

## Límites y siguiente paso

La validación contiene un único positivo, en muñequera, mientras los positivos de entrenamiento son de camiseta; no permite demostrar calidad comercial. Los grupos son conservadores y provisionales según metadatos de evento, sin identidad de partido confirmada. No existe conjunto de test independiente; los grupos no demuestran por sí solos ausencia de toda similitud visual. Las 12 imágenes positivas de entrenamiento tampoco son 12 escenas independientes.

Antes de entrenar o subir material a servicios externos, registrar condiciones de uso/permisos pendientes y verificar el entorno y recursos de T03. El siguiente paso técnico es preparar y comprobar ese entorno para el ensayo. T04 continúa en curso; T05 y T10 siguen pendientes. La aceptación final necesita más evidencia y un origen independiente para test.
