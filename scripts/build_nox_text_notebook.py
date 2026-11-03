"""Build the Colab training handoff without executing a training run."""

import ast
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]
cells = []


def md(source):
    cells.append(dict(cell_type="markdown", metadata={}, source=textwrap.dedent(source).strip()+"\n"))


def code(source, tag):
    source = textwrap.dedent(source).strip()+"\n"
    ast.parse(source)
    cells.append(dict(cell_type="code", metadata={"tags":[tag]}, source=source, execution_count=None, outputs=[]))


md('''
# Entrenar texto NOX en Colab gratuito

## Objetivo
Cuaderno preparado el 03/11/2026, **sin entrenamiento ejecutado todavía**.
Las cajas fueron revisadas y aprobadas por Fernanda. Se entrenará una sola clase:
`nox_texto`. El símbolo independiente y otras marcas quedan fuera de este ensayo.

**Época:** una pasada por las imágenes de entrenamiento. **Máximo 50:** no promete
mejora por completar 50. **640:** tamaño de entrada; conserva proporción y añade
relleno, sin modificar originales. **Parada temprana:** detener tras 10 épocas
sin mejora del criterio de validación de Ultralytics.

19 imágenes train, 3 val y 1 test exploratorio ya inspeccionado. El test no es
ciego ni suficiente para demostrar generalización. La validación tiene un solo
positivo: sus métricas pueden variar mucho. El nivel esencial exige comprobar
cajas útiles en predicciones reales, no solo que el entrenamiento termine.

## Preparación
En Colab: **Entorno de ejecución → Cambiar tipo de entorno → GPU**, modalidad
gratuita. No comprar unidades. Si no se asigna GPU, detenerse. Ejecutar las celdas
en orden. Antes de subir el ZIP, documentar permisos de reutilización del material;
la aprobación de cajas no es una licencia. El cuaderno no publica medios.

[Guía oficial de entrenamiento](https://docs.ultralytics.com/modes/train/).
''')
code('''
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.metadata, io, json, math, platform, shutil, subprocess, sys, time, zipfile
import torch

if not torch.cuda.is_available():
    raise RuntimeError("No hay GPU CUDA. Selecciona GPU gratuita y vuelve a comenzar; no se inicia entrenamiento CPU.")
print("GPU:", torch.cuda.get_device_name(0), "| Python:", sys.version.split()[0], "| Torch:", torch.__version__)
probe = torch.ones((16,16), device="cuda")
assert (probe @ probe)[0,0].item() == 16
del probe
torch.cuda.empty_cache()
WORK = Path("/content/nox-text-work")
WORK.mkdir(exist_ok=True)
environment = {"python":sys.version,"platform":platform.platform(),"torch":torch.__version__,"cuda":torch.version.cuda,"gpu":torch.cuda.get_device_name(0)}
''', 'gpu-check')
md('''
### 1. Instalar herramientas
Se conserva PyTorch de Colab. Se instala `jedi` si falta y se fija Ultralytics
8.4.189. Se desactivan integraciones usando únicamente opciones existentes.
Si se pide reiniciar la sesión, reiniciarla y volver a la primera celda.
''')
code('''
import importlib.util
if importlib.util.find_spec("jedi") is None:
    subprocess.run([sys.executable,"-m","pip","install","jedi==0.19.2"],check=True)
subprocess.run([sys.executable,"-m","pip","install","ultralytics==8.4.189"],check=True)
subprocess.run([sys.executable,"-m","pip","check"],check=True)
from ultralytics import YOLO, settings
settings.update({k:False for k in ("sync","wandb","mlflow","comet","clearml") if k in settings})
environment["ultralytics"] = importlib.metadata.version("ultralytics")
freeze = subprocess.run([sys.executable,"-m","pip","freeze"],capture_output=True,text=True,check=True).stdout
''', 'install')
md('''
## Pasos
### 2. Subir y verificar el dataset
Selecciona solo **nox-text-dataset-2026-11-03.zip**, entregado junto al cuaderno.
Se comprueban el SHA-256 del ZIP, cada imagen/etiqueta, las cajas y la separación
de grupos, y que el YAML y el manifiesto definan solo `nox_texto`. Se genera una ruta
válida para esta sesión. No usar otro ZIP parecido. La celda se detiene antes de pedir
el ZIP si no se marca `PERMISSIONS_CONFIRMED` (permisos de reutilización por escrito).
''')
code('''
from google.colab import files
from PIL import Image, ImageDraw
import yaml
EXPECTED_ZIP = "8332c1b07824f7c5a2abac9c43f17c23cc78dfa2d7c92d9953af77b4a9364254"
PERMISSIONS_CONFIRMED = False  #@param {type:"boolean"}
if not PERMISSIONS_CONFIRMED:
    raise PermissionError("Permisos de reutilización sin confirmar: no se sube el ZIP ni se entrena. Marca la casilla solo si constan por escrito.")
uploaded = files.upload()
if len(uploaded) != 1:
    raise ValueError("Selecciona exactamente un ZIP")
filename, content = next(iter(uploaded.items()))
if hashlib.sha256(content).hexdigest() != EXPECTED_ZIP:
    raise ValueError("El ZIP no coincide con el lote aprobado; no se extrae")
DATA = WORK / "dataset"
if DATA.exists():
    raise FileExistsError("El dataset ya está extraído; continúa con la celda siguiente")
with zipfile.ZipFile(io.BytesIO(content)) as archive:
    entries = archive.namelist()
    prefix = "nox-text-2026-11-03/"
    manifest = json.loads(archive.read(prefix+"manifest.json"))
    expected = {prefix+"manifest.json",prefix+"dataset.yaml"}
    expected.update(prefix+i[k] for i in manifest["images"] for k in ("image","label"))
    if len(entries)!=len(set(entries)) or set(entries)!=expected:
        raise ValueError("Contenido de ZIP inesperado")
    packaged = yaml.safe_load(archive.read(prefix+"dataset.yaml"))
    if manifest["classes"] != {"0":"nox_texto"} or packaged.get("names") != {0:"nox_texto"} or any(packaged.get(k) != "images/"+k for k in ("train","val","test")):
        raise ValueError("El YAML o el manifiesto del ZIP no definen la clase única nox_texto")
    if sum(i.file_size for i in archive.infolist()) > 200_000_000:
        raise ValueError("Tamaño de ZIP inesperado")
    for name in entries:
        target = (DATA / name.removeprefix(prefix)).resolve()
        if not target.is_relative_to(DATA.resolve()):
            raise ValueError("Ruta no válida en ZIP")
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(archive.read(name))
for item in manifest["images"]:
    image_path, label_path = DATA/item["image"], DATA/item["label"]
    assert hashlib.sha256(image_path.read_bytes()).hexdigest()==item["source_sha256"]
    assert hashlib.sha256(label_path.read_bytes()).hexdigest()==item["label_sha256"]
    with Image.open(image_path) as image:
        image.load()
        assert image.size==(item["width"],item["height"])
    rows=label_path.read_text().splitlines()
    assert len(rows)==len(item["boxes"])
    for row, original in zip(rows,item["boxes"],strict=True):
        label,*values=row.split()
        assert label=="0" and len(values)==4
        cx,cy,w,h=map(float,values)
        assert all(math.isfinite(v) for v in (cx,cy,w,h)) and w>0 and h>0
        assert -.000001<=cx-w/2<=cx+w/2<=1.000001 and -.000001<=cy-h/2<=cy+h/2<=1.000001
        restored=[(cx-w/2)*item["width"],(cy-h/2)*item["height"],(cx+w/2)*item["width"],(cy+h/2)*item["height"]]
        assert max(abs(a-b) for a,b in zip(restored,original)) < .001
for key in ("source_sha256","video_id","group_id"):
    parts={s:{i[key] for i in manifest["images"] if i["split"]==s} for s in ("train","val","test")}
    assert not parts["train"]&parts["val"] and not parts["train"]&parts["test"] and not parts["val"]&parts["test"]
assert len(manifest["images"])==23
assert {s:sum(i["split"]==s for i in manifest["images"]) for s in ("train","val","test")}=={"train":19,"val":3,"test":1}
config={"path":str(DATA),"train":"images/train","val":"images/val","test":"images/test","names":{0:"nox_texto"}}
(DATA/"dataset.yaml").write_text(yaml.safe_dump(config))
del uploaded,content
print("23 imágenes verificadas:",manifest["summary"])
''','dataset-check')
md('''
### 3. Comprobar visualmente etiquetas de entrenamiento y validación
Las cajas verdes son referencia humana, no predicciones. No se usa la imagen de
test para configurar el entrenamiento. Los originales permanecen intactos.
''')
code('''
from IPython.display import display
from ultralytics.data.utils import check_det_dataset
checked=check_det_dataset(str(DATA/"dataset.yaml"),autodownload=False)
assert checked["names"]=={0:"nox_texto"}
for split in ("train","val"):
    item=next(i for i in manifest["images"] if i["split"]==split and i["boxes"])
    with Image.open(DATA/item["image"]) as source:
        image=source.convert("RGB")
    draw=ImageDraw.Draw(image)
    for box in item["boxes"]:
        draw.rectangle(tuple(box),outline="lime",width=3)
    print(split,item["video_id"])
    display(image)
''','preview-labels')
md('''
### 4. Configuración del ensayo y respaldo
Máximo 50 épocas; parada tras 10 sin mejora, resolución 640, lote 2, semilla 42.
Se usa YOLO11n preentrenado oficial como punto de partida, no el checkpoint pobre
del ensayo anterior. Se registrará el hash de los pesos realmente descargados.

Sin volteos que reflejen las letras y sin mosaicos que reduzcan los logos pequeños.
Se aplican variaciones moderadas de color/luz, escala y traslación. Son parámetros
de este ensayo, no una configuración optimizada. No cambiar parámetros mirando test.

`USE_DRIVE=False` usa almacenamiento temporal. Para respaldo durante el ensayo,
puedes activar Drive; pedirá tu autorización. Sin Drive, una desconexión puede
perder resultados antes de descargarlos. No se compran recursos ni servicios.

**Un solo ensayo:** esta celda comprueba que los parámetros acordados no se han
editado y crea `ONE_RUN.lock`; un segundo intento falla. No hay barridos ni repeticiones
automáticas. Con una sesión nueva sin Drive el bloqueo desaparece: no ejecutar otro ensayo
sin acuerdo explícito.
''')
code('''
USE_DRIVE = False
RUNS = WORK/"runs"
if USE_DRIVE:
    from google.colab import drive
    drive.mount("/content/drive")
    RUNS=Path("/content/drive/MyDrive/nox-text-runs")
PARAMETERS=dict(epochs=50,patience=10,imgsz=640,batch=2,device=0,seed=42,deterministic=True,
    workers=0,amp=False,save=True,save_period=5,plots=True,cache=False,
    mosaic=0.0,mixup=0.0,fliplr=0.0,flipud=0.0,hsv_h=0.015,hsv_s=0.3,hsv_v=0.2,scale=0.2,translate=0.1)
AGREED=dict(epochs=50,patience=10,imgsz=640,batch=2,seed=42,mosaic=0.0,mixup=0.0,fliplr=0.0,flipud=0.0)
if any(PARAMETERS[k]!=v for k,v in AGREED.items()):
    raise ValueError("Los parámetros difieren de la configuración acordada; este paquete no admite barridos")
RUNS.mkdir(parents=True,exist_ok=True)
RUN_NAME="nox-text-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
try:
    with (RUNS/"ONE_RUN.lock").open("x") as lock:
        lock.write(RUN_NAME)
except FileExistsError:
    raise FileExistsError("Ya se preparó una ejecución (ONE_RUN.lock). Este paquete admite un solo run; no se repite ni se barren hiperparámetros.") from None
RUN=RUNS/RUN_NAME
RUN.mkdir(parents=True,exist_ok=False)
(RUN/"environment.json").write_text(json.dumps(environment,indent=2))
(RUN/"requirements-resolved.txt").write_text(freeze)
(RUN/"dataset-manifest.json").write_bytes((DATA/"manifest.json").read_bytes())
(RUN/"experiment.json").write_text(json.dumps({"run_name":RUN_NAME,"parameters":PARAMETERS,"dataset_zip_sha256":EXPECTED_ZIP,"annotations_user_approved":"2026-11-03","status":"prepared"},indent=2))
print("Ejecución:",RUN_NAME,"| Resultados:",RUN)
print(PARAMETERS)
''','experiment-config')
md('''
### 5. Entrenar
Esta celda inicia el entrenamiento real y descarga el checkpoint oficial si falta.
No promete que el modelo detecte bien. Si falla, conserva el error y ejecuta la
última celda para descargar lo disponible antes de reiniciar o cambiar parámetros.
''')
code('''
if not torch.cuda.is_available():
    raise RuntimeError("La GPU ya no está disponible; detener el ensayo")
if (RUN/"train").exists():
    raise FileExistsError("Esta ejecución ya comenzó; crea un nuevo RUN_NAME para otro ensayo")
import traceback
record={"run_name":RUN_NAME,"model":"yolo11n.pt","parameters":PARAMETERS,"dataset_zip_sha256":EXPECTED_ZIP,"annotations_user_approved":"2026-11-03","status":"starting"}
started=time.perf_counter()
try:
    model=YOLO("yolo11n.pt")
    record["pretrained_checkpoint_sha256"]=hashlib.sha256(Path(model.ckpt_path).read_bytes()).hexdigest()
    record["status"]="training"
    (RUN/"experiment.json").write_text(json.dumps(record,indent=2))
    model.train(data=str(DATA/"dataset.yaml"),project=str(RUN),name="train",exist_ok=False,**PARAMETERS)
    assert (RUN/"train/weights/best.pt").is_file()
    record["status"]="training_completed"
except BaseException as error:
    record["status"]="training_failed_or_interrupted"
    record["error"]=type(error).__name__+": "+str(error)
    (RUN/"error.log").write_text(traceback.format_exc(),encoding="utf-8")
    raise
finally:
    record["elapsed_training_seconds"]=time.perf_counter()-started
    (RUN/"experiment.json").write_text(json.dumps(record,indent=2))
print("Entrenamiento terminado; falta evaluar e inspeccionar las cajas.")
''','train')
md('''
## Comprobaciones
### 6. Evaluar el modelo elegido y ver sus predicciones
Se carga `best.pt`, elegido mediante validación, y se guarda su hash. La imagen
test solo se evalúa ahora; es una reserva exploratoria ya inspeccionada, no una
prueba final suficiente. No seleccionar umbrales ni reentrenar usando su resultado.

Se mostrarán predicciones sobre las tres imágenes de validación, incluidas las
dos negativas, y la imagen de reserva. El umbral 0.25 es diagnóstico, no una regla
de claridad aprobada. Una confianza alta no demuestra exactitud. Comparar cajas
con el logo real; no aceptar el modelo solo por una métrica o por acabar 50 épocas.
''')
code('''
best_path=RUN/"train/weights/best.pt"
if not best_path.is_file():
    raise FileNotFoundError("No existe best.pt; revisa el entrenamiento")
best=YOLO(str(best_path))
assert best.names=={0:"nox_texto"}
evaluation={"checkpoint_sha256":hashlib.sha256(best_path.read_bytes()).hexdigest(),"test_is_exploratory":True,"splits":{}}
for split in ("val","test"):
    metrics=best.val(data=str(DATA/"dataset.yaml"),split=split,device=0,imgsz=640,batch=2,workers=0,plots=True,project=str(RUN),name="evaluation-"+split)
    evaluation["splits"][split]={k:float(v) for k,v in metrics.results_dict.items()}
(RUN/"evaluation.json").write_text(json.dumps(evaluation,indent=2,allow_nan=False))
predictions=[]
for item in manifest["images"]:
    if item["split"] not in ("val","test"):
        continue
    result=best.predict(str(DATA/item["image"]),conf=0.25,imgsz=640,device=0,save=False,verbose=False)[0]
    predictions.append({"image":item["image"],"split":item["split"],"reference_boxes":item["boxes"],"predicted_boxes":result.boxes.xyxy.cpu().tolist(),"scores":result.boxes.conf.cpu().tolist(),"classes":result.boxes.cls.cpu().tolist(),"review_status":"pending_human_review"})
    target=RUN/"predictions"/Path(item["image"]).name
    target.parent.mkdir(exist_ok=True)
    result.save(filename=str(target))
    print(item["split"],Path(item["image"]).name,"| referencia:",len(item["boxes"]),"| predicciones:",len(result.boxes))
    display(Image.open(target))
(RUN/"predictions.json").write_text(json.dumps({"confidence_threshold":0.25,"predictions":predictions},indent=2,allow_nan=False))
print(evaluation)
''','evaluate')
md('''
## Siguiente paso
### 7. Descargar resultados, también si hubo un error previo
Descarga el ZIP y guárdalo en tu equipo antes de cerrar Colab. Incluye lo que
exista: checkpoints, configuración, métricas, vistas y versiones. Guarda también
el cuaderno ejecutado con **Archivo → Descargar → Descargar .ipynb**; no se incluye
automáticamente en este ZIP. Ambos deben corresponder al mismo identificador.

Al terminar, compartimos las métricas y revisamos las predicciones. La siguiente
decisión será aceptar el resultado o corregir datos/ensayo según errores reales.
No publicar ZIP, imágenes ni pesos en GitHub.
''')
code('''
from google.colab import files
if "RUN" not in globals() or not RUN.exists():
    raise RuntimeError("Todavía no existe una ejecución que descargar")
archive_path=Path(str(RUN)+"-results.zip")
if archive_path.exists():
    raise FileExistsError("Ya hay un ZIP de esta ejecución; no sobrescribir")
REQUIRED=("train/weights/best.pt","train/weights/last.pt","train/args.yaml","train/results.csv","experiment.json","environment.json","requirements-resolved.txt","dataset-manifest.json")
listed=[p for p in sorted(RUN.rglob("*")) if p.is_file() and p.name!="run-manifest.json"]
run_manifest={"run_name":RUN.name,"status":json.loads((RUN/"experiment.json").read_text())["status"],
    "missing_required":[r for r in REQUIRED if not (RUN/r).is_file()],"error_log_present":(RUN/"error.log").is_file(),
    "files":{p.relative_to(RUN).as_posix():{"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size} for p in listed}}
(RUN/"run-manifest.json").write_text(json.dumps(run_manifest,indent=2),encoding="utf-8")
with zipfile.ZipFile(archive_path,"x",zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(RUN.rglob("*")):
        if path.is_file():
            archive.write(path,path.relative_to(RUN))
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
print("Descarga:",archive_path.name,"| SHA256:",hashlib.sha256(archive_path.read_bytes()).hexdigest())
files.download(str(archive_path))
''','download')

notebook=dict(nbformat=4,nbformat_minor=5,metadata={"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python"},"colab":{"name":"nox_text_training.ipynb"},"accelerator":"GPU"},cells=cells)
for i,cell in enumerate(cells):
    cell["id"]=f"nox-text-{i:02d}"
path=ROOT/"notebooks/nox_text_training.ipynb"
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(notebook,indent=1,ensure_ascii=False)+"\n",encoding="utf-8")
print(path)
