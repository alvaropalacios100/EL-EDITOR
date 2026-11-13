"""Titular general de El País, sin inventar títulos ni fotografías."""
import datetime,email.utils,json,re,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
RSS='https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada'
MAX_HOURS=48

def text(node,name):
 e=node.find(name);return ''.join(e.itertext()).strip() if e is not None else ''
def collect_pais(online,root):
 cache=Path(root)/'portada_pais_v09.json'
 if not online:
  try:return json.loads(cache.read_text(encoding='utf-8'))
  except:return None
 try:
  req=urllib.request.Request(RSS,headers={'User-Agent':'Mozilla/5.0 EL EDITOR/0.9','Accept':'application/rss+xml, application/xml, text/xml'})
  with urllib.request.urlopen(req,timeout=18) as resp: raw=resp.read(3_000_000)
  rootxml=ET.fromstring(raw)
  now=datetime.datetime.now(datetime.timezone.utc)
  pool=[]
  for item in rootxml.findall('.//item'):
   title=text(item,'title');url=text(item,'link');ds=text(item,'pubDate')
   if not title or not url.startswith('https://elpais.com/') and not url.startswith('https://www.elpais.com/'):continue
   try:
    date=email.utils.parsedate_to_datetime(ds)
    if date.tzinfo is None:date=date.replace(tzinfo=datetime.timezone.utc)
    age=(now-date).total_seconds()/3600
    if age< -2 or age>MAX_HOURS:continue
   except:continue
   # News, not the first tagged sports, culture or opinion entry on the RSS.
   category=' '.join(''.join(n.itertext()).lower() for n in item.findall('category'))
   if any(x in category for x in ['deportes','fútbol','futbol','opinión','opinion','cultura','televisión','television','gastronomía','gastronomia']):continue
   if any(x in title.lower() for x in ['real madrid','barcelona gana','liga de campeones','horóscopo']):continue
   image=''
   for e in item.iter():
    if e.tag.lower().endswith(('content','thumbnail')) and e.get('url','').startswith('https://'):
     image=e.get('url');break
   pool.append({'id':'elpais-portada-'+re.sub('[^0-9]','',ds),'title':title,'url':url,'date':date.isoformat(),'source':'El País','primary':'Política','sections':['Política'],'topics':['Actualidad general'],'priorities':['media'],'score':0,'cross':False,'image':image})
   if len(pool)>=1:break
  result=pool[0] if pool else None
  if result:cache.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
  print('El País portada:', 'titular válido de '+result['date'] if result else 'sin noticia general reciente válida')
  return result
 except Exception as ex:
  print('El País portada: RSS no disponible:',str(ex)[:140])
  # Cache is only valid if still recent.
  try:
   value=json.loads(cache.read_text(encoding='utf-8'))
   dt=datetime.datetime.fromisoformat(value['date'])
   if (datetime.datetime.now(datetime.timezone.utc)-dt).total_seconds()<MAX_HOURS*3600:return value
  except:pass
  return None
