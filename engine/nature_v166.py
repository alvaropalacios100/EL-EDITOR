"""Nature: noticia original por medio, sin inventar artículos ni imágenes."""
import json,re,html,email.utils,datetime,urllib.request,urllib.parse,xml.etree.ElementTree as ET,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CACHE=ROOT/'nature_noticias_v166.json'
ANIMALS=re.compile(r'\b(animal(?:es)?|fauna|mamíferos?|aves?|pájaros?|lobos?|linces?|felinos?|perros?|gatos?|osos?|tiburones?|ballenas?|delfines?|orcas?|leones?|elefantes?|insectos?|abejas?|mariposas?|reptiles?|peces?|rapaces?|anfibios?|biodiversidad|especies|águilas?|ciervos?|cetáceos?|primates?|avestruz|caballos?|cocodrilos?|pingüinos?|corales?|pulpos?|arañas?|invertebrados?)\b',re.I)
NATURE=re.compile(r'\b(naturaleza|animal|fauna|flora|medioambiente|medio ambiente|ecología|biodiversidad|bosques?|montañas?|ríos?|océanos?|selvas?|especies|plantas?|aves?|animales?|ecosistema|paisaje|clima|bosques?)\b',re.I)
FEEDS={
 'Muy Interesante':['https://feeds.feedburner.com/Muyinteresantees','https://www.muyinteresante.com/feed/'],
 'National Geographic España':['https://www.nationalgeographic.com.es/feeds/rss.html'],
 'ECOticias':['https://www.ecoticias.com/naturaleza/feed','https://www.ecoticias.com/feed/']
}
def findtext(el,name):
 n=el.find(name)
 return ''.join(n.itertext()).strip() if n is not None else ''
def strip(s):return re.sub(r'<[^>]+>','',html.unescape(s or '')).strip()
def dateval(x):
 try:
  d=email.utils.parsedate_to_datetime(x)
  if d.tzinfo is None:d=d.replace(tzinfo=datetime.timezone.utc)
  return d
 except Exception:
  try:
   d=datetime.datetime.fromisoformat(x.replace('Z','+00:00'))
   if d.tzinfo is None:d=d.replace(tzinfo=datetime.timezone.utc)
   return d
  except:return None
def parse_rss(raw,source):
 document=ET.fromstring(raw)
 items=document.findall('.//item')
 if not items:
  items=document.findall('.//{http://www.w3.org/2005/Atom}entry')
 output=[]
 for e in items[:100]:
  title=strip(findtext(e,'title') or findtext(e,'{http://www.w3.org/2005/Atom}title'))
  url=findtext(e,'link')
  if not url:
   ln=e.find('{http://www.w3.org/2005/Atom}link')
   if ln is not None:url=ln.attrib.get('href','')
  date=dateval(findtext(e,'pubDate') or findtext(e,'{http://www.w3.org/2005/Atom}updated'))
  summ=strip(findtext(e,'description') or findtext(e,'{http://www.w3.org/2005/Atom}summary'))
  if not title or not url.startswith('http') or not date:continue
  age=(datetime.datetime.now(datetime.timezone.utc)-date).total_seconds()/86400
  if age<0 or age>21:continue
  if source=='Muy Interesante' and 'muyinteresante' not in urllib.parse.urlparse(url).netloc:continue
  if source=='National Geographic España' and 'nationalgeographic' not in urllib.parse.urlparse(url).netloc:continue
  if source=='ECOticias' and 'ecoticias' not in urllib.parse.urlparse(url).netloc:continue
  img=''
  for child in e.iter():
   if child.tag.endswith(('thumbnail','content','enclosure','image')):
    candidate=child.attrib.get('url','')
    if candidate.startswith('https://') and not re.search(r'\.(?:svg|gif|ico)(?:\?|$)',candidate,re.I):
     img=candidate;break
  output.append({'id':'nature-'+hashlib.sha1(url.encode()).hexdigest()[:16],
    'title':title,'url':url,'source':source,'date':date.isoformat(),'image':img,
    'summary':summ[:350],'nature':True})
 return output
def collect(online=False):
 if not online:
  try:return json.loads(CACHE.read_text(encoding='utf-8'))
  except Exception:return {'articles':[],'status':{}}
 print('NATURE: consultando Muy Interesante, National Geographic y ECOticias...',flush=True)
 results={};statuses={}
 for source,urls in FEEDS.items():
  all_items=[]
  for url in urls:
   try:
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (EL EDITOR RSS personal)','Accept':'application/rss+xml, application/xml, text/xml'})
    with urllib.request.urlopen(req,timeout=12) as response:raw=response.read(3_000_000)
    all_items=parse_rss(raw,source)
    if all_items:break
   except Exception as exc:statuses[source]=str(exc)[:120]
  results[source]=all_items
  if all_items:statuses[source]=f'{len(all_items)} artículos recientes'
 # Images supplied by several RSS feeds are incomplete. Probe each publisher's
 # original article metadata before ranking the shortlists (never use guessed images).
 from imagenes_v159 import extract_image
 from miniaturas_v14 import embed
 from concurrent.futures import ThreadPoolExecutor
 candidates=[]
 for source,items in results.items():
  filtered=[x for x in items if (NATURE if source=='Muy Interesante' else ANIMALS).search(x['title']+' '+x.get('summary',''))]
  candidates.extend(filtered[:12])
 missing=[x for x in candidates if not x.get('image')]
 if missing:
  with ThreadPoolExecutor(max_workers=6) as pool:
   probes=list(pool.map(extract_image,[x['url'] for x in missing]))
  for article,(image,status,url) in zip(missing,probes):
   if image:article['image']=image
   article['foto_origen_estado']=status
 embed(candidates,max_articles=len(candidates))
 used=set(); chosen=[]
 def pick(source,predicate):
  eligible=[x for x in results.get(source,[]) if x['id'] not in used and predicate(x)]
  # A visible verified photo is useful, but recency remains important.
  eligible.sort(key=lambda a:(bool(a.get('image_data')),bool(a.get('image')),a['date']),reverse=True)
  if eligible:used.add(eligible[0]['id']);return eligible[0]
  return None
 # Strict source slots; use no invented placeholder articles.
 a=pick('Muy Interesante',lambda x:bool(NATURE.search(x['title']+' '+x.get('summary',''))))
 if a:chosen.append({'slot':0,'article':a})
 # rotation across the two specified animal sources
 hist_path=ROOT/'nature_rotacion_v166.json'
 try:hist=json.loads(hist_path.read_text(encoding='utf-8'))
 except Exception:hist={}
 sources=['National Geographic España','Muy Interesante']
 if hist.get('slot2_source') in sources:sources.reverse() if hist['slot2_source']==sources[0] else None
 b=None
 for source in sources:
  b=pick(source,lambda x:bool(ANIMALS.search(x['title'])))
  if b:hist['slot2_source']=source;break
 if b:chosen.append({'slot':1,'article':b})
 c=pick('ECOticias',lambda x:bool(ANIMALS.search(x['title'])))
 if c:chosen.append({'slot':2,'article':c})
 hist_path.write_text(json.dumps(hist,ensure_ascii=False),encoding='utf-8')
 payload={'articles':chosen,'status':statuses}
 print('NATURE: noticias seleccionadas',len(chosen),'de 3.',flush=True)
 CACHE.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
 return payload
if __name__=='__main__':
 import sys
 print(collect('--online' in sys.argv))
