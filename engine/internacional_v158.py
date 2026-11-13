"""Three editorial slots: foreign reporting substantively about Spain. No invented articles or titles."""
import re,html,datetime,urllib.request,urllib.parse,xml.etree.ElementTree as ET,json,hashlib,concurrent.futures,csv
from html.parser import HTMLParser
from pathlib import Path
from imagenes_v13 import find_meta_image
ROOT=Path(__file__).resolve().parent
SOURCES={
 'The Guardian':('https://www.theguardian.com/world/europe-news/rss','theguardian.com','en'),
 'Der Spiegel':('https://www.spiegel.de/international/index.rss','spiegel.de','de'),
 'Libération':('https://www.liberation.fr/arc/outboundfeeds/rss-all/','liberation.fr','fr'),
 'Le Monde':('https://www.lemonde.fr/international/rss_full.xml','lemonde.fr','fr'),
 'The New York Times':('https://rss.nytimes.com/services/xml/rss/nyt/Europe.xml','nytimes.com','en'),
 'The Washington Post':('https://feeds.washingtonpost.com/rss/world','washingtonpost.com','en'),
 'NYT en Español':('https://rss.nytimes.com/services/xml/rss/nyt/es.xml','nytimes.com','es')}
PAIRS=[['The Guardian','Der Spiegel'],['Libération','Le Monde'],['NYT en Español','The New York Times','The Washington Post']]
HISTORY=ROOT/'historial_internacional.json'
HDR={'User-Agent':'Mozilla/5.0 (compatible; EL EDITOR personal reader)','Accept-Language':'es,en;q=0.8'}
SPAIN=re.compile(r'\b(españa|espan[ao]l(?:es|as|a)?|spain|spanish|spanien|spanisch(?:e|en|er)?|espagne|espagnol(?:e|s)?|espagn[eé]s?)\b',re.I)
SECONDARY=re.compile(r'\b(madrid|barcelona|catalu(?:nya|ña|nia)|catalonia|andaluc[ií]a|valencia|sanchez|sánchez|pedro s[aá]nchez|prado|basque country)\b',re.I)
NS={'media':'http://search.yahoo.com/mrss/','content':'http://purl.org/rss/1.0/modules/content/','atom':'http://www.w3.org/2005/Atom'}
class Img(HTMLParser):
 def __init__(self):super().__init__();self.images=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='img':self.images.append(a.get('src',''))
def plain(s):return html.unescape(re.sub('<[^>]*>',' ',str(s or ''))).strip()
def download(url):
 try:
  req=urllib.request.Request(url,headers=HDR)
  with urllib.request.urlopen(req,timeout=10) as r:return r.read(1_100_000)
 except Exception:return b''
def rss_read(url,source,lang):
 raw=download(url)
 if not raw:return []
 try:root=ET.fromstring(raw)
 except ET.ParseError:return []
 items=root.findall('.//item'); out=[]
 if not items:items=root.findall('.//atom:entry',NS)
 for e in items[:60]:
  def get(name):return (e.findtext(name) or '').strip()
  title=plain(get('title') or get('{http://www.w3.org/2005/Atom}title'))
  link=get('link')
  if not link:
   node=e.find('atom:link',NS);link=node.get('href','') if node is not None else ''
  desc=plain(get('description') or get('{http://www.w3.org/2005/Atom}summary'))
  date=get('pubDate') or get('{http://www.w3.org/2005/Atom}updated')
  pic=''
  for el in e.findall('media:content',NS)+e.findall('media:thumbnail',NS)+e.findall('enclosure'):
   candidate=el.get('url','');typ=el.get('type','');
   if candidate.startswith('https://') and (not typ or typ.startswith('image/')):pic=candidate;break
  if title and link.startswith('http'):out.append({'title':title,'summary':desc,'url':link,'date':date,'image':pic,'source':source,'language':lang})
 return out
def news_fallback(source,domain,lang):
 # Google News is discovery only: direct sources are preferred for photographs and accurate links.
 q='site:'+domain+' (Spain OR España OR Spanien OR Espagne)'
 url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':q,'hl':'en-US','gl':'US','ceid':'US:en'})
 return rss_read(url,source,lang)
def relevant(a):
 t=a['title'];s=a.get('summary','')
 # Strong subject requirement: Spain in headline, or meaningful mention in both headline and summary.
 # Madrid and Barcelona alone do not count unless summary explicitly connects to Spain.
 return bool(SPAIN.search(t)) or (bool(SECONDARY.search(t)) and bool(SPAIN.search(s)))
def fresh(a,now):
 from email.utils import parsedate_to_datetime
 try:
  d=parsedate_to_datetime(a['date'])
 except Exception:
  try:d=datetime.datetime.fromisoformat(a['date'].replace('Z','+00:00'))
  except:return False
 if d.tzinfo is None:d=d.replace(tzinfo=datetime.timezone.utc)
 return -3600 <= (now-d).total_seconds() <= 21*86400
