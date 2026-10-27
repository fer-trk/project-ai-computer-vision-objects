# Primer ensayo NOX: resultados y revisión — 27/10/2026

El ensayo confirmó la ejecución del proceso de entrenamiento en Colab, pero las predicciones revisadas todavía no sirven para medir exposición fiable. El comentario del profesor se adopta como prioridad: ampliar datos originales y distinguir palabra y símbolo.

## Evidencia comprobada

- ZIP local: `data/review/colab-results/smoke-20261027-092003-results.zip`. CRC correcto; incluye configuración, métricas, vistas y pesos best/last. No se cargaron ni ejecutaron los pesos en el portátil.
- YOLO11n, una clase `nox`, 3 épocas, resolución 640, lote 2 y semilla 42, según args.yaml. Entorno registrado: Python 3.13.16, PyTorch 2.11.0+cu130, CUDA 13.0, Ultralytics 8.4.189 y Tesla T4.
- Tiempo de la llamada de entrenamiento registrado en execution.json: 31,46 segundos. No es una estimación de futuros ensayos ni incluye toda la preparación de la sesión.
- El manifiesto del ZIP coincide byte a byte con el manifiesto publicado: 15 imágenes train (12 positivas y 3 negativas) y 3 val (1 positiva en muñequera y 2 negativas). No se entrenó con 40 imágenes: 40 era el inventario revisado, con 22 excluidas.
- results.csv contiene las tres épocas. En la tercera registra precisión 0,00206, recall 1, mAP50 0,02764 y mAP50–95 0,01106. Estas cifras corresponden a esa validación mínima; mAP no es porcentaje de imágenes acertadas y recall 1 con un único positivo no demuestra calidad general. No sustituir estos valores por métricas de otra ejecución.
- Hashes y resultados tabulares en [registro verificable](nox-first-training-review-2026-10-27.json). Los medios, pesos y cuaderno ejecutado siguen en local, excluidos de Git.

## Revisión visual realizada

Se inspeccionaron las vistas originales `val_batch0_labels.jpg`, `val_batch0_pred.jpg` y `confusion_matrix.png` del ZIP:

| Imagen en la vista | Etiqueta de referencia | Observación visual de predicción |
|---|---|---|
| `7695444675531951382_b9763220d7f9.png` | Negativa revisada | No se aprecia caja en la vista guardada. No implica ausencia de propuestas por debajo de su umbral de visualización. |
| `7695453226648292630_f3613f595620.png` | Negativa revisada | Se marcan partes de la camiseta y la cinta de la red como NOX: falsas detecciones respecto a la revisión. |
| `7695453226648292630_244c1944d702.png` | Una caja clara en la muñequera | La vista de predicciones marca el brazo; no muestra una caja ajustada al logo de muñequera anotado. |

La matriz incluye 1 coincidencia y 899 propuestas sin correspondencia con etiquetas bajo su configuración de validación. No son 899 falsas detecciones visibles en el mosaico ni se equiparan directamente al valor de precisión de results.csv: las vistas y las métricas usan filtros y criterios diferentes. La matriz admite una coincidencia aunque el mosaico no muestre una caja útil sobre la muñequera. No hay TXT/JSON de predicciones por imagen en este ZIP para reconstruir aquí todos sus scores.

Se contrastó la interpretación con el código oficial fijado de [validación](https://github.com/ultralytics/ultralytics/blob/v8.4.189/ultralytics/engine/validator.py) y [matriz de confusión](https://github.com/ultralytics/ultralytics/blob/v8.4.189/ultralytics/utils/metrics.py). No se hizo inferencia nueva ni evaluación en test. La revisión es de un ensayo corto, no una comparación concluyente entre modelos.

## Trazabilidad que debe conservarse

El cuaderno local `NOX_primer_ensayo_corregido.ipynb` conserva salidas de `smoke-20261027-091027`, mientras el ZIP pertenece a `smoke-20261027-092003`. Ambos evidencian ejecuciones, pero no se debe afirmar que sean la misma. Este informe toma configuración, métricas, tiempo y vistas del ZIP 092003. En futuros ensayos, descargar juntos cuaderno y ZIP y comprobar el mismo identificador de ejecución.

El cuaderno guardado por el usuario incorpora las correcciones de jedi y la eliminación de neptune. El cuaderno publicado en GitHub todavía necesita sincronizar esas correcciones; no afirmar que ya están allí ni que el push cambia las copias de Drive.

## Decisión y pendientes

Se vuelve a priorizar T04: más escenas y orígenes, dos variantes visuales (`nox_texto` y `nox_simbolo`), revisión y test independiente. El dataset y pesos anteriores de una clase se conservan como baseline exploratorio; no se renombran para simular un detector de dos clases. Dos variantes siguen siendo una sola marca.

Roboflow es el siguiente paso propuesto para gestionar y anotar el nuevo conjunto; aún no se ha creado proyecto ni subido datos a esa plataforma. Primero verificar acceso, plan gratuito y privacidad, conservar procedencia y comprobar permisos. Se propone una tanda inicial de unas 50 imágenes variadas y después ampliar hacia 200–300 según cobertura, sin prometer calidad por alcanzar una cifra.

T03 tiene evidencia real de entrenamiento gratuito, pero carece todavía de prueba de hosting/API y cierre de licencias. T05 tiene un ensayo ejecutado y artefactos guardados, pero no un modelo aceptado para el dataset ampliado. T10 tiene esta revisión preliminar, pero no test independiente, objetivos de calidad acordados ni aceptación del nivel esencial. No se cierra ninguna de estas tareas por este ensayo.
