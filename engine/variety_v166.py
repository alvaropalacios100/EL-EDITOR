"""RSS de Variety: titulares traducidos, atribución y enlace originales."""
import re,html,json,hashlib,urllib.request,urllib.parse,xml.etree.ElementTree as ET,datetime,email.utils
from pathlib import Path
from espectador_internacional_v164 import translate
ROOT=Path(__file__).resolve().parent
CACHE=ROOT/'variety_v166.json'
TRANS=ROOT/'traducciones_variety_v166.json'
URL='https://variety.com/feed/'
HEAD={'User-Agent':'Mozilla/5.0 (EL EDITOR personal RSS reader)','Accept-Language':'en-US,en;q=0.9'}

def collect(online=False):
 if not online:
  try:return json.loads(CACHE.read_text(encoding='utf-8'))
  except Exception:return []
 try:
  req=urllib.request.Request(URL,headers=HEAD)
  with urllib.request.urlopen(req,timeout=15) as rsp:raw=rsp.read(3_000_000)
  root=ET.fromstring(raw)
 except Exception:return collect(False)
 try:trans=json.loads(TRANS.read_text(encoding='utf-8'))
 except Exception:trans={}
 out=[];now=datetime.datetime.now(datetime.timezone.utc)
 for node in root.findall('.//item')[:65]:
  title=html.unescape(re.sub('<[^>]+>','',(node.findtext('title') or '').strip()))
  link=(node.findtext('link') or '').strip()
  date=(node.findtext('pubDate') or '').strip()
  try:d=email.utils.parsedate_to_datetime(date).astimezone(datetime.timezone.utc)
  except Exception:continue
  if not 0<=(now-d).total_seconds()<=21*86400:continue
  if not title or not urllib.parse.urlparse(link).hostname or not urllib.parse.urlparse(link).hostname.endswith('variety.com'):continue
  categories=' '.join((x.text or '') for x in node.findall('category')).lower()
  if re.search(r'\b(video game|videogame|gaming|steam|fortnite)\b',title,re.I):continue
  entertainment=bool(re.search(r'film|movie|tv|television|stream|series|box office|cinema|oscars?|screen|studio|director|showrunner|theater|theatre',title+' '+categories,re.I))
  celebrities=bool(re.search(r'music|song|album|concert|singer|tour|pop star|grammy|celebrity|artist',title+' '+categories,re.I))
  if not entertainment and not celebrities:continue
  section='Celebrities' if celebrities and not entertainment else 'Entretenimiento'
  image=''
  for child in node.iter():
   tag=child.tag.split('}')[-1].lower()
   if tag in ('thumbnail','content','enclosure') and child.attrib.get('url','').startswith('https://'):
    image=child.attrib['url'];break
  display=translate(title,trans)
  out.append({'id':'variety-'+hashlib.sha1(link.encode()).hexdigest()[:15],'title':display,'original_title':title,'source':'Variety','url':link,
              'date':d.isoformat(),'image':image,'score':23,'topics':['Cine y televisión internacional' if section=='Entretenimiento' else 'Música y celebridades'],
              'primary':section,'sections':[section],'translation_ok':display!=title})
  if len(out)>=18:break
 if out:
  CACHE.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
  TRANS.write_text(json.dumps(trans,ensure_ascii=False,indent=2),encoding='utf-8')
  return out
 return collect(False)
