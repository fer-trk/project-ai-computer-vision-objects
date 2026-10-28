# Tanda local de candidatos para variantes NOX — 28/10/2026

Se prepararon **50 fotogramas candidatos adicionales** de los cinco vídeos locales, tras examinar 219 instantes. No son 50 positivos nuevos ni se añaden automáticamente a las 18 imágenes utilizables del ensayo. Todas las clases, cajas y particiones de estos candidatos permanecen pendientes.

El usuario desactivó Data Licensing and Model Training en Roboflow; se comprobó en la interfaz el estado Off. Esto no acredita permisos de uso de los vídeos ni sustituye su registro. El proyecto y las clases existen, pero esta tanda no se subió a servicios externos.

## Preparación y verificación

`python scripts/prepare_nox_variant_candidates.py` desde la raíz del repositorio. Usa los vídeos originales y sus metadatos, el inventario revisado y los grupos existentes. Rechaza sobrescribir `data/review/nox-variant-candidates-2026-10-28/`.

El proceso decodifica progresivamente sin cargar vídeos completos en RAM. Considera un fotograma cerca de la mitad de cada segundo y selecciona por turnos entre vídeos, hasta diez por vídeo, con al menos 1,5 s entre seleccionados del mismo vídeo. Usa DCT de 63 bits para exigir distancia Hamming mayor que ocho frente a las 40 imágenes revisadas y los candidatos ya elegidos. Es un filtro de parecido de la imagen completa, no una medida de legibilidad del logo ni prueba de escenas independientes; también puede descartar imágenes útiles parecidas.

Se verificaron los hashes de las 40 referencias y de los metadatos; conteo completo de frames decodificados por vídeo; reproducción del fingerprint al extraer; hashes de los 50 PNG finales; ausencia de duplicados exactos respecto al inventario y dentro del lote. Los 50 candidatos conservan vídeo, hash del vídeo, frame, dimensiones, grupo provisional y hash de imagen. Los tiempos se estiman por FPS, no miden exposición.

Distribución por vídeo: `{"7695444675531951382": 10, "7695453226648292630": 10, "7697671396830317846": 10, "7697683756945280279": 10, "7698076371569888534": 10}`. Pasaron las 16 pruebas automatizadas: las 14 existentes y dos sobre exclusión por similitud y restricciones temporales/cupo. La selección automática no aprueba ninguna etiqueta.

## Archivos y revisión siguiente

Originales, hojas de contacto e índice: `data/review/nox-variant-candidates-2026-10-28/`. Manifiesto sin medios: [selección y procedencia](nox-variant-candidates-2026-10-28.json). Las imágenes no se publican en Git.

Revisar las hojas para localizar candidatos y después los PNG a tamaño original para decidir `nox_texto`, `nox_simbolo`, negativo revisado o pendiente. Anotar todas las impresiones identificables de cada imagen y excluir ambigüedades sin convertirlas en negativas. Aplicar [la guía de variantes](nox-variant-labeling.md).

El lote procede de los mismos dos grupos provisionales, Germany P2 y Milano P1. No incorpora partidos nuevos ni resuelve el test independiente. La ampliación hacia 200–300 originales seguirá necesitando nuevos orígenes y variedad; no aumentar por copias o fotogramas casi idénticos. Antes de una nueva subida, registrar condiciones de uso/permisos. No se crean etiquetas YOLO ni se reentrena en este paso.

Se inspeccionaron las cinco hojas de contacto: contienen primeros planos, tomas lejanas y público. Esta inspección orienta la siguiente revisión; no aprueba logos pequeños desde miniaturas ni convierte los 50 candidatos en 50 positivos. Incluso los candidatos que pasan el filtro pueden pertenecer a la misma escena que imágenes ya revisadas.
