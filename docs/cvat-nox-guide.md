# Primer lote de anotación de NOX en CVAT

T04 — nivel esencial. Flujo acordado con el usuario el 21/10/2026: Python/venv, OpenCV/Pillow, CVAT gratuito y primer detector YOLO11n; entrenamiento en Colab gratuito sujeto a disponibilidad. La prueba del entorno de entrenamiento, configuración concreta y adopción de la licencia del proyecto siguen pendientes. Este bloque prepara datos locales; no instala el detector ni inicia entrenamiento.

## Resultado de este bloque

- Script: scripts/prepare_annotation_batch.py.
- Fuente de selección: [nox-pilot.json](nox-pilot.json), con tres ejemplos de pecho/espalda/movimiento.
- Salida local: data/review/nox-cvat-pilot-2026-10-21/images.zip, tres imágenes completas sin alteraciones ni etiquetas importadas.
- Manifiesto de salida: dimensiones, hash de imagen/vídeo, frame, segundo, URL, estado de revisión y propuestas anteriores; ninguna partición de entrenamiento asignada.
- Las imágenes y el ZIP permanecen bajo data/review, excluido de Git. No se subió contenido a CVAT.

Es un lote para aprender el flujo y acordar criterio. Tres imágenes no bastan para demostrar entrenamiento o rendimiento. N01 conserva su claridad aprobada; todas las cajas y la claridad de N02/N03 siguen pendientes del usuario.

## Comprobar o reconstruir desde Git Bash

Con el entorno .venv activado, desde la raíz del repositorio:

```bash
python scripts/prepare_annotation_batch.py --check-only --output data/review/nox-cvat-check
```

La comprobación no crea archivos. Verifica que cada imagen coincide con su hash y manifiesto de extracción; comprueba también el hash del vídeo original, dimensiones, referencia temporal, límites de cajas propuestas y duplicados exactos. No evalúa automáticamente la nitidez ni detecta duplicados visuales entre clips editados.

El lote predeterminado ya está preparado. Para reproducirlo en otra carpeta nueva:

```bash
python scripts/prepare_annotation_batch.py --output data/review/nox-cvat-rebuild
```

El programa rechaza carpetas de salida existentes para conservar revisiones anteriores. No borra ni reemplaza lotes. Necesita los originales, los manifiestos de extracción y las dependencias de requirements-tools.txt.

Pruebas:

```bash
python -m unittest discover -s tests -p 'test_prepare_annotation_batch.py' -v
```

## Configuración del piloto en CVAT

Preparación local no implica permiso para subir o redistribuir retransmisiones. Las condiciones de uso del material siguen pendientes de registrar antes de cargarlo en un servicio externo. No se ha realizado esa carga en este bloque.

1. Acceder a [CVAT Online](https://app.cvat.ai/) con el plan gratuito.
2. Crear un proyecto llamado **Padel Sponsor Detection**, con una etiqueta **nox** para rectángulos. Mantener una sola clase de marca.
3. Añadir dos atributos de tipo selección a esa etiqueta:

   | Atributo | Valores | Valor inicial |
   | --- | --- | --- |
   | visibility | pending, clear, possible | pending |
   | support | unknown, clothing, paddle, static | unknown |

4. Crear una tarea del proyecto llamada **NOX annotation pilot 01** y seleccionar el ZIP local images.zip. Contiene tres PNG originales a 1080 × 1920; no subir la hoja comparativa ni recortes como sustituto de los originales.
5. Abrir el trabajo de anotación. Los nombres N01/N02/N03 permiten relacionarlo con [la revisión del piloto](nox-pilot-review.md). Dibujar rectángulos en modo de formas para imágenes; no usar interpolación temporal entre estos fotogramas aislados.

Referencia oficial: [proyectos y etiquetas](https://docs.cvat.ai/docs/workspace/projects/), [anotación con rectángulos](https://docs.cvat.ai/docs/annotation/manual-annotation/shapes/annotation-with-rectangles/).

## Cómo anotar

- Rodear el logo completo visible con poco fondo. Revisar el original al 100 %: ampliar facilita dibujar, pero no recupera detalle. Las coordenadas propuestas están en píxeles de la imagen completa.
- Revisar todas las apariciones de NOX en la imagen completa y registrar su soporte; un NOX en red/cartel no es una aparición en camiseta. Los ejemplos de pecho y espalda no aprueban el resto del frame.
- **clear** corresponde a categoría 1 aprobada por el usuario; **possible** a categoría 2 y no acredita exposición. **pending** se conserva mientras falte criterio humano. La elección de estas opciones no es una predicción del detector.
- Categoría 3: no asignar NOX a un logo que no se puede identificar. Registrar el descarte y motivo en la revisión, sin convertir el caso en positivo ni en imagen negativa revisada automáticamente.
- No confundir N03 con un negativo solo por ser borroso. El usuario todavía debe decidir su claridad. Conservar la revisión completa permite decidir después si se excluye la imagen o cómo se tratan regiones ambiguas, sin enseñar al detector que un logo conocido es fondo.
- Los atributos documentan evidencia y soporte; el entrenamiento de una clase no aprenderá automáticamente a distinguir claridad ni equipación/carteles. Ese método sigue pendiente de diseño y evaluación.
- Guardar el trabajo en CVAT tras revisar cada imagen. La categoría clara de N01 estaba aprobada; aprobar su caja constituye una revisión distinta.

## Exportación que debemos conservar

Después de la revisión, guardar las exportaciones dentro de una subcarpeta de data/review:

1. **CVAT for images**, que conserva cajas y atributos de revisión.
2. **Ultralytics YOLO Detection**, como formato candidato de entrenamiento. El formato YOLO no conserva estos atributos; no utilizar directamente todo el export como positivos.

Referencias oficiales: [formato CVAT](https://docs.cvat.ai/docs/dataset_management/formats/format-cvat/) y [formato Ultralytics YOLO](https://docs.cvat.ai/docs/dataset_management/formats/format-yolo-ultralytics/). El plan gratuito exporta anotaciones; conservamos localmente las imágenes para emparejarlas por nombre.

El siguiente bloque contrastará cajas, categorías y nombres con los originales antes de preparar etiquetas de entrenamiento. Después ampliaremos la muestra y revisaremos grupos de origen: N02/N03 pertenecen a una misma escena, y vídeos distintos pueden repetirla. No generar train/validation/test aleatorio por frame ni contar estos tres ejemplos como dataset suficiente.