def translate(text,lang,cache):
 if lang=='es':return text,True
 k=lang+'|'+text
 if k in cache:return cache[k],True
 try:
  url='https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode({'client':'gtx','sl':lang,'tl':'es','dt':'t','q':text})
  data=json.loads(download(url).decode('utf-8'))
  translated=''.join(part[0] for part in data[0] if part and part[0]).strip()
  if translated and translated!=text:cache[k]=translated;return translated,True
 except Exception:pass
 return text,False

def headline_language(title, declared):
 # Detect clear English headlines incorrectly labeled Spanish by a feed/fallback.
 if declared!='es':return declared
 t=' '+re.sub(r'[^a-zA-Záéíóúñü ]',' ',title.lower())+' '
 en=len(re.findall(r'\b(the|with|after|over|amid|how|why|what|will|could|should|spain|spanish|against|about|from|into|says|new|government)\b',t))
 es=len(re.findall(r'\b(el|la|los|las|del|por|para|que|una|un|españa|gobierno|sobre|ante|tras|según|con|desde|como|más)\b',t))
 return 'en' if en>=2 and en>es else declared

def collect(online=False):
 cachefile=ROOT/'internacional_cache_v158.json';translationfile=ROOT/'traducciones_v158.json'
 if not online:
  try:return json.loads(cachefile.read_text(encoding='utf-8'))
  except Exception:return {'articles':[],'status':{'modo':'sin datos en caché; ejecutar online'}}
 now=datetime.datetime.now(datetime.timezone.utc)
 old={};translations={}
 try:old=json.loads(HISTORY.read_text(encoding='utf-8'))
 except Exception:pass
 try:translations=json.loads(translationfile.read_text(encoding='utf-8'))
 except Exception:pass
 def get(s):
  url,domain,lang=SOURCES[s];records=rss_read(url,s,lang)
  valid=[a for a in records if relevant(a) and fresh(a,now)]
  if not valid:
   records+=news_fallback(s,domain,lang)
   valid=[a for a in records if relevant(a) and fresh(a,now)]
  return valid
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
  result=dict(zip(SOURCES,pool.map(get,SOURCES)))
 selected=[];status={};last=old.get('last',{})
 with (ROOT/'diagnostico_internacional_v158.csv').open('w',encoding='utf-8-sig',newline='') as file:
  writer=csv.writer(file);writer.writerow(['Medio','Candidatos recientes sobre España','Fuente RSS configurada','Seleccionado para mini sección'])
  for source,(feed,domain,lang) in SOURCES.items():
   writer.writerow([source,len(result.get(source,[])),feed,'Pendiente de selección'])
 for slot,pair in enumerate(PAIRS,1):
  candidates=[]
  for s in pair:
   for a in result[s]:
    score=(1 if s!=last.get(str(slot)) else 0)*100 + (10 if a['image'] else 0) + (3 if a['language']=='es' else 0)
    candidates.append((score,a))
  candidates.sort(key=lambda p:(p[0],p[1].get('date','')),reverse=True)
  chosen=None
  for _,a in candidates:
   if not any(x['url']==a['url'] for x in selected):chosen=a;break
  if chosen:
   original=chosen['title'];chosen['language']=headline_language(original,chosen['language']);chosen['detected_language']=chosen['language'];shown,translated=translate(original,chosen['language'],translations)
   chosen['title']=shown;chosen['original_title']=original;chosen['translated']=translated;chosen['slot']=slot
   chosen['id']='int-'+hashlib.sha1(chosen['url'].encode()).hexdigest()[:16]
   chosen['primary']='Internacional';chosen['score']=40;chosen['topics']=['España'];chosen['sections']=['Internacional']
   chosen['image']=chosen.get('image') or find_meta_image(chosen['url'])
   try:
    from email.utils import parsedate_to_datetime
    chosen['date']=parsedate_to_datetime(chosen['date']).astimezone(datetime.timezone.utc).isoformat()
   except Exception:pass
   selected.append(chosen)
   status[str(slot)]=chosen['source']+(' · traducido' if translated and chosen['language']!='es' else ' · titular original')
  else:status[str(slot)]='sin noticias recientes verificables sobre España'
 try:
  selected_sources={x['source'] for x in selected}
  with (ROOT/'diagnostico_internacional_v158.csv').open('w',encoding='utf-8-sig',newline='') as file:
   writer=csv.writer(file);writer.writerow(['Medio','Candidatos recientes sobre España','Fuente RSS configurada','Seleccionado para mini sección'])
   for source,(feed,domain,lang) in SOURCES.items():writer.writerow([source,len(result.get(source,[])),feed,'Sí' if source in selected_sources else 'No'])
  translationfile.write_text(json.dumps(translations,ensure_ascii=False,indent=2),encoding='utf-8')
  HISTORY.write_text(json.dumps({'last':{str(x['slot']):x['source'] for x in selected}},ensure_ascii=False,indent=2),encoding='utf-8')
  cachefile.write_text(json.dumps({'articles':selected,'status':status},ensure_ascii=False,indent=2),encoding='utf-8')
 except Exception:pass
 return {'articles':selected,'status':status}
