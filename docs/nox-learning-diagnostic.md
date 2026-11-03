# Diagnóstico de aprendizaje de texto NOX

Bloque aprobado por Fernanda el 03/11/2026. Refs #5.

El ensayo `nox-text-20261103-104507` terminó en 11 épocas y conservó la época 1.
En las cuatro vistas a confianza 0,25 se observaron 13 falsos positivos y tres
logos omitidos. Este diagnóstico pregunta si el proceso puede ajustar una muestra
de train; no repite la evaluación exploratoria ni afirma una causa demostrada.

Cuaderno: `notebooks/nox_learning_diagnostic.ipynb`, ejecutable en GPU gratuita
con el mismo ZIP `nox-text-dataset-2026-11-03.zip` (SHA-256
`8332c1b07824f7c5a2abac9c43f17c23cc78dfa2d7c92d9953af77b4a9364254`).

- Selección determinista: tres positivos de vídeos distintos por mayor caja y un
  negativo, todos de train. Cuatro imágenes y cuatro cajas; etiquetas intactas.
- 80 épocas, patience=0, 640, batch=nbs=2, Adam, lr0=0,001 constante, warmup=0,
  sin aumentos. Actualización de pesos en cada lote; checkpoint oficial fresco.
- Se evalúa last.pt sobre la misma muestra: confianza 0,25, IoU >= 0,50,
  coincidencias una a una. Criterio de ajuste: todas las cajas recuperadas y cero
  falsas detecciones. Es una comprobación de memorización, no una meta del producto.
- train y val apuntan a la misma muestra únicamente para compatibilidad del
  entrenador. Ninguna métrica interna constituye validación independiente.
- Cambian varios controles para facilitar el ajuste: un resultado diferente no
  identifica por sí solo qué cambio fue causal. No se utilizan val/test originales.
- Se descargan muestra, pesos, entorno, configuración, vistas y sample-fit.json en
  un ZIP no publicable en Git; guardar también el cuaderno ejecutado del mismo run.

Validación local: esquema nbformat, sintaxis de siete celdas, ZIP real, hashes de
copias, selección solo train, cargador Ultralytics 8.4.189 (4 imágenes, 0 corruptas),
parámetros de API y asociación IoU en casos exactos, duplicados, ausentes, negativos,
sin solapamiento y límite 0,50. Control de no sobrescritura verificado.

Pendiente: entrenamiento GPU real, predicciones de last.pt y revisión visual del
resultado. No se ha ejecutado este diagnóstico ni se ha aceptado un modelo.

Para repetir las comprobaciones (requiere nbformat y dependencias de inferencia):

```bash
python scripts/validate_nox_learning_diagnostic.py /ruta/al/dataset.zip
```

Si aprende la muestra, revisar después generalización y configuración completa;
si falla, inspeccionar pérdidas, inicialización/cabeza, gradientes y carga real
antes de ampliar datos o ensayar más combinaciones. No modificar cajas aprobadas
solo porque una predicción sea errónea.

## Resultado del diagnóstico 110615 y siguiente ejecución

El 03/11/2026 se recibió el cuaderno ejecutado y el ZIP
`nox-fit-20261103-110615-results.zip` (SHA-256
`19a4e3d215d23512657d7796efb56d5dbdf8973ecf37bc4de29490161015140f`).
Siete celdas 1–7, código intacto y sin errores; CRC y hashes de muestra correctos.
80 épocas, 100,54 s de llamada. last.pt SHA-256
`8392cbee815733eeb9465f079ef974701bf070a94bcbc79f4a30f670956fdaba`.

Resultado a confianza 0,25 / IoU 0,50: TP=4, FP=0, FN=0; negativo sin detecciones.
IoU de las cuatro cajas: 0,9762 / 0,9625 / 0,9751 / 0,9801. Se inspeccionaron las
vistas positiva con dos cajas y negativa. El proceso consigue aprender la muestra;
no se demuestra generalización ni se identifica un único cambio causal.

Siguiente cuaderno listo: `notebooks/nox_full_training.ipynb`. Reutiliza el dataset
original 19/3/1 y las celdas verificadas de integridad/evaluación. Entrena desde
checkpoint oficial fresco con 80 épocas, patience=0, batch=nbs=2, Adam lr=0,001
constante y sin aumentos; val separado, selección de best.pt y test exploratorio.
Validación local: esquema, sintaxis, configuración ejecutada y API; ejecución GPU
real pendiente. No se modifican etiquetas ni se incorpora la muestra al val/test.
