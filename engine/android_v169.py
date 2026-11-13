"""LA MAZMORRA DEL ANDROID: RSS oficiales y noticias auténticas por fuente."""
import json,re,datetime,urllib.request,urllib.parse,xml.etree.ElementTree as ET
from pathlib import Path
from nature_v166 import parse_rss
ROOT=Path(__file__).resolve().parent
CACHE=ROOT/'android_noticias_v169.json'
FEEDS={
 'Xataka Móvil':['https://www.xatakamovil.com/feedburner.xml','https://feeds.weblogssl.com/xatakamovil','https://www.xatakamovil.com/atom.xml'],
 'Computer Hoy':['https://computerhoy.20minutos.es/rss','https://computerhoy.20minutos.es/rss/ultimas-noticias/']
}
def collect(online=False):
 if not online:
  try:return json.loads(CACHE.read_text(encoding='utf-8'))
  except Exception:return {'articles':[],'status':{'local':'Ejecuta INICIAR_PRUEBA.bat para obtener noticias actuales'}}
 print('ANDROID: recuperando noticias de Xataka Móvil y Computer Hoy...',flush=True)
 results={};status={}
 for source,feeds in FEEDS.items():
  articles=[]
  for address in feeds:
   try:
    req=urllib.request.Request(address,headers={'User-Agent':'Mozilla/5.0 (EL EDITOR, RSS lector personal)','Accept':'application/rss+xml, application/xml, text/xml'})
    with urllib.request.urlopen(req,timeout=12) as response:raw=response.read(3_000_000)
    candidates=parse_rss(raw,source)
    domain='xatakamovil.com' if source=='Xataka Móvil' else 'computerhoy.20minutos.es'
    articles=[a for a in candidates if urllib.parse.urlparse(a['url']).hostname and urllib.parse.urlparse(a['url']).hostname.endswith(domain)]
    if articles:break
   except Exception as exc:status[source]=type(exc).__name__+': '+str(exc)[:100]
  results[source]=articles
  status[source]=f'{len(articles)} noticias recientes' if articles else status.get(source,'Sin noticias recientes')
 from imagenes_v159 import extract_image
 from miniaturas_v14 import embed
 from concurrent.futures import ThreadPoolExecutor
 # Recuperar imagen antes de ordenar, priorizando fotos que realmente se pueden incrustar.
 eligible=results['Xataka Móvil'][:20]+results['Computer Hoy'][:20]
 missing=[x for x in eligible if not x.get('image')]
 if missing:
  with ThreadPoolExecutor(max_workers=6) as pool: probes=list(pool.map(extract_image,[x['url'] for x in missing]))
  for article,(img,stat,url) in zip(missing,probes):
   if img:article['image']=img
 embed(eligible,max_articles=len(eligible))
 used=set();selected=[]
 def take(source,slot):
  pool=[x for x in results[source] if x['url'] not in used]
  # Sólo consideramos los candidatos ya inspeccionados para puntuar imágenes.
  pool=pool[:20]
  pool.sort(key=lambda a:(bool(a.get('image_data')),bool(a.get('image')),a['date']),reverse=True)
  if pool:
   item=pool[0];used.add(item['url']);selected.append({'slot':slot,'article':item})
 take('Xataka Móvil',0)
 take('Computer Hoy',1)
 take('Xataka Móvil',2)
 result={'articles':selected,'status':status}
 CACHE.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print('ANDROID:',len(selected),'de 3 noticias seleccionadas.',flush=True)
 return result
if __name__=='__main__':print(collect(online='--online' in __import__('sys').argv))
