# Inferencia de una imagen y exportación para revisión

Bloque de T10 autorizado el 03/11/2026: ejecutar un checkpoint local configurable,
ver sus cajas y exportar resultados. La herramienta funciona; la calidad del
checkpoint del ensayo sigue sin aceptarse. No completa el nivel esencial.

## Preparación

Esta rama incluye el lector de vídeo previo como base, pero este comando procesa
solo una imagen. Desde un clon nuevo, seleccionar explícitamente la rama:

```powershell
git clone --branch feat/image-inference https://github.com/fer-trk/project-ai-computer-vision-objects.git
cd project-ai-computer-vision-objects
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-inference.txt
.\.venv\Scripts\python.exe -m pip check
```

Se comprobó Windows x64 con Python 3.11.9, Ultralytics 8.4.189, PyTorch 2.11.0+cpu
y Torchvision 0.26.0+cpu. El archivo de dependencias conserva las versiones
resueltas en el entorno aislado. No modifica `requirements-tools.txt`, el entorno
anterior ni Colab. La instalación de este bloque terminó con `pip check` correcto;
no se hizo una segunda instalación desde el archivo fijado.

El checkpoint debe ser un `.pt` local propio y confiable: la herramienta no
sustituye una ruta ausente por pesos genéricos ni descarga un modelo. Los pesos
del ensayo se recuperaron de `weights/best.pt` dentro del ZIP original, conservado
en local. SHA-256: `f667beed8ce6356f56d6468eea86b64927e8d56888712c1d73a9e304759fc570`.
Ese checkpoint tiene una sola clase `nox`; no se presenta como modelo de dos clases.

## Ejecutar

```powershell
.\.venv\Scripts\python.exe scripts/predict_image.py "ruta/a/imagen.png" --checkpoint "ruta/a/best.pt" --output local-artifacts/prediccion-001 --confidence 0.25
```

La confianza es un argumento obligatorio. `0.25` se usó para la comprobación
funcional, no es una regla de claridad aprobada ni un umbral de calidad final.
IoU de supresión por defecto 0.7, tamaño de entrada 640 y máximo 300 propuestas;
estos parámetros se guardan en el informe. La inferencia usa CPU.

La salida debe estar en `local-artifacts/` o `data/review/`, excluidos de Git,
y debe ser una carpeta nueva. No se sobrescriben resultados ni originales.

Cada ejecución produce:

- `annotated.png`: imagen con cajas, IDs, clase, score y aviso de revisión.
  Los nombres aparecen debajo de sus cajas; se añade espacio inferior si se
  solapan las etiquetas. El original permanece intacto.
- `predictions.json`: dimensiones, orientación, hashes de imagen/checkpoint,
  clases reales del modelo, parámetros, versiones, tiempo y lista de detecciones.
- `predictions.csv`: una fila por detección, con ID, clase, score, caja y hashes.
  Sin detecciones, conserva solo las cabeceras; JSON conserva una lista vacía.

Las cajas utilizan coordenadas `xyxy` en píxeles de la imagen original después
de corregir EXIF. No incluyen los 38 píxeles de cabecera de la vista anotada.
La transparencia se compone sobre blanco antes de inferir. Se validan coordenadas,
clases, scores, integridad de entradas y parámetros. Los archivos se preparan en
una carpeta temporal y se publican juntos al completar el guardado.

Las propuestas se guardan como `evidence_status=unreviewed`, `support=unknown`.
No se decide claridad por score ni se atribuyen ropa/pala/cartel automáticamente.
La herramienta no mide exposición ni persiste en una base de datos.

## Evidencias y límites

- **34 pruebas correctas**, 10 nuevas sobre correspondencia caja/clase/score,
  JSON/CSV, imagen vacía, EXIF, transparencia, solapamientos, entradas inválidas,
  protección de resultados y fallos de escritura. Estas pruebas usan respuestas
  controladas; verifican software, no la calidad del detector.
- Ejecución real de `best.pt` sobre las tres imágenes históricas de validación y
  una imagen nueva con camiseta negra y hombros blancos. Hubo 1, 1, 3 y 5 propuestas
  respectivamente con umbral 0.25. Se inspeccionaron las cuatro vistas.
- Las dos negativas recibieron falsas propuestas; en la positiva de muñequera
  la caja marca brazo/ropa; en la imagen nueva las propuestas no encuadran el logo
  claro del pecho. Una propuesta errónea alcanza aproximadamente **99,4 % de
  confianza**: el score no demuestra que la detección sea correcta.
- CLI final comprobada con 5 detecciones y con lista vacía al indicar umbral 1
  como caso funcional. Esto último no valida la ausencia de marca: la imagen
  contiene un logo. JSON y CSV de las seis ejecuciones coinciden en sus campos.
- La primera carga/importación tardó unos 23,26 s; las siguientes llamadas en
  el mismo proceso tardaron aproximadamente 0,50–0,61 s. Incluyen carga del modelo
  y predicción, no dibujo/exportación. No representan velocidad de vídeo ni una
  garantía de rendimiento; no se midió pico de RAM.

[Registro sin medios](image-inference-validation-2026-11-03.json). Las vistas y
predicciones completas permanecen en `local-artifacts/image-inference-2026-11-03/`.
Las primeras cuatro ejecuciones preceden al ajuste visual de etiquetas; las dos
ejecuciones CLI posteriores comprobaron el diseño final.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas anteriores de preparación no requieren instalar PyTorch para ejecutarse:
la carga de Ultralytics se realiza solo al invocar el adaptador real. En este equipo
el sandbox de Windows bloqueó el renombrado de carpetas temporales; la batería
se ejecutó fuera de ese sandbox: 33 pruebas pasaron en el entorno de herramientas
antes del ajuste de etiquetas y 34 pruebas finales en el entorno de inferencia.

Siguiente bloque recomendado: revisar y anotar el lote ampliado y entrenar un
modelo mejor. Esta herramienta permitirá comprobarlo cambiando `--checkpoint`,
sin modificar etiquetas de entrenamiento ni simular predicciones correctas.

Referencias de API consultadas:
[Ultralytics Predict](https://docs.ultralytics.com/modes/predict/) y
[PyTorch local](https://pytorch.org/get-started/locally/). La disponibilidad de GPU
o un servicio cloud no forma parte de esta implementación.
