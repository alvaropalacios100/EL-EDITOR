"""A single general-news lead from elDiario.es, using its original RSS."""
import datetime as dt,email.utils,urllib.request,xml.etree.ElementTree as ET,json,re
from pathlib import Path
from motor_v02 import image_from,clean
RSS='https://www.eldiario.es/rss/'
MAX_HOURS=72

def _read(e, tag):
 x=e.find(tag)
 return ''.join(x.itertext()).strip() if x is not None else ''

def _recent(date):
 try:
  value=email.utils.parsedate_to_datetime(date)
  if value.tzinfo is None:value=value.replace(tzinfo=dt.timezone.utc)
  hours=(dt.datetime.now(dt.timezone.utc)-value).total_seconds()/3600
  return value.isoformat() if 0<=hours<=MAX_HOURS else None
 except (TypeError,ValueError):return None

def _valid(a):
 try:
  when=dt.datetime.fromisoformat(a['date'])
  return bool(when.tzinfo and 0<=(dt.datetime.now(dt.timezone.utc)-when).total_seconds()<=MAX_HOURS*3600)
 except (KeyError,ValueError,TypeError):return False

def _select(raw):
 root=ET.fromstring(raw)
 selected=[]
 for item in root.findall('.//item'):
  title=clean(_read(item,'title'));url=_read(item,'link');date=_recent(_read(item,'pubDate'))
  if not(title and url.startswith('https://www.eldiario.es/') and date):continue
  # Choose broad general news, not lifestyle, cinema or celebrity stories.
  path=url.lower();heading=title.casefold()
  ignore=('vertele','/cultura/','/viajes/','/consumoclaro/','/sociedad/medio-ambiente/', '/caballodenietzsche/', '/blog/', '/opinion/', '/fotos/', '/videos/', '/catalunya/cultura/')
  if any(term in path for term in ignore):continue
  if any(w in heading for w in ('serie de netflix','película de','actor de hollywood','premios óscar','recetas de','horóscopo')):continue
  priority=5 if any(w in path for w in ('/politica/','/internacional/','/economia/','/sociedad/','/madrid/','/espana/')) else 0
  if '/deportes/' in path:continue
  selected.append((priority,{'id':'eldiario-lead-'+re.sub(r'\D','',date),'title':title,'url':url,'date':date,'source':'elDiario.es','primary':'Política','sections':['Política'],'topics':['Actualidad general'],'priorities':['media'],'score':0,'cross':False,'image':image_from(item,_read(item,'description'))}))
 selected.sort(key=lambda x:(x[0],x[1]['date']),reverse=True)
 return selected[0][1] if selected else None

def collect_eldiario(online,root):
 cache=Path(root)/'portada_eldiario_v155.json'
 if online:
  try:
   request=urllib.request.Request(RSS,headers={'User-Agent':'Mozilla/5.0 (EL EDITOR RSS Reader)','Accept':'application/rss+xml, text/xml'})
   with urllib.request.urlopen(request,timeout=18) as response:raw=response.read(4_000_000)
   candidate=_select(raw)
   if candidate:
    cache.write_text(json.dumps(candidate,ensure_ascii=False,indent=2),encoding='utf8')
    print('elDiario.es portada: noticia general disponible')
    return candidate
  except Exception as exc:print('elDiario.es portada: RSS no accesible:',str(exc)[:140])
 if cache.exists():
  try:
   cached=json.loads(cache.read_text(encoding='utf8'))
   if _valid(cached):return cached
  except Exception:pass
 return None
