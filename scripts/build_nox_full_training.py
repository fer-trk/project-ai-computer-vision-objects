"""Prepare the full training run using the successful sample-fit configuration."""
import ast,copy,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
nb=json.loads((root/'notebooks/nox_text_training.ipynb').read_text(encoding='utf-8'))
diag=json.loads((root/'notebooks/nox_learning_diagnostic.ipynb').read_text(encoding='utf-8'))
lookup={c['metadata']['tags'][0]:''.join(c['source']) for c in diag['cells'] if c['cell_type']=='code'}
parameters=lookup['sample-config'].split('PARAMETERS=',1)[1].split("\nrecord=",1)[0].replace('cache=False,val=False,','cache=False,val=True,')
for c in nb['cells']:
 s=''.join(c['source'])
 if c['cell_type']=='code':
  s=s.replace('/content/nox-text-work','/content/nox-full-work').replace('RUN_NAME="nox-text-"','RUN_NAME="nox-full-"')
  if 'experiment-config' in c['metadata']['tags']:
   start=s.index('PARAMETERS=');end=s.index('(RUN/"environment.json")',start)
   s=s[:start]+'PARAMETERS='+parameters+'\n'+s[end:]
  ast.parse(s)
 else:
  s=s.replace('Máximo 50','Máximo 80').replace('**Máximo 50:**','**Máximo 80:**').replace('acabar 50 épocas','acabar 80 épocas')
  if '# Entrenar texto NOX' in s:
   s=s.replace('# Entrenar texto NOX en Colab gratuito','# Entrenamiento completo NOX tras diagnóstico')
   a=s.index('**Época:**');b=s.index('19 imágenes train',a)
   s=s[:a]+'''El diagnóstico `nox-fit-20261103-110615` aprendió cuatro cajas sin falsas detecciones
en su muestra. Eso solo demuestra ajuste sobre train. Ahora se entrenan las 19
imágenes originales de train y se mantiene val separado. **Sin ejecutar todavía.**

'''+s[b:]
  if '### 4. Configuración' in s:
   s='''### 4. Ensayo completo con configuración que aprendió la muestra
80 épocas fijas, sin parada temprana; 640, batch=nbs=2, Adam a 0,001 constante,
sin warmup ni aumentos. Semilla 42. Se parte del checkpoint oficial fresco, no de
los pesos memorizados del diagnóstico. Cambian varios controles respecto al ensayo
fallido: este resultado no aislará su efecto causal. Val permanece separado de train.

Se guarda best.pt según validación y last.pt al terminar. La validación tiene solo
un positivo: la calidad sigue pendiente de inspección. El test ya inspeccionado
es exploratorio; no ajustar parámetros o umbral mirando ese resultado.

USE_DRIVE=False guarda temporalmente; descarga antes de cerrar. Opcionalmente
activa Drive para respaldo. No comprar recursos. Los medios y pesos no se publican.
'''
 c['source']=s
 c['id']='full-'+c['id']
nb['metadata']['colab']['name']='nox_full_training.ipynb'
(root/'notebooks/nox_full_training.ipynb').write_text(json.dumps(nb,indent=1,ensure_ascii=False)+'\n',encoding='utf-8')
print('Built nox_full_training.ipynb')
