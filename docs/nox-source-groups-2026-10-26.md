# Procedencia y grupos para evitar fugas — 26/10/2026

Paso completado: auditar la procedencia de las 40 imágenes únicas revisadas y proponer grupos conservadores que deben mantenerse juntos. No se han creado particiones, convertido etiquetas ni entrenado un modelo.

## Resultado

| Grupo provisional | Vídeos | Imágenes revisadas | Positivas sin ambigüedad registrada | Negativas | Pendientes/excluidas |
| --- | --- | --- | --- | --- | --- |
| Germany P2 | 2 | 5 | 1 | 2 | 2 |
| Milano P1 | 3 | 35 | 12 | 3 | 20 |
| Total | 5 | 40 | 13 | 5 | 22 |

La agrupación utiliza los hashtags de procedencia de los `.info.json` locales: `#GermanyPremierPadelP2` y `#OyshoMilanoPremierPadelP1`. Los dos vídeos del primer grupo indican publicación el 11/10/2026; los de Milano indican 17/10/2026 y 18/10/2026. Son fechas de publicación en los metadatos, no fechas verificadas de partidos.

Esto establece una regla conservadora de separación, no demuestra por sí solo la identidad de cada partido ni descarta montajes con tomas reutilizadas. Cada grupo se mantiene íntegro hasta contar con evidencia para subdividirlo. No se asignan todavía etiquetas train/validation/test.

## Comprobaciones y evidencia

- Se verificaron los SHA-256 de las 40 imágenes contra el inventario y sus dimensiones originales (1080 × 1920). El inventario conserva 40 hashes únicos; las revisiones repetidas ya estaban consolidadas.
- Se comprobaron los identificadores y hashes de los cinco archivos de metadatos. Todas las imágenes tienen correspondencia con un único grupo propuesto.
- Se compararon 543 parejas entre vídeos mediante hash perceptual DCT de imagen completa (63 bits, umbral de distancia Hamming ≤ 8). Se señaló una pareja, dentro de Milano, y ninguna entre los grupos propuestos.
- Se inspeccionó visualmente esa pareja: vídeo 7697671396830317846, frame 43 (1,72 s), frente a vídeo 7697683756945280279, frame 300 (12 s). Comparten encuadre/pista, pero las posiciones de jugadores y el fotograma son distintos. No se confirma un duplicado ni se elimina ninguna imagen.

El hash perceptual sirve para descubrir candidatos. Una distancia baja no demuestra que se repita una toma; una distancia alta no prueba independencia ni detecta todas las transformaciones, recortes o cambios de cámara. El resultado no justifica repartir aleatoriamente los frames.

## Consecuencia para el siguiente paso

Hay dos grupos provisionales, no cinco orígenes independientes demostrados. Con estos dos grupos indivisibles no pueden formarse tres particiones no vacías e independientes de entrenamiento, validación y test.

Se puede preparar un ensayo exploratorio con separación en dos grupos y reconocer que falta un test independiente. Para la evaluación final hará falta un tercer origen confirmado, o evidencia suficiente que permita subdividir por partidos/sesiones sin fugas. Esta revisión no modifica ese requisito ni aprueba el ensayo como entrega final.

Las 13 imágenes positivas están muy concentradas: 12 pertenecen al grupo Milano y solo una al grupo Germany. El tamaño y el cambio de soporte (camiseta/muñequera) limitan lo que pueda concluirse de un primer ensayo. Las 22 imágenes pendientes/excluidas conservan su estado; no se convierten en negativos.

## Archivos y reproducción

- Inventario de entrada: `docs/nox-review-inventory-2026-10-26.json`.
- Informe por imagen, hashes de fuentes y parejas candidatas: `docs/nox-source-groups-2026-10-26.json`.
- Script: `scripts/audit_nox_groups.py`.

Con los originales y metadatos locales presentes, ejecutar desde la raíz del repositorio:

```bash
python scripts/audit_nox_groups.py
```

La ejecución escribe únicamente el informe JSON y no modifica imágenes, anotaciones ni el inventario. La comparación visual de la pareja candidata se registra en este documento, separada del resultado automático. Los medios permanecen en las carpetas ignoradas.
