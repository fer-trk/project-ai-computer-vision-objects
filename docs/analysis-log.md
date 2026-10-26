# Registro de análisis del material de pádel

Estado: exploración inicial. Fecha de apertura: 21/10/2026 (Europe/Madrid). Las marcas, anotaciones y reglas técnicas siguen pendientes de revisión con el usuario.

Este documento conserva el método, las observaciones y las decisiones del análisis. Los requisitos viven en [specs.md](specs.md); la ejecución y los bloqueos de cada entregable se registran en las issues del [plan](plan.md). La preparación de esta muestra no completa T04 ni aprueba un modelo.

## 1. Pregunta de esta revisión

¿Qué marcas ofrecen ejemplos suficientes y visualmente identificables en ropa y palas para medir la exposición de sponsors de jugadores en cada publicación individual, respetando el plazo y el coste cero? Los soportes estáticos se analizarán en una sección secundaria separada.

La muestra permite explorar el material y acordar criterios. No permite calcular precisión del detector, medir exposición temporal ni demostrar que ya existe un dataset suficiente para entrenar.

## 2. Decisiones funcionales recibidas

| Decisión del usuario | Consecuencia para el análisis |
| --- | --- |
| Priorizar ropa y palas; publicidad de pista en sección secundaria separada. | Seleccionar datos y evaluar por soporte; no confundir éxito en carteles con utilidad para sponsors de jugadores. |
| Categoría 1: logo claro. | Es la única categoría que aportará tiempo y porcentaje de exposición. |
| Categoría 2: posible marca, parcialmente identificable. | Mostrar hipótesis diferenciada, sin duración ni porcentaje. |
| Categoría 3: no identificable. | Descartar atribución de marca y medición; no forzar una respuesta por conocer al jugador. |
| Revisar 12 fotogramas por vídeo. | Preparar una primera muestra distribuida; ampliar alrededor de momentos útiles después. |
| Registrar el análisis en un documento. | Conservar aquí observaciones, decisiones, límites y siguientes pasos. |

La categoría corresponde a cada logo candidato, no a la imagen completa. Una imagen puede contener un cartel claro y una pala ilegible. La confianza del futuro detector no sustituye la revisión de claridad.

## 3. Material recibido

El usuario descargó cuatro MP4 con yt-dlp, junto con sus archivos `.info.json`. Los archivos se conservan en `data/raw/videos/`, excluidos de Git. Las fuentes quedan registradas para trazabilidad; descarga técnica y permisos de entrenamiento/publicación son cuestiones distintas, y los permisos siguen pendientes de comprobación.

