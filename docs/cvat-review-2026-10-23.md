# Revisión del piloto NOX — 23/10/2026

El usuario delega la revisión visual y corrección de atributos para avanzar. Trabajo: https://app.cvat.ai/tasks/2694276/jobs/4626112.

| Imagen | ID en CVAT | Claridad | Soporte | Resultado |
| --- | --- | --- | --- | --- |
| N01 | 1 | clear | clothing | Se comprueban atributos y caja sobre el logo del pecho; sin cambios. |
| N02 | 2 | pending | paddle | Se cambia support de unknown a paddle según la zona y la aclaración del usuario. La identidad visual del logo sigue sin confirmarse. |
| N02 | 3 | clear | clothing | Se corrige support de paddle a clothing y visibility de possible a clear: logo legible en la espalda. |
| N03 | 4 | possible | clothing | Se conserva como posible por desenfoque de movimiento. |

Se pulsó Save en CVAT y se comprobaron los valores resultantes de N02. No se eliminaron ni movieron cajas. La recomendación anterior de eliminar ID 2 queda descartada: la región incluye la pala.

Esta revisión no crea un dataset de entrenamiento. No tratar pending/possible como positivos claros ni como negativos. N02 contiene una región ambigua: decidir su tratamiento antes de incorporarla al entrenamiento. Las coordenadas no se revisaron a resolución nativa en este bloque; la revisión visual se realizó en la vista ajustada de CVAT. La exportación local del 22/10 permanece como historial y no refleja estos cambios; se necesita una nueva exportación antes de convertir etiquetas.

Siguiente bloque: ampliar ejemplos variados y negativos revisados, registrar grupos de origen y resolver el tratamiento de imágenes con regiones ambiguas antes de particionar y entrenar.

## Verificación y respaldo posteriores

Se inspeccionaron los tres PNG originales a 1080 × 1920 y se contrastaron con las coordenadas exportadas. N01 contiene el logo del pecho; la caja de espalda de N02 contiene el logo legible con margen vertical amplio. N03 mantiene desenfoque y categoría posible; la zona de pala de N02 sigue sin identificación segura. No se estrecharon las cajas ni se aprobaron regiones ambiguas.

Se descargó nox-pilot-cvat-2026-10-23.zip y se conservó una copia exacta en data/review/exports/nox-cvat-export-2026-10-23, con XML y verification.json. Verificación ejecutada con verify_cvat_revision.py: ZIP íntegro, tres referencias únicas, hashes y dimensiones de originales coincidentes, cuatro cajas válidas, atributos esperados y coordenadas idénticas a la exportación anterior. La exportación del 22 no se altera. El XML puede contener metadatos de cuenta: data/review está excluido mediante .gitignore.

Se prepara data/review/nox-expansion-2026-10-23 con 12 imágenes de cinco vídeos, images.zip, README y manifiesto de procedencia. Se reutilizan extracciones existentes sin alterar los PNG; se verificaron hashes, ausencia de duplicados exactos e integridad del ZIP. La selección de candidatos procede de hojas de contacto; no aprueba claridad, cajas ni negativos. No se ha subido el lote, asignado particiones o iniciado entrenamiento. Distintos vídeos no equivalen necesariamente a escenas o partidos independientes. Las condiciones del material siguen pendientes de registrar antes de nuevas cargas o entrenamiento.

## Reproducción local

Ejecutar desde la raíz del repositorio con el entorno activo:

python scripts/verify_cvat_revision.py
python scripts/prepare_nox_expansion.py

El verificador necesita el ZIP del 23 en Descargas, el lote original y la exportación del 22. El preparador necesita las extracciones existentes y sus manifiestos. Ambos rechazan destinos existentes. Las salidas actuales se copiaron a estas rutas ignoradas conservando sus bytes; no se publican los medios ni el XML. Sin los archivos locales autorizados, un clon por sí solo no reconstruye estos lotes.
