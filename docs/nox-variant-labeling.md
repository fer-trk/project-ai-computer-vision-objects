# NOX: guía de las dos variantes visuales

Fecha: 27/10/2026. T04. El usuario acepta continuar con la distinción de variantes solicitada por el profesor. Esta guía define el criterio para el nuevo dataset; no convierte automáticamente las etiquetas antiguas ni acepta nuevos positivos de pala.

| ID propuesto | Clase | Qué encerrar en la caja | Marca agregada |
|---|---|---|---|
| 0 | `nox_texto` | La palabra NOX completa, con su tipografía de marca reconocible | NOX |
| 1 | `nox_simbolo` | El emblema independiente en forma de X, contrastado con referencia oficial | NOX |

Los IDs se aplicarán al nuevo dataset. El conjunto del primer ensayo conserva su única clase `nox`: no es compatible por simple cambio de nombres con un modelo de dos clases. Dos variantes de NOX siguen siendo una sola marca; no satisfacen por sí solas el requisito multimarca.

## Referencias comprobadas

- **Símbolo y texto en un mismo producto:** [NOX AT10 Luxury Genius 18K Alum 2025, ficha oficial](https://noxsport.com/en/products/racket-at10-genius-18k-alum-by-agustin-tapia). Se inspeccionó la fotografía principal de la galería: muestra una gran X en la cara y la palabra NOX pequeña cerca del borde superior. Es referencia de apariencia, no prueba del modelo exacto que aparece en nuestros vídeos ni permiso para reutilizar la foto como dato de entrenamiento.
- **Texto en vídeo propio:** segundo 29, frame 725, vídeo `7697671396830317846`, referencia histórica N01. PNG `data/review/user-moments-2026-10-26/frames/7697671396830317846/T08_frame_000725.png`, SHA-256 `017b5348045c9c98c59d3dd40196b36046ead9ad457e0865a2817389b8603201`. Se inspeccionó el original y un detalle nativo, sin ampliación ni mejora. La palabra NOX del pecho es reconocible. Caja de referencia CVAT ya revisada: xyxy `[610.6, 1558.9, 713.1, 1618.9]` sobre 1080 × 1920. Su futura clase será `nox_texto`; no se ha migrado todavía.
- **Pala a 9 s:** frame 225, SHA-256 `bcb30588edaeade499874178bd6cceb36c0e07521d1429bab117007ffef5622d`. Reinspeccionados original y detalle nativo. El tamaño y el movimiento no permiten tomarla como referencia clara del símbolo. Continúa pendiente, sin caja nueva y sin considerarla negativa.
- **Pala a 25 s:** frame 625, SHA-256 `85a150ea55ea6cd1d9e19c047f4a6b1fdeb13191acc4846cf24cc0b311c23164`. La cara muestra un gráfico compatible con la variante en X, pero la revisión nativa sigue afectada por movimiento y perforaciones. Se conserva como candidato, sin aprobar aún caja de entrenamiento. Ya corresponde a E06; no añadir otra imagen al inventario por esta revisión.

Los dos frames de pala pertenecen al mismo vídeo y carpeta que el ejemplo de texto, con nombres `T03_frame_000225.png` y `T06_frame_000625.png`. Los recortes de inspección permanecen locales y no son nuevas imágenes de entrenamiento. No se han descargado ni publicado fotos oficiales.

## Reglas de anotación

1. **La clase depende del diseño, no del soporte.** La palabra NOX en una pala es `nox_texto`; una X independiente en una prenda puede ser `nox_simbolo` si coincide con la referencia. Registrar soporte por separado (ropa, muñequera, pala, estático). El detector de estas dos clases no aprenderá automáticamente ese atributo.
2. **Una caja ajustada por impresión visible**, sin incluir toda la pala, camiseta o persona. Mantener coordenadas sobre el original. Las perforaciones de una pala forman parte del aspecto visible de la impresión, no son cajas adicionales.
3. **Si aparecen dos impresiones separadas, anotar ambas.** Ejemplo: gran X central y palabra NOX pequeña en el borde de una pala, siempre que cada una sea identificable. También pueden coexistir NOX en pecho y símbolo en pala dentro del mismo frame.
4. **No duplicar dentro de la palabra.** La X final de NOX no recibe otra caja `nox_simbolo`. Si únicamente queda visible esa letra por un recorte u oclusión, no asumir que sea el emblema independiente.
5. **Categorías de claridad conservadas.** Identificable: positivo de su variante. Probable/ambiguo: pendiente, sin exposición confirmada. No identificable: fuera de los positivos. No reconstruir letras ni atribuir la marca por jugador, color o modelo supuesto.
6. **No convertir incertidumbre en negativo.** Revisar todas las apariciones objetivo de una imagen. Si contiene una región dudosa sin resolver, mantener la imagen fuera del conjunto utilizable; nuestro exportador YOLO actual no implementa regiones ignoradas.
7. **Mantener la procedencia.** Conservar vídeo, frame, hash y grupo de origen. No repartir tomas próximas o variantes derivadas de la misma escena entre entrenamiento, validación y test. Aplicar aumentos solo al entrenamiento tras fijar las particiones.
8. **Agrupar por marca al informar.** Preservar la variante, pero calcular el tiempo NOX mediante la unión de intervalos de ambas, evitando sumar dos veces segundos simultáneos dentro del mismo apartado de soporte. Ropa/palas y soportes estáticos seguirán en apartados separados.

## Resultado de este paso y continuación

Queda fijado el esquema visual de dos clases con referencia oficial del símbolo y un ejemplo propio claro de texto. Sigue faltando un ejemplo propio de símbolo con calidad suficiente y caja revisada. No se han modificado las decisiones históricas, generado otro dataset, creado un proyecto Roboflow ni entrenado de nuevo.

Siguiente paso: configurar el proyecto de detección en Roboflow con estos nombres y revisar condiciones gratuitas, privacidad y uso del material antes de subirlo. Primera ampliación propuesta: una tanda de unas 50 imágenes originales variadas, incluyendo primeros planos de la X y NOX escrito, con fuentes suficientes para reservar un test independiente. 200–300 imágenes es un objetivo inicial de recopilación, no un umbral demostrado de calidad.
