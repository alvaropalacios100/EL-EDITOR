"""Xataka fixed Express lead: prefer recent stories with a verified, embedded image."""
import datetime,csv,hashlib
from pathlib import Path
from internacional_v158 import rss_read,fresh
from imagenes_v159 import extract_image
from miniaturas_v14 import fetch,valid
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parent
RSS='https://www.xataka.com/index.xml'

def collect(online=False):
 if not online:return None
 now=datetime.datetime.now(datetime.timezone.utc)
 valid_articles=[a for a in rss_read(RSS,'Xataka','es') if fresh(a,now) and a.get('url','').startswith('https://')]
 if not valid_articles:return None
 # Explore up to 15 recent links; preserve RSS ordering when image quality is equivalent.
 candidates=valid_articles[:15]
 def photo(item):
  url=item.get('image','')
  if url and valid(url):
   content=fetch(url)
   if content:return (url,content,'RSS_VERIFICADA')
  url,status,_=extract_image(item['url'])
  if url and valid(url):
   content=fetch(url)
   if content:return (url,content,status+'_VERIFICADA')
  return ('','','SIN_FOTO_VERIFICABLE')
 with ThreadPoolExecutor(max_workers=5) as pool:
  inspected=list(pool.map(photo,candidates))
 index=next((i for i,(_,data,_) in enumerate(inspected) if data),0)
 selected=candidates[index].copy(); url,embedded,status=inspected[index]
 if embedded:
  selected['image']=url;selected['image_data']=embedded
 else:
  selected['image']=''
 selected['foto_xataka_estado']=status
 from email.utils import parsedate_to_datetime
 try:selected['date']=parsedate_to_datetime(selected['date']).isoformat()
 except Exception:pass
 selected['id']='xataka-'+hashlib.sha1(selected['url'].encode()).hexdigest()[:16]
 selected['primary']='Express';selected['score']=30;selected['topics']=['Tecnología']
 with (ROOT/'diagnostico_xataka_v162.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['titular','url','foto_verificada','estado','seleccionada'])
  for i,(a,(_,data,state)) in enumerate(zip(candidates,inspected)):
   w.writerow([a['title'],a['url'],bool(data),state,'Sí' if i==index else 'No'])
 return selected
