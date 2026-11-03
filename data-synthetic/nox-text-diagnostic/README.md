# Conjunto sintético de diagnóstico `nox_texto`

**Conclusión obligatoria.** Este trabajo solo sirve para comprobar el pipeline y estudiar si el modelo puede aprender un patrón controlado. No sustituye imágenes reales ni permite afirmar que el detector es confiable.

Es un conjunto **sintético** (`synthetic: true`), separado del dataset oficial de T04 (23 imágenes reales). No se mezcla con sus `train`/`val`/`test`, no se sube a Roboflow y no cambia ninguna métrica publicada. Sus particiones se llaman `diag_train` y `diag_val`, sin `test`.

## Contenido

| Partición | Imágenes | Positivas | Negativas | Cajas |
| --- | ---: | ---: | ---: | ---: |
| `diag_train` | 160 | 100 | 60 | 107 |
| `diag_val` | 40 | 24 | 16 | 27 |
| Total | 200 | 124 | 76 | 134 |

- Clase única: `0: nox_texto`. Una caja ajustada por impresión visible; 10 positivas tienen dos impresiones.
- Positivos (escenas): camiseta (`shirt_chest`, 42), manga (`shirt_sleeve`, 41) y superficie tipo pala perforada (`paddle_face`, 41).
- Negativos difíciles (sin NOX): texto parecido (HOX, MOX, NOK, PADEL…, 16), prenda con rayas/formas (15), brazos (15), público (15), texturas de red/pista/pala sin texto (15).
- Variación registrada por imagen: tamaño (3,75 %–63 % del ancho), posición, color y contraste del texto, rotación, perspectiva, iluminación (pliegues, gradiente, brillo, contraste, reflejo), desenfoque gaussiano o de movimiento, ruido, compresión JPEG y oclusión parcial (bola, brazo o borde de marco; 14 de 124 positivas, ya que las oclusiones que ocultaban más del 40 % del texto se rechazan).
- Las cajas cubren solo la parte visible del texto, tras oclusión y perforaciones. Cada caja conserva `visible_fraction` ≥ 0,6.

## Reproducir

Semilla global `20261103`; cada imagen usa `default_rng([semilla, índice])`.

```powershell
.\.venv\Scripts\python.exe scripts/generate_nox_synthetic.py --ultralytics
.\.venv\Scripts\python.exe scripts/generate_nox_synthetic.py --validate-only
```

El generador rechaza sobrescribir un conjunto existente. `manifest.json` incluye semilla, parámetros, versiones de la herramienta (generador 1.0.0, Python 3.11.9, Pillow 13.0.0, NumPy 2.4.6, Matplotlib 3.11.2), clase, caja en píxeles y YOLO, dimensiones, hash SHA-256 de imagen y etiqueta, tipo de escena y transformaciones. Los hashes de las imágenes dependen de esas versiones: con otras puede variar el píxel exacto aunque las etiquetas coincidan.

## Procedencia y licencias

Ninguna imagen real, fotograma ni recurso de marca. Todo se dibuja con el script. Único recurso externo: fuentes DejaVu (Sans Bold, Serif Bold, Sans Bold Oblique, Sans Mono Bold) incluidas con Matplotlib, bajo la licencia Bitstream Vera/DejaVu, que permite uso y redistribución. No se copian al repositorio; sus hashes están en el manifiesto. `mono-bold` solo aparece en validación (7 de 27 impresiones).

## Publicación en Git

Se publican el generador, las pruebas, `manifest.json`, `dataset.yaml`, `labels/` y este README. Las imágenes (`images/`) están excluidas por `.gitignore`; se regeneran con el comando anterior.

## Validación realizada

- Cajas dentro de la imagen, clase 0, conversión YOLO ↔ píxeles (tolerancia 0,001 px), positivas con etiqueta y negativas con etiqueta vacía, hashes de imagen y etiqueta, dimensiones, ausencia de duplicados y de archivos sobrantes, y YAML esperado.
- Carga real con `YOLODataset` de Ultralytics 8.4.189: `diag_train` 160 imágenes/107 cajas y `diag_val` 40/27, con 0 corruptos.
- Pruebas: 9 nuevas (`tests/test_generate_nox_synthetic.py`) y suite completa de 51 pruebas, de las que 16 se omiten porque falta FFmpeg en este equipo.

## Limitaciones: por qué no demuestra generalización

- La palabra usa fuentes genéricas, no la tipografía real de NOX; fondos, brazos, público y pala son dibujos simples, no escenas reales.
- Entrenamiento y validación salen del mismo generador, con las mismas escenas, oclusores y distribuciones; `diag_val` solo añade una fuente no vista. No es validación independiente ni test ciego.
- Las perforaciones, el desenfoque y la oclusión son aproximaciones. Que un modelo aprenda este patrón no implica que detecte NOX en vídeos reales.
- Un buen resultado aquí no debe citarse como fiabilidad del detector ni como métrica oficial. Los negativos sintéticos no sustituyen negativos reales (ropa, público y brazos filmados).
- `nox_simbolo` queda fuera: no se genera la X independiente.
