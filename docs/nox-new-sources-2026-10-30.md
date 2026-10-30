# Ampliación NOX con nueve vídeos nuevos — 30/10/2026

Fernanda seleccionó nueve publicaciones de TikTok para ampliar variedad de
camisetas, colores y escenas. Se descargaron en local con el entorno existente,
sin cookies de navegador ni autenticación, y se extrajeron **108 candidatos**:
12 PNG a resolución original por vídeo. No son 108 positivos ni un dataset
anotado: la clasificación completa, las cajas y las particiones siguen pendientes.
El ensayo histórico conserva sus 18 imágenes y su clase única; no se sobrescribió.

## Acceder a la tanda local

Desde la raíz de esta rama:

- `data/raw/videos/`: nueve MP4 y sus metadatos originales.
- `data/review/nox-new-sources-2026-10-30/index.md`: índice por vídeo e instante.
- `data/review/nox-new-sources-2026-10-30/sheets/`: nueve hojas de contacto.
- `data/review/nox-new-sources-2026-10-30/frames/`: originales, separados por ID.

Las miniaturas ayudan a localizar tomas. La decisión sobre un logo se hace en el
PNG original. Los medios permanecen excluidos de Git; no se subieron a Roboflow.

## Fuentes y prioridad de revisión

Las fechas proceden de metadatos de descarga. Los grupos se infieren de la
descripción/hashtags y fecha; no identifican partidos ni prueban independencia.
La atribución del perfil `agustin.tapia2` se conserva como fuente seleccionada
por la usuaria, sin afirmar aquí una verificación independiente de su oficialidad.

| Vídeo | Publicación según metadatos | Grupo provisional | Observación en la hoja de contacto |
| --- | --- | --- | --- |
| [7570843031901883670](https://www.tiktok.com/@agustin.tapia2/video/7570843031901883670) | 09/11/2025 | Kuwait 2025 | Ropa negra; vistas frontal/posterior y últimos planos más cercanos. |
| [7695117320800259350](https://www.tiktok.com/@premierpadel/video/7695117320800259350) | 10/10/2026 | Germany P2, mismo grupo conservador previo | Ropa roja/morada, acción lejana y publicidad estática; no asumir que son negativos sin revisar todo NOX visible. |
| [7696547391893212438](https://www.tiktok.com/@premierpadel/video/7696547391893212438) | 14/10/2026 | Milano P1, mismo grupo conservador previo | Ropa negra, acción lejana y primeros planos parciales/ocultos. |
| [7696886990255476001](https://www.tiktok.com/@premierpadel/video/7696886990255476001) | 15/10/2026 | Milano P1, mismo grupo conservador previo | Ropa verde/negra, acción y planos de cara; utilidad del logo pendiente. |
| [7700661233569041687](https://www.tiktok.com/@premierpadel/video/7700661233569041687) | 25/10/2026 | Kuwait 2026 provisional | Escena de entrenamiento con ropa negra; muchas muestras pertenecen al mismo plano. |
| [7701024496504835350](https://www.tiktok.com/@premierpadel/video/7701024496504835350) | 26/10/2026 | Kuwait 2026 provisional | Ropa clara y oscura, marcas distintas y acción lejana; revisar sin atribuir NOX por jugador o camiseta. |
| [7701662392148593942](https://www.tiktok.com/@premierpadel/video/7701662392148593942) | 28/10/2026 | Kuwait 2026 provisional | Ropa clara y un primer plano final de tejido oscuro con texto NOX naranja. |
| [7702209547183721750](https://www.tiktok.com/@premierpadel/video/7702209547183721750) | 29/10/2026 | Kuwait 2026 provisional | Plano final de camiseta negra con hombros blancos y texto NOX blanco. |
| [7702355729411247382](https://www.tiktok.com/@premierpadel/video/7702355729411247382) | 30/10/2026 | Kuwait 2026 provisional | Vistas de pista y primeros planos de camiseta blanca con otras marcas; candidatos a revisar, no negativos aprobados. |

Se inspeccionaron las nueve hojas. Además se abrieron a tamaño original
`7701662392148593942/T01`, `7701662392148593942/T12` y
`7702209547183721750/T12`. La primera tiene oclusión/desenfoque; no convertirla
automáticamente en negativa. Las otras dos muestran las variantes de color del
texto descritas arriba; esto no aprueba todas sus regiones ni crea cajas finales.

## Comprobaciones

- Nueve IDs nuevos respecto a los cinco vídeos previos; archivos completos
  decodificados por el preparador: **6.789 frames** en total.
- **108 PNG distintos por SHA-256**, dimensiones comprobadas y referencias a
  vídeo, frame, instante y fuente conservadas.
- Sin duplicados exactos respecto a las 40 imágenes revisadas y los 50 candidatos
  del 28/10. Esto no detecta todas las escenas repetidas o casi idénticas.
- Todos los originales son de **1080×1920**. La resolución no garantiza legibilidad.
- Sin cambios de código de preparación ni dependencias: se reutilizó
  `scripts/sample_videos.py`. No se afirma una nueva ejecución de sus pruebas.
- MP4, metadatos completos y PNG excluidos por `.gitignore`. Solo se publica la
  selección, el plan y el manifiesto de referencias, hashes y estados pendientes.

[Manifiesto auditado](nox-new-source-candidates-2026-10-30.json) ·
[Plan reproducible](nox-new-sources-review-plan-2026-10-30.json) ·
[URLs seleccionadas](nox-new-sources-2026-10-30.txt).

```powershell
.\.venv\Scripts\python.exe scripts/sample_videos.py --root . --review-plan docs/nox-new-sources-review-plan-2026-10-30.json
```

Ejecutar la reproducción en una carpeta de salida nueva; el preparador de
muestreo existente no protege frente a sobrescribir una tanda previa.
Los instantes son referencias de revisión del decodificador, con una estimación
por FPS si faltan; no son una medición de exposición.

## Revisión y anotación pendientes

El color es una característica de cobertura, no una clase: NOX blanco o naranja
conserva `nox_texto`; el emblema independiente conserva `nox_simbolo`. La X de la
palabra no se etiqueta de nuevo. Revisar todas las impresiones y soportes, separar
ropa/palas de estáticos y distinguir positivas, negativas revisadas y ambiguas.

Priorizar planos cercanos y variedad real; no utilizar doce frames de un mismo
plano como doce escenas independientes. Germany y Milano conservan el bloqueo
de grupo anterior. Mantener los clips Kuwait relacionados juntos hasta comprobar
partidos, sesiones y posibles reposts. No se ha reservado un test independiente.

Las fuentes están seleccionadas para revisión local; el permiso de reutilización
sigue pendiente de documentar. No se asignó licencia, no se cargó material en un
servicio externo y no se entrenó un modelo en este bloque.
