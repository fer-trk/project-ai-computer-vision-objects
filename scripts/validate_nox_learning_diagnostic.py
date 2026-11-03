"""Check the diagnostic against real inputs without training or executing uploads."""
import argparse,ast,hashlib,io,json,math,sys,tempfile,types,zipfile
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('dataset_zip',type=Path);p.add_argument('--nbformat-path',type=Path)
a=p.parse_args()
if a.nbformat_path:sys.path.insert(0,str(a.nbformat_path))
import nbformat
from ultralytics.cfg import DEFAULT_CFG_DICT,get_cfg
from ultralytics.data.dataset import YOLODataset
from ultralytics.data.utils import check_det_dataset
nb=nbformat.read(Path(__file__).resolve().parents[1]/'notebooks/nox_learning_diagnostic.ipynb',as_version=4)
nbformat.validate(nb)
cells={c.metadata.tags[0]:c.source for c in nb.cells if c.cell_type=='code'}
assert len(cells)==7
for c in nb.cells:
 if c.cell_type=='code':ast.parse(c.source);assert c.execution_count is None and not c.outputs
stub=types.ModuleType('google.colab');stub.files=types.SimpleNamespace(upload=lambda:{a.dataset_zip.name:a.dataset_zip.read_bytes()});sys.modules['google.colab']=stub
stub_display=types.ModuleType('IPython.display');stub_display.display=lambda *args:None;sys.modules['IPython.display']=stub_display
with tempfile.TemporaryDirectory(prefix='nox-fit-validation-') as folder:
 state=dict(Path=Path,hashlib=hashlib,io=io,json=json,math=math,zipfile=zipfile,WORK=Path(folder),datetime=datetime,timezone=timezone,environment={},freeze='offline validation')
 exec(cells['dataset-check'],state)
 exec(cells['sample-config'],state)
 selected=state['selected'];assert len(selected)==4 and all(i['split']=='train' for i in selected)
 assert len({i['video_id'] for i in selected if i['boxes']})==3
 assert sum(len(i['boxes']) for i in selected)==4
 assert sum(not i['boxes'] for i in selected)==1
 for i in selected:
  assert hashlib.sha256((state['SAMPLE']/'images'/Path(i['image']).name).read_bytes()).hexdigest()==i['source_sha256']
  assert hashlib.sha256((state['SAMPLE']/'labels'/Path(i['label']).name).read_bytes()).hexdigest()==i['label_sha256']
 data=check_det_dataset(str(state['SAMPLE_YAML']),autodownload=False)
 loaded=YOLODataset(img_path=data['train'],data=data,imgsz=640,batch_size=2,augment=False,cache=False)
 assert len(loaded)==4 and sum(len(i['cls']) for i in loaded.labels)==4
 get_cfg(DEFAULT_CFG_DICT,overrides=state['PARAMETERS'])
 assert state['PARAMETERS']['nbs']==state['PARAMETERS']['batch']==2
 assert state['PARAMETERS']['patience']==0 and state['PARAMETERS']['epochs']==80
 function=ast.parse(cells['check-fit']).body[0];assert isinstance(function,ast.FunctionDef)
 exec(compile(ast.Module(body=[function],type_ignores=[]),'<matching>','exec'),state)
 match=state['match_boxes'];box=[0,0,10,10]
 assert match([box],[box],[.9])['tp']==1
 assert match([box],[box,box],[.9,.8])['fp']==1
 assert match([box],[],[])['fn']==1
 assert match([], [box],[.9])['fp']==1
 assert match([box],[[20,20,30,30]],[.9])['tp']==0
 assert match([box],[[0,0,5,10]],[.9])['tp']==1
 fixed_time=datetime.strptime(state['RUN'].name.removeprefix('nox-fit-'),'%Y%m%d-%H%M%S')
 state['datetime']=types.SimpleNamespace(now=lambda timezone:fixed_time)
 try:exec(cells['sample-config'],state)
 except FileExistsError:pass
 else:raise AssertionError('Existing run overwritten')
 print(json.dumps({'passed':['nbformat and seven code cells','real ZIP integrity and label checks','deterministic selection: three positive videos and one negative, train only','copied image/label hashes unchanged','real Ultralytics loader: four images, four boxes, zero corrupt','training API parameters valid','one-to-one IoU matching: exact, duplicate, miss, negative, disjoint and boundary','existing run refused'], 'selected':[i['image'] for i in selected], 'not_executed':['Colab GPU training','real last.pt predictions','browser file upload/download']},indent=2))
