"""Build a training-only sample-fit diagnostic for free Colab GPU."""
import ast
import copy
import json
from pathlib import Path
import textwrap

ROOT=Path(__file__).resolve().parents[1]
original=json.loads((ROOT/'notebooks/nox_text_training.ipynb').read_text(encoding='utf-8'))
lookup={c['metadata']['tags'][0]:c for c in original['cells'] if c['cell_type']=='code'}
cells=[]
def md(source):
 cells.append(dict(cell_type='markdown',metadata={},source=textwrap.dedent(source).strip()+'\n'))
def code(source,tag):
 source=textwrap.dedent(source).strip()+'\n';ast.parse(source)
 cells.append(dict(cell_type='code',metadata={'tags':[tag]},source=source,execution_count=None,outputs=[]))
def reuse(tag):
 c=copy.deepcopy(lookup[tag]);c['source']=''.join(c['source']).replace('/content/nox-text-work','/content/nox-learning-diagnostic');cells.append(c)
md('''
# Diagnóstico: ¿puede aprender cuatro imágenes?
Aprobado por Fernanda tras el ensayo `nox-text-20261103-104507` fallido.
**Preparado, sin ejecución GPU de este diagnóstico todavía.**

La pregunta es si el proceso puede memorizar tres imágenes positivas y una negativa
que ya pertenecen a train. No se modifica ninguna caja aprobada. No se utiliza val
ni test para elegir ejemplos o ajustar parámetros. Acertar estas mismas imágenes
no demuestra generalización ni completa el esencial.

## Preparación
Usa una sesión nueva de Colab, GPU gratuita. Ejecuta en orden y sube el mismo
`nox-text-dataset-2026-11-03.zip` de 23 imágenes cuando se solicite. El ZIP y los
pesos previos no se sobrescriben. Los permisos de reutilización conservan el estado
pendiente del registro de fuentes. Se mantienen los controles de GPU y de integridad.
''')
reuse('gpu-check');reuse('install');reuse('dataset-check')
md('''
## 1. Elegir la muestra y fijar el experimento
Se eligen las tres cajas más grandes disponibles en vídeos distintos de train,
conservando todas las cajas de cada imagen, más el primer negativo de train por
nombre. Selección determinista basada en anotaciones, sin mirar predicciones.

Se muestran las cuatro referencias. El YAML apunta train y val a estas mismas
cuatro imágenes únicamente para esta comprobación de memorización: sus métricas
internas **no son validación independiente**.

80 épocas fijas; lote 2; tamaño 640; semilla 42. Sin transformaciones aleatorias.
Adam a 0,001 y `nbs=2`, de modo que se actualicen pesos en cada lote, sin acumular
hasta el lote nominal 64 del ensayo anterior. Son cambios deliberados para facilitar
aprender la muestra; este ensayo no aísla cuál de ellos explica un eventual cambio.
Se usa un checkpoint oficial fresco y se evalúa `last.pt` tras las 80 épocas.
''')
code('''
import shutil
positives=sorted((i for i in manifest['images'] if i['split']=='train' and i['boxes']),
    key=lambda i:(-max((b[2]-b[0])*(b[3]-b[1]) for b in i['boxes']),i['image']))
selected=[]
seen=set()
for item in positives:
    if item['video_id'] not in seen:
        selected.append(item);seen.add(item['video_id'])
    if len(selected)==3:break
selected+=sorted((i for i in manifest['images'] if i['split']=='train' and not i['boxes']),key=lambda i:i['image'])[:1]
assert len(selected)==4 and sum(bool(i['boxes']) for i in selected)==3
assert all(i['split']=='train' for i in selected)
RUN=WORK/('nox-fit-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
RUN.mkdir(parents=True,exist_ok=False)
SAMPLE=RUN/'sample'
from IPython.display import display
for item in selected:
    for kind in ('image','label'):
        target=SAMPLE/('images' if kind=='image' else 'labels')/Path(item[kind]).name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(DATA/item[kind],target)
    with Image.open(DATA/item['image']) as source:image=source.convert('RGB')
    draw=ImageDraw.Draw(image)
    for box in item['boxes']:draw.rectangle(tuple(box),outline='lime',width=3)
    print(Path(item['image']).name,'| referencia:',len(item['boxes']))
    display(image)
SAMPLE_YAML=SAMPLE/'dataset.yaml'
SAMPLE_YAML.write_text(yaml.safe_dump(dict(path=str(SAMPLE),train='images',val='images',names={0:'nox_texto'})))
PARAMETERS=dict(epochs=80,patience=0,imgsz=640,batch=2,nbs=2,device=0,seed=42,deterministic=True,
    optimizer='Adam',lr0=0.001,lrf=1.0,warmup_epochs=0.0,weight_decay=0.0,
    workers=0,amp=False,save=True,save_period=20,plots=True,cache=False,val=False,
    mosaic=0.0,mixup=0.0,cutmix=0.0,copy_paste=0.0,fliplr=0.0,flipud=0.0,
    hsv_h=0.0,hsv_s=0.0,hsv_v=0.0,scale=0.0,translate=0.0,degrees=0.0,shear=0.0,perspective=0.0)
record=dict(diagnostic='training_sample_fit_only',status='prepared',parameters=PARAMETERS,
    dataset_zip_sha256=EXPECTED_ZIP,selected=selected,independent_evaluation=False)
(RUN/'experiment.json').write_text(json.dumps(record,indent=2))
(RUN/'environment.json').write_text(json.dumps(environment,indent=2))
(RUN/'requirements-resolved.txt').write_text(freeze)
print('Resultados:',RUN)
''','sample-config')
md('''
## 2. Entrenar la muestra
Este paso sí entrena en la GPU. Puede tardar unos minutos; no se garantiza tiempo.
Si aparece error, descarga los resultados disponibles con la última celda.
Una desconexión puede perder los archivos temporales: descárgalos antes de cerrar.
''')
code('''
if not torch.cuda.is_available():raise RuntimeError('GPU CUDA no disponible')
if (RUN/'train').exists():raise FileExistsError('El ensayo ya comenzó; no sobrescribir')
model=YOLO('yolo11n.pt')
record['pretrained_checkpoint_sha256']=hashlib.sha256(Path(model.ckpt_path).read_bytes()).hexdigest()
record['status']='training'
(RUN/'experiment.json').write_text(json.dumps(record,indent=2))
started=time.perf_counter()
try:
    model.train(data=str(SAMPLE_YAML),project=str(RUN),name='train',exist_ok=False,**PARAMETERS)
    assert (RUN/'train/weights/last.pt').is_file()
    record['status']='training_completed'
except BaseException as error:
    record['status']='training_failed_or_interrupted'
    record['error']=type(error).__name__+': '+str(error)
    raise
finally:
    record['elapsed_training_seconds']=time.perf_counter()-started
    (RUN/'experiment.json').write_text(json.dumps(record,indent=2))
''','train-sample')
md('''
## 3. Comprobar si aprendió esas mismas imágenes
Confianza fija 0,25 e IoU mínimo 0,50 para asociar predicción y referencia una a una.
Se cuentan aciertos, falsas detecciones y logos omitidos. El criterio diagnóstico
estricto exige recuperar todas las cajas y no producir falsos positivos en estas
cuatro imágenes. Un fallo no identifica por sí solo la causa; un acierto solo prueba
capacidad de ajuste sobre esta muestra. No usar el resultado como precisión del producto.

Se guardan vistas y JSON. Revisaremos también las pérdidas y las cajas a escala útil.
''')
code('''
def match_boxes(references,boxes,scores,threshold=0.5):
    def iou(a,b):
        overlap=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
        union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-overlap
        return overlap/union if union>0 else 0.0
    remaining=set(range(len(references)));matched=[]
    for index in sorted(range(len(boxes)),key=lambda i:-scores[i]):
        if not remaining:break
        target=max(remaining,key=lambda j:iou(boxes[index],references[j]))
        if iou(boxes[index],references[target])>=threshold:
            remaining.remove(target);matched.append(dict(prediction=index,reference=target,iou=iou(boxes[index],references[target])))
    return dict(tp=len(matched),fp=len(boxes)-len(matched),fn=len(remaining),matches=matched)

last=RUN/'train/weights/last.pt'
if not last.is_file():raise FileNotFoundError('No existe last.pt; revisar entrenamiento')
fitted=YOLO(str(last))
assert fitted.names=={0:'nox_texto'}
results=[]
for item in selected:
    result=fitted.predict(str(DATA/item['image']),conf=0.25,imgsz=640,device=0,save=False,verbose=False)[0]
    boxes=result.boxes.xyxy.cpu().tolist();scores=result.boxes.conf.cpu().tolist()
    assert all(c==0 for c in result.boxes.cls.cpu().tolist())
    metrics=match_boxes(item['boxes'],boxes,scores)
    results.append(dict(image=item['image'],reference_boxes=item['boxes'],boxes=boxes,scores=scores,**metrics))
    target=RUN/'predictions'/Path(item['image']).name;target.parent.mkdir(exist_ok=True)
    result.save(filename=str(target))
    print(Path(item['image']).name,metrics)
    with Image.open(target) as image:display(image.copy())
totals={key:sum(r[key] for r in results) for key in ('tp','fp','fn')}
summary=dict(checkpoint_sha256=hashlib.sha256(last.read_bytes()).hexdigest(),confidence=0.25,iou=0.5,
    independent_evaluation=False,totals=totals,sample_fit_pass=totals['fp']==0 and totals['fn']==0,
    interpretation='Training sample only; not evidence of generalization',predictions=results)
(RUN/'sample-fit.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
print('AJUSTE DE MUESTRA:',summary['sample_fit_pass'],totals)
''','check-fit')
md('''
## 4. Descargar y compartir
Descarga el ZIP de este diagnóstico y el cuaderno ejecutado (Archivo → Descargar
→ Descargar .ipynb). Mantén el identificador `nox-fit-...` para no confundirlo con
el entrenamiento anterior. El ZIP contiene la muestra local, pesos y resultados:
no publicarlo en GitHub. Esta celda funciona también tras un fallo de entrenamiento.
''')
reuse('download')
for i,c in enumerate(cells):c['id']=f'nox-fit-{i:02d}'
nb=dict(nbformat=4,nbformat_minor=5,metadata=copy.deepcopy(original['metadata']),cells=cells)
nb['metadata']['colab']['name']='nox_learning_diagnostic.ipynb'
(ROOT/'notebooks/nox_learning_diagnostic.ipynb').write_text(json.dumps(nb,indent=1,ensure_ascii=False)+'\n',encoding='utf-8')
print('Built:',ROOT/'notebooks/nox_learning_diagnostic.ipynb')