| ID del vídeo | Duración indicada por los metadatos de descarga | Resolución indicada | Fuente |
| --- | --- | --- | --- |
| 7507398381900205334 | 81 s | 720 × 1280 | [Publicación](https://www.tiktok.com/@premierpadel/video/7507398381900205334) |
| 7697683756945280279 | 56 s | 1080 × 1920 | [Publicación](https://www.tiktok.com/@premierpadel/video/7697683756945280279) |
| 7697932261643128086 | 58 s | 1080 × 1920 | [Publicación](https://www.tiktok.com/@premierpadel/video/7697932261643128086) |
| 7698076371569888534 | 42 s | 1080 × 1920 | [Publicación](https://www.tiktok.com/@premierpadel/video/7698076371569888534) |

Total indicado por esos metadatos: 237 s (3 min 57 s). Son metadatos de descarga; los valores medidos por el decodificador se registran por separado para no confundir duraciones redondeadas con medidas precisas.

## 4. Método reproducible

1. Usar Python del `.venv` del proyecto. Incorporar OpenCV sin interfaz gráfica y Pillow como herramientas para lectura de vídeo y hojas de contacto; registrar versiones en `requirements-tools.txt`.
2. Leer los vídeos secuencialmente, conservando solo los frames seleccionados en memoria. Comparar el número decodificado con el indicado por el archivo.
3. Dividir el rango de índices de frames en doce grupos iguales y elegir el centro de cada grupo. Es un muestreo sistemático por índice, no selección manual de los mejores planos ni garantía de separación temporal exacta en vídeo de frecuencia variable.
4. Guardar los frames seleccionados en PNG, a resolución completa y sin realces, y construir una hoja de contacto por vídeo con miniaturas e identificadores S01–S12.
5. Registrar hash SHA-256 del vídeo, frame, referencia temporal, base de esa referencia, dimensiones, versiones y ruta de cada muestra en un manifiesto.

Los instantes son referencias para volver al vídeo: el script usa el timestamp informado por el decodificador y, si no es utilizable, una estimación `índice / FPS` identificada como tal. No se usarán estas doce muestras ni sus tiempos para calcular exposición. La política temporal final requiere validación específica.

Desde la raíz del proyecto, con `.venv` activo:

```bash
python -m pip install -r requirements-tools.txt
python scripts/sample_videos.py
```

Salidas locales: `data/review/initial-2026-10-21/`. Contiene `manifest.json`, `index.md`, las carpetas `frames/` y `sheets/`. Las salidas están excluidas de Git. Al clonar el repositorio faltarán las imágenes locales: se regeneran con los vídeos autorizados y el script. Repetir el script reconstruye esas salidas y no sobrescribe este registro de análisis.

## 5. Muestra para revisión conjunta

Abrir el [índice local de los 48 fotogramas](../data/review/initial-2026-10-21/index.md) para consultar el frame completo y su referencia temporal. Las hojas son una vista de navegación: no decidir que un logo es ilegible únicamente porque se vea pequeño en una miniatura.

| Vídeo | Hoja de contacto | Revisión humana |
| --- | --- | --- |
| 7507398381900205334 | [S01–S12](../data/review/initial-2026-10-21/sheets/7507398381900205334.jpg) | Pendiente |
| 7697683756945280279 | [S01–S12](../data/review/initial-2026-10-21/sheets/7697683756945280279.jpg) | Pendiente |
| 7697932261643128086 | [S01–S12](../data/review/initial-2026-10-21/sheets/7697932261643128086.jpg) | Pendiente |
| 7698076371569888534 | [S01–S12](../data/review/initial-2026-10-21/sheets/7698076371569888534.jpg) | Pendiente |

## 6. Registro de observaciones por candidato

Añadir una fila por logo candidato, con el PNG completo como evidencia. Puede haber varias filas para una misma muestra. Dejar la marca sin atribuir cuando la evidencia sea insuficiente. No completar categorías automáticamente antes de revisarlas.

| Vídeo / muestra | Marca candidata | Soporte | Categoría 1/2/3 | Evidencia y dificultad | Revisor / decisión |
| --- | --- | --- | --- | --- | --- |
| 7697671396830317846 / T03 / 29 s / frame 725 | NOX | Ropa, camiseta | 1 | [PNG completo](../data/review/player-moments-2026-10-21/frames/7697671396830317846/T03_frame_000725.png) | Usuario: logo claramente identificable; caja pendiente de anotar. |

Registrar tamaño aparente, desenfoque, oclusión, perspectiva y si hay texto o sobreimpresiones que podrían confundirse con logos del entorno. Las observaciones sobre soporte son manuales: todavía no se ha acordado un clasificador automático de ropa/pala/pista ni identificación de jugadores.

Observación preliminar de navegación, sin clasificación aprobada: en la hoja del vídeo 7507398381900205334 se ven planos generales con rótulos de pista de mayor tamaño que los logos sobre jugadores; S11 presenta un encuadre más cercano de ropa. Son ejemplos para revisar en los PNG completos y alrededor del instante señalado. No se ha atribuido todavía una marca ni categoría a esos candidatos.

## 7. Límites y riesgos a comprobar

- Cuatro publicaciones de una cuenta no garantizan cuatro partidos o sesiones independientes. Revisar su procedencia antes de separar train/validation/test; evitar planos de una misma jugada en particiones distintas.
- Los doce frames pueden omitir una aparición breve, una transición o un primer plano importante. Ausencia en la muestra no demuestra ausencia en el vídeo.
- Una impresión de claridad en un frame no determina cuánto tiempo se mantiene clara. Se revisarán los frames vecinos para ese criterio.
- La muestra no es representativa de todo el pádel y no sirve para prometer desempeño general.
- La marca de agua, textos editoriales y gráficos de retransmisión pueden introducir sesgos. Decidir explícitamente qué cuenta como exposición del caso de uso antes de anotar.
- No se ha calculado exposición, entrenado un detector ni validado ningún logo. El porcentaje de ocupación de pantalla sigue siendo una ampliación opcional.

## 8. Historial de decisiones y siguientes pasos

| Fecha | Avance o decisión | Estado |
| --- | --- | --- |
| 20/10/2026 | Consignas, restricciones, progresión por niveles y estructura inicial del proyecto. | Registrado en specs/plan e issues. |
| 21/10/2026 | Entorno `.venv`, instalación de yt-dlp y corrección de su dependencia de solicitudes de navegador. | Descargas realizadas por el usuario; herramientas presentes en el entorno. |
| 21/10/2026 | Cuatro vídeos descargados con metadatos. | Archivos comprobados. |
| 21/10/2026 | Muestra de 12 frames por vídeo y documento de análisis solicitados por el usuario. | Muestra exploratoria generada; revisión inicial del usuario recibida, con problemas de distancia y movimiento. |
| 21/10/2026 | Revisión inicial del usuario: la mayoría de frames muestran jugadores lejanos o poca definición por movimiento. | Observación cualitativa registrada; faltan etiquetas por candidato. |
| Pendiente | Elegir marcas y ejemplos de referencia para categorías 1/2/3. | No decidido. |
| Pendiente | Confirmar permisos, procedencia independiente y material adicional necesario. | No validado. |
| Pendiente | Acordar anotación, particiones y reglas técnicas antes de entrenar. | No iniciado. |

Actualizar este documento con el resultado de cada revisión. Mantener visibles los desacuerdos o cambios de criterio con su motivo; no convertir propuestas en decisiones aprobadas.

## 9. Verificaciones técnicas de la muestra

Generación verificada el 21/10/2026. Se comprobaron cuatro vídeos, 48 PNG y cuatro hojas de contacto. El script decodificó secuencialmente los vídeos y comprobó que el número de frames decodificados coincidía con el indicado por el contenedor; esto no constituye una revisión humana completa ni valida la precisión de timestamps o detección.

| Vídeo | Frames decodificados | FPS informados | Duración estimada frames/FPS | Resolución decodificada | Muestras |
| --- | --- | --- | --- | --- | --- |
| 7507398381900205334 | 2031 | 25 | 81.24 s | 720 × 1280 | 12 |
| 7697683756945280279 | 1413 | 25 | 56.52 s | 1080 × 1920 | 12 |
| 7697932261643128086 | 1450 | 24.761 | 58.56 s | 1080 × 1920 | 12 |
| 7698076371569888534 | 1054 | 25 | 42.16 s | 1080 × 1920 | 12 |

Versiones empleadas:

- opencv-python-headless: 5.0.0.93
- Pillow: 13.0.0
- numpy: 2.4.6

El manifiesto contiene hashes de los vídeos y referencias por frame. Las versiones completas están en requirements-tools.txt. Se verificó la exclusión de data/raw y data/review mediante git check-ignore. La revisión visual conjunta y la selección de marcas permanecen pendientes.

## 10. Revisión del usuario y cambio de selección

El 21/10/2026 el usuario indicó que la mayoría de los frames del piloto no sirven para el objetivo principal: los jugadores aparecen demasiado lejos o el movimiento reduce la definición del logo. Se registra esta conclusión cualitativa sin inventar una tasa de descarte; las 48 imágenes extraídas no equivalen a 48 ejemplos válidos para entrenar. Se conserva el piloto para trazabilidad.

También se acuerda informe principal de ropa/palas e informe secundario de carteles, red y otros soportes estáticos. No mezclar tiempos aunque la marca coincida; una detección en un cartel no acredita exposición sobre un jugador.

Se acuerda aprovechar primero los vídeos actuales y añadir otros si no bastan. La siguiente muestra se dirige a fragmentos con encuadres más cercanos y celebraciones, localizados a partir de las hojas iniciales y comprobaciones puntuales de PNG completos. Su configuración está en review-windows.json; se extrae un candidato cada dos segundos dentro de esos fragmentos. Esto reduce planos generales irrelevantes, pero no garantiza por sí solo nitidez ni validez del logo.

Criterios de revisión de cada candidato:

1. El logo tiene detalle reconocible en la resolución original. Ampliar o recortar no recupera información que no existe.
2. Valorar movimiento, desenfoque, oclusión y tamaño en la zona del logo; un fondo nítido no vuelve legible la ropa.
3. Identificar soporte y categoría 1/2/3 por candidato. La cercanía ayuda a revisar, pero no convierte automáticamente una imagen borrosa en positiva.
4. Conservar ejemplos difíciles para comprobar hipótesis y descarte; no utilizarlos como positivos claros sin evidencia.
5. Seleccionar después ejemplos variados, evitando muchos frames casi idénticos de una misma celebración. Separar por origen antes de entrenar.

La herramienta final analiza un vídeo completo cada vez. La selección de entrenamiento no altera el denominador temporal ni elimina tramos difíciles de la evaluación del producto. El método automático para distinguir soportes, los umbrales y las marcas definitivas siguen pendientes de revisión. No se ha implementado un detector ni calculado exposición.

La muestra dirigida se generó y verificó en data/review/targeted-2026-10-21: 24 candidatos sobre los mismos cuatro vídeos (hashes originales conservados). El piloto de 48 muestras permanece separado. La revisión conjunta por candidato sigue pendiente; los 24 candidatos no se declaran positivos de entrenamiento.

```bash
python scripts/sample_videos.py --windows-file docs/review-windows.json
```

### Resultado técnico y primera observación de la selección dirigida

[Índice local de candidatos](../data/review/targeted-2026-10-21/index.md).

| Vídeo | Candidatos | Hoja |
| --- | --- | --- |
| 7507398381900205334 | 3 | [Hoja](../data/review/targeted-2026-10-21/sheets/7507398381900205334.jpg) |
| 7697683756945280279 | 7 | [Hoja](../data/review/targeted-2026-10-21/sheets/7697683756945280279.jpg) |
| 7697932261643128086 | 3 | [Hoja](../data/review/targeted-2026-10-21/sheets/7697932261643128086.jpg) |
| 7698076371569888534 | 11 | [Hoja](../data/review/targeted-2026-10-21/sheets/7698076371569888534.jpg) |

Se comprobaron existencia de los PNG, hashes de fuente sin cambios y correspondencia entre instantes solicitados y referencias decodificadas (desviación máxima admitida en esta comprobación: 0,15 s). Esta tolerancia comprueba extracción, no precisión de exposición ni claridad del logo.

En el vídeo 7507398381900205334, la nueva hoja todavía contiene un plano general (T01), ropa cercana con detalle limitado (T02) y una toma sin logo de equipación claramente visible (T03). La cercanía de una ventana temporal a una celebración no garantiza candidatos útiles. No declarar positivos claros para este vídeo por obligación de aprovechar los cuatro archivos; puede servir para revisar contexto o descarte y requerir más material para entrenamiento. La clasificación final y las marcas siguen pendientes del usuario.

### Selección preliminar de seis ejemplos de equipación

[Abrir seis candidatos para revisión conjunta](../data/review/targeted-2026-10-21/shortlist.md). Se seleccionan por encuadre, no por etiqueta de marca ni categoría aprobada: vídeo 7697683756945280279 T01/T05, 7697932261643128086 T03, y 7698076371569888534 T02/T06/T09. Faltan ejemplos de pala revisados y aprobados.

La revisión de hojas dirigidas también detecta tomas irrelevantes dentro de una ventana cercana, por cambios de cámara: 7697683756945280279 T06 muestra un espectador sin un logo de equipación de jugador visible. No usarlo como positivo primario. T02 del mismo vídeo y T01 de 7507398381900205334 son planos generales; conservarlos para revisión de dificultad/contexto, sin declararlos positivos claros. Acercar las ventanas temporales mejora la búsqueda, pero no reemplaza la selección por evidencia en la zona del logo.

Los frames de una misma celebración pueden ser casi idénticos. La selección final deberá evitar duplicados y separar fuentes; seis ejemplos de revisión no constituyen un dataset de entrenamiento suficiente ni una estimación de rendimiento.

## 11. Inventario actualizado tras incorporar tres vídeos

El 21/10/2026 el usuario seleccionó vídeos de Agustín Tapia y Arturo Coello y anunció tres incorporaciones. Se comprobaron los archivos y sus metadatos en data/raw/videos. Esta selección manual de contenido no introduce reconocimiento automático de jugadores como funcionalidad.

| ID | Situación | Duración en metadatos | Resolución en metadatos | Fuente |
| --- | --- | --- | --- | --- |
| 7695444675531951382 | Nuevo | 50 s | 1080 × 1920 | [Publicación](https://www.tiktok.com/@premierpadel/video/7695444675531951382) |
| 7695453226648292630 | Nuevo | 34 s | 1080 × 1920 | [Publicación](https://www.tiktok.com/@premierpadel/video/7695453226648292630) |
| 7697671396830317846 | Nuevo | 33 s | 1080 × 1920 | [Publicación](https://www.tiktok.com/@premierpadel/video/7697671396830317846) |
| 7697683756945280279 | Conservado del inventario anterior | 56 s | 1080 × 1920 | [Publicación](https://www.tiktok.com/@premierpadel/video/7697683756945280279) |
| 7698076371569888534 | Conservado del inventario anterior | 42 s | 1080 × 1920 | [Publicación](https://www.tiktok.com/@premierpadel/video/7698076371569888534) |

La carpeta actual contiene cinco MP4 con metadatos. Los archivos 7507398381900205334 y 7697932261643128086 ya no figuran en el inventario actual. Las muestras y observaciones de las secciones anteriores conservan el historial; no representan cinco fuentes actuales ni se deben reutilizar suponiendo que todas sus fuentes siguen disponibles.

No se ha revisado visualmente el contenido completo de los tres nuevos vídeos ni validado su legibilidad. Resolución 1080 × 1920 no garantiza detalle en el logo. El usuario debe indicar o revisar los mejores planos de ropa/palas antes de definir nuevas ventanas de extracción. La configuración review-windows.json corresponde al conjunto anterior y requiere actualización antes de repetir muestreo dirigido sobre la carpeta actual; no restaurar archivos ni descartar los nuevos silenciosamente para hacerla coincidir.

Siguiente decisión: escoger el primer clip y los instantes útiles junto con el usuario, revisar logo/soporte/claridad en resolución original y elegir la primera marca sobre equipación. El objetivo inmediato sigue siendo un dataset piloto anotado para el nivel esencial. Los nuevos archivos aún no son positivos aprobados ni prueba de suficiencia para entrenar; permisos y particiones por origen siguen pendientes.

## 12. Momentos concretos seleccionados por el usuario

El 21/10/2026 el usuario indicó personalmente los instantes que considera más adecuados de los tres vídeos nuevos:

| Vídeo | Selección del usuario | Fotogramas solicitados | Cantidad |
| --- | --- | --- | --- |
| 7695444675531951382 | 35 s y 49 s | 35, 49 | 2 |
| 7695453226648292630 | 13–16 s y 23–30 s | Cada segundo, incluyendo extremos | 12 |
| 7697671396830317846 | 25 s, 27 s y 29 s | 25, 27, 29 | 3 |

Se extrajeron y verificaron 17 PNG a resolución completa, con tres hojas de contacto y [un índice local](../data/review/player-moments-2026-10-21/index.md). Esta selección sustituye el criterio temporal exploratorio por instantes aportados por el usuario; la aprobación de un instante no aprueba automáticamente cada logo como categoría 1.

Configuración versionable: review-player-moments.json. El script acepta seleccionar un subconjunto explícito de vídeos y deja intactos los otros dos archivos actuales y las muestras anteriores. Usa el primer frame decodificado en o después del instante solicitado; el manifiesto registra petición, referencia real, frame, dimensiones y hash del vídeo. Se verificaron conteos, correspondencia temporal y existencia de las imágenes; la tolerancia técnica de extracción de 0,15 s no es una tolerancia acordada para medir exposición.

```bash
python scripts/sample_videos.py --review-plan docs/review-player-moments.json
```

Próxima revisión conjunta: identificar por logo el soporte (ropa/pala/estático), marca candidata y claridad (1/2/3), excluyendo público del informe principal. Después elegir la primera marca y anotar sus cajas. Los frames cercanos de una misma escena no se deben repartir entre entrenamiento y evaluación; estos 17 candidatos todavía no forman un dataset suficiente ni validado.

## 13. Primer ejemplo aprobado y referencias estáticas de camisetas

El 21/10/2026 el usuario confirmó que el logo NOX de la camiseta en el vídeo 7697671396830317846, segundo 29, frame 725 (muestra T03), cumple la categoría 1. La decisión se limita a ese logo en esa imagen; no valida todos los logos del frame, no fija el listado final de clases y no demuestra desempeño del detector. La caja sigue pendiente de anotación. Registro estructurado y hash del PNG: review-decisions.json.

El usuario propone utilizar fotos estáticas de camisetas oficiales como referencia para reconocer todos los patrocinadores. Se consultaron las fichas aportadas, con estos resultados:

| Referencia aportada | Información verificada en la ficha | Uso y límites |
| --- | --- | --- |
| [NOX Sponsors AT10 rojo](https://noxsport.com/products/camiseta-sponsors-at10-red) | La ficha identifica la colección 2026 y menciona Qatar Airways, Commvault y NFA entre sus patrocinadores. | Referencia candidata de nombres y variantes. No es un inventario visual exhaustivo; contrastar temporada y distribución con el vídeo. |
| [HEAD Arturo Coello Black SS26, Decathlon Marketplace](https://www.decathlon.es/es/p/mp/head-arturo-coello-black-ss26-camiseta-oficial/857dff3e-775a-4cd7-af66-e00f2645efdb/c1) | La ficha corresponde a una camiseta negra 2026 de HEAD, vendida por Padel Market, y declara que incluye logos de patrocinadores sin enumerarlos en el texto. | Referencia candidata para la equipación. No asumir que la versión naranja/roja del vídeo tenga exactamente los mismos logos, colores de impresión o posiciones. |

Alcance de consulta: se leyeron ambas fichas. El acceso a las imágenes de la galería de Decathlon falló en la herramienta; todavía no se han inspeccionado visualmente todos los logos de ambos productos. No se descargaron imágenes de catálogo ni se incorporaron al dataset.

Propuesta de uso para revisar con el usuario: construir un pequeño catálogo de referencia con marca, variante de logo, posición en prenda, temporada/color, fuente y estado de confirmación en vídeo. Separar tres evidencias: marca mencionada por la ficha, logo observado en una foto de producto y aparición validada en un frame del vídeo. Ninguna de ellas sustituye a las otras.

El catálogo puede orientar la anotación y ayudar a reconocer fragmentos, pero no permite inventar exposición de un logo oculto, borroso o ausente. Conocer quién patrocina al jugador no convierte una hipótesis de categoría 2 en exposición clara. Se conserva la política principal/secundaria por soporte.

El entrenamiento y la evaluación seguirán necesitando ejemplos reales variados de vídeo (movimiento, pliegues, tamaño, iluminación y oclusiones). Si se decide añadir imágenes de catálogo como complemento, acordar antes su uso y verificar permisos; las versiones de una misma foto no deben repartirse entre entrenamiento y evaluación. Buscar todas las referencias no compromete entrenar todas las marcas dentro de los ocho días: el listado final de clases se decidirá con el usuario después del inventario.

## 14. Inventario visual de camisetas y segunda etapa con Instagram

El 21/10/2026 el usuario solicita registrar los sponsors identificados como guía de búsqueda en vídeo y propone complementar el material con Instagram oficial de los jugadores en una segunda etapa.

Se crea [el catálogo de referencias de camisetas](sponsor-reference.md), con nombres, variantes gráficas, posiciones, fuentes de catálogo y frames locales. Se inspeccionaron ahora las imágenes de ambas galerías en el navegador, ampliando la consulta de texto y el fallo inicial de acceso descritos en la sección 13. Se identifican NOX, Qatar Airways, Commvault, NFA, CUPRA, HEAD y Alpine en las fuentes indicadas; Premier Padel se distingue como identificador del circuito. No todas las marcas están confirmadas en vídeo. Los textos incompletos se dejan sin atribución.

Las variantes difieren: el catálogo NOX presenta NFA en una manga, mientras que una camiseta del vídeo presenta CUPRA; el frontal de catálogo incluye un gran Qatar Airways ausente del frame NOX aprobado. La camiseta negra HEAD muestra Alpine, sin demostrar su presencia en la naranja. La referencia orienta la revisión, sin completar logos ausentes por conocimiento previo del sponsor.

Solo se mantiene la aprobación explícita de categoría 1 para NOX en el segundo 29 del vídeo 7697671396830317846. El resto del inventario no añade aprobaciones, anotaciones ni segundos de exposición. No se descargaron imágenes de catálogo ni se cambió el listado definitivo de clases.

Instagram queda registrado como ampliación de fuentes para una segunda etapa: confirmar cuentas/enlaces y condiciones de uso; revisar utilidad real; agrupar reposts y tomas del mismo origen antes de particionar; evaluar con el mismo criterio por soporte y claridad. No se han descargado vídeos ni iniciado integración con Instagram. No se amplía el plazo ni se añaden tarjetas al backlog.

## 15. NOX elegida como primera marca y piloto de cajas

El 21/10/2026 el usuario aprueba empezar con NOX para el nivel esencial. Se actualiza la selección de primera marca en las especificaciones; modelo, herramienta de anotación y marcas adicionales siguen pendientes.

Se prepara [un piloto de tres ejemplos](nox-pilot-review.md), con dos cajas manuales propuestas sobre pecho y espalda y un caso movido para contrastar el criterio de claridad. Se revisaron los originales a resolución completa, verificaron hashes/dimensiones y límites de cajas, y se inspeccionó la comparación de recortes a escala 1:1. Las cajas no proceden de un modelo ni tienen aprobación del usuario todavía.

El frame 725 del vídeo 7697671396830317846 conserva la categoría 1 ya aprobada; su caja propuesta es nueva. Los otros dos ejemplos mantienen claridad pendiente de revisión. La propuesta de categoría 2 para el ejemplo movido es provisional, no una decisión del usuario. review-decisions.json permanece intacto. No hay exportación de etiquetas, particiones ni entrenamiento. El piloto fija criterio antes de ampliar anotaciones y no acredita suficiencia del dataset.

## 16. Lote local para CVAT y validación de procedencia

El 21/10/2026 el usuario acepta la propuesta de herramientas y autoriza preparar el siguiente bloque. Se añade scripts/prepare_annotation_batch.py y [la guía de anotación en CVAT](cvat-nox-guide.md), reutilizando el entorno existente sin instalar dependencias adicionales.

Se genera data/review/nox-cvat-pilot-2026-10-21/images.zip con tres PNG completos del piloto, conservando sus bytes, y un manifiesto con hashes de imágenes/vídeos, procedencia, frame, segundo, dimensiones y estados de revisión. Las propuestas no se convierten en etiquetas de entrenamiento. No se asignan particiones ni se cambian review-decisions.json o nox-pilot.json.

Se verifican integridad, correspondencia con manifiestos de extracción y vídeos actuales, duplicados exactos y límites de cajas. Nueve pruebas automatizadas comprueban conservación de originales y estados pendientes, rechazo de imagen/vídeo alterados, duplicados, caja inválida, timestamp incorrecto, comprobación sin escritura y protección de destinos existentes o fuera de data/review. No evalúan nitidez ni duplicados visuales entre clips editados.

CVAT usará clase nox y atributos de revisión visibility/support. Conservar exportación CVAT con atributos además de YOLO, que no los conserva. La clasificación de claridad y soporte no se aprende automáticamente con una clase de detector. Pendientes: revisar condiciones de uso antes de carga externa, crear la tarea de anotación, revisar cajas/claridad y ampliar ejemplos. No se subió contenido a CVAT, no se entrenó y el piloto no acredita suficiencia del dataset. La adopción de licencia, configuración y prueba de recursos de entrenamiento siguen pendientes.

## 17. Primera exportación de anotaciones CVAT guardada

El 22/10/2026 el usuario informa de que revisó y guardó sus anotaciones. Exportó el trabajo 4626112 en formato CVAT for images 1.1 sin imágenes, después de resolver el aviso de upgrade por incluirlas. Autoriza expresamente la descarga y guardado local.

Se conserva el ZIP original, annotations.xml, verification.json y README.md en data/review/nox-cvat-pilot-2026-10-21/exports/2026-10-22-job-4626112. Se verificaron integridad del ZIP, referencias a tres imágenes originales, hashes/dimensiones, cuatro cajas dentro de límites y valores de clase/atributos. La copia de Descargas se conserva. No se modificaron las anotaciones ni review-decisions.json.

Resultado exportado: N01 tiene una caja clear/clothing; N02 tiene una pending/unknown y otra possible/paddle; N03 tiene una possible/clothing. La segunda caja de N02 corresponde visualmente al logo de espalda de la camiseta, por lo que debe revisarse support con el usuario. También queda pendiente revisar la primera caja de N02. La validación estructural pasa; la revisión semántica sigue abierta. No hay conversión a YOLO, particiones ni entrenamiento. Tres imágenes siguen siendo un piloto.

## 18. Revisión CVAT, respaldo y ampliación local — 23/10/2026

El usuario delega las correcciones de atributos. Se registra el resultado y sus límites en [la revisión del 23](cvat-review-2026-10-23.md). Exportación nueva verificada: tres imágenes, cuatro cajas, hashes/dimensiones correctos, coordenadas conservadas y atributos esperados. Se inspeccionaron los PNG originales. N01 y espalda N02 quedan claras; pala N02 pendiente; N03 posible. No se generaron etiquetas de entrenamiento.

Se prepara un lote local de doce candidatos de cinco vídeos con originales intactos, ZIP y procedencia; no hay positivos/negativos aprobados ni particiones. Las escenas compartidas y las condiciones del material siguen pendientes. Se añaden scripts reproducibles para preservar/verificar la exportación y reconstruir esta selección. Los medios y XML quedan bajo data/review, excluido de Git. Siguiente paso: revisar y anotar las doce imágenes antes de entrenar.

## 19. Revisión delegada del lote de doce candidatos — 23/10/2026

Se revisaron las doce imágenes originales a 1080 por 1920 y detalles a escala nativa. Resultado: E05 (muñequera) y E08 (pecho) son positivos claros con una caja cada uno; E02/E04/E07/E09/E11 son negativos visuales revisados, sin logo NOX visible identificado; E01/E03/E06/E10/E12 quedan excluidos por ambigüedad, movimiento u oclusión. Son decisiones de revisión del asistente por delegación, no aprobaciones humanas individuales ni resultados de un modelo. [Decisiones y cajas](nox-expansion-review-2026-10-23.json).

Se añade scripts/render_nox_review.py para validar referencias, hashes, dimensiones, decisiones y cajas, y generar vistas anotadas, XML CVAT y ZIP local de las siete imágenes retenidas. Salida: data/review/nox-expansion-reviewed-2026-10-23, excluida de Git. Se verificaron integridad del ZIP, hashes de las siete imágenes y conteo de XML: siete imágenes y dos cajas. Las dos vistas anotadas se inspeccionaron a resolución original. No se probó la importación en CVAT ni se subió este lote. Las nueve pruebas previas siguen pasando; validan el preparador del piloto, no la exactitud visual de esta revisión.

Reproducción con originales presentes: python scripts/render_nox_review.py. El programa rechaza una carpeta de salida existente. No hay particiones ni entrenamiento; dos positivos nuevos no constituyen un dataset suficiente. Falta ampliar variedad de positivos y comprobar grupos de origen independientes y condiciones del material antes de entrenar. Evitar multiplicar frames casi iguales para aparentar tamaño o repartirlos entre evaluación y entrenamiento.

## 20. Instantes y capturas aportados por el usuario — 26/10/2026

El usuario señala NOX en 1, 2, 13, 16 y 28–33 s de ropa, y 9/25 s de pala, con siete capturas como orientación. Se extraen los doce instantes originales, sin usar capturas reescaladas como datos. Se decodificaron 847 frames a 25 FPS; duración estimada 33,88 s, por lo que 33 s es accesible. Se comprobaron referencias temporales (desfase máximo permitido de un frame, 0,041 s), dimensiones y hashes. [Selección exacta](review-user-moments-2026-10-26.json).

Se preparan 21 candidatos adicionales a +0,24/+0,48/+0,72 s en siete instantes para localizar las apariciones de las capturas. Se inspeccionan los doce originales exactos y cuatro vecinos (1,72; 16,48; 16,72; 28,48 s) a escala nativa; el resto de vecinos solo se navega mediante hoja de contacto. [Configuración de vecinos](review-neighbor-moments-2026-10-26.json).

Resultado registrado: siete muestras de ropa identificables con cajas verificadas (1,72; 28,48; 29; 30; 31; 32; 33 s). El segundo 29 ya es N01: seis frames claros nuevos, sin contar ese duplicado. Seis pertenecen al mismo primer plano y no constituyen escenas de evaluación independientes. El frame 25 coincide con E06, pero la observación del usuario se refiere específicamente a la pala: se conserva esa nueva indicación sin recontar la imagen. Las palas 9/25 se mantienen pendientes de contraste visual de su variante gráfica; una descripción de producto oficial consultada no sustituye la comparación de fotos. No se han aprobado negativos ni medido exposición en este bloque. [Decisiones y cajas](review-user-moments-decisions-2026-10-26.json).

Se conservan los PNG originales, manifiestos, vistas anotadas e índice local en data/review/user-moments-reviewed-2026-10-26 y las dos carpetas de extracción; todo bajo data/review excluido de Git. Se inspeccionaron los detalles anotados a tamaño original y se verificaron siete cajas dentro de 1080 por 1920. No hay particiones, etiquetas YOLO, subida a CVAT ni entrenamiento.

Reproducción de las extracciones desde el repositorio: python scripts/sample_videos.py --review-plan docs/review-user-moments-2026-10-26.json y python scripts/sample_videos.py --review-plan docs/review-neighbor-moments-2026-10-26.json. El muestreador existente reconstruye estas rutas y puede sobreescribir su salida: usar una carpeta/proyecto de reproducción distinto para conservar los artefactos actuales. La revisión visual y las coordenadas se preservan en el JSON; las capturas del usuario no se publican.
