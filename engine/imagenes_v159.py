"""EL EDITOR v1.5.9: recover publication image using original publisher metadata.
No keyword-based image guesses. Only attach images explicitly linked by the article page.
"""
from html.parser import HTMLParser
from urllib.parse import urlparse,urljoin
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
from imagenes_v13 import safe_url,google_original
import json,html,re

class PageParser(HTMLParser):
 def __init__(self):
  super().__init__();self.meta=[];self.jsonld=[];self.in_json=False;self.buf=[];self.canonical=''
 def handle_starttag(self,tag,attrs):
  a={k.lower():v for k,v in attrs if k}
  if tag=='meta':
   key=(a.get('property') or a.get('name') or '').lower()
   if key in ('og:image','og:image:url','og:image:secure_url','twitter:image','twitter:image:src'):
    if a.get('content'):self.meta.append(a['content'])
  if tag=='link' and a.get('rel','').lower()=='image_src' and a.get('href'):self.meta.append(a['href'])
  if tag=='link' and 'canonical' in a.get('rel','').lower():self.canonical=a.get('href','')
  if tag=='script' and 'ld+json' in a.get('type','').lower():self.in_json=True;self.buf=[]
 def handle_data(self,data):
  if self.in_json:self.buf.append(data)
 def handle_endtag(self,tag):
  if tag=='script' and self.in_json:
   self.in_json=False
   try:self.jsonld.append(json.loads(''.join(self.buf)))
   except (ValueError,TypeError):pass

def ld_images(data):
 if isinstance(data,list):
  for x in data:yield from ld_images(x)
 if isinstance(data,dict):
  typ=data.get('@type','')
  if isinstance(typ,list):typ=' '.join(map(str,typ))
  if any(x in str(typ) for x in ('NewsArticle','Article','BlogPosting','ReportageNewsArticle')):
   imgs=data.get('image',[])
   if isinstance(imgs,(str,dict)):imgs=[imgs]
   for img in imgs:
    if isinstance(img,str):yield img
    if isinstance(img,dict):
     for key in ('url','contentUrl'):
      if isinstance(img.get(key),str):yield img[key]
  if '@graph' in data:yield from ld_images(data['@graph'])

def extract_image(url):
 if not safe_url(url):return ('','INVALID_URL','')
 host=urlparse(url).hostname or ''
 if host in ('news.google.com','www.news.google.com'):
  resolved=google_original(url)
  if not resolved:return ('','GOOGLE_NO_RESUELTO','')
  url=resolved
 elif host.endswith('google.com'):return ('','GOOGLE_NO_RESUELTO','')
 try:
  req=Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'text/html,application/xhtml+xml','Accept-Language':'es-ES,es;q=0.9,en;q=0.7'})
  with urlopen(req,timeout=8) as r:
   final=r.geturl()
   if not safe_url(final):return ('','REDIRECCION_NO_SEGURA','')
   if 'html' not in r.headers.get('Content-Type','').lower():return ('','NO_HTML',final)
   body=r.read(1_100_000)
  parser=PageParser();parser.feed(body.decode('utf-8','replace'))
  candidates=parser.meta+list(ld_images(parser.jsonld))
  for c in candidates:
   candidate=urljoin(final,html.unescape(c.strip()))
   if safe_url(candidate) and not re.search(r'\.(?:svg|gif|ico)(?:\?|$)',candidate,re.I):return (candidate,'META_ORIGINAL',final)
  return ('','SIN_METADATOS',final)
 except Exception as exc:
  return ('','ERROR_'+type(exc).__name__,url)

def enrich(articles):
 selected=[a for a in articles if not a.get('image') and safe_url(a.get('url',''))]
 urls=list(dict.fromkeys(a['url'] for a in selected))
 results={}
 if urls:
  with ThreadPoolExecutor(max_workers=7) as pool:
   results=dict(zip(urls,pool.map(extract_image,urls)))
 count=0
 for a in articles:
  if a.get('image'):
   a['foto_origen_estado']='RSS_CON_IMAGEN';a['foto_url_original']=a.get('url','');continue
  if a.get('url','') in results:
   img,status,final=results[a['url']]
   a['foto_origen_estado']=status;a['foto_url_original']=final
   if img:a['image']=img;count+=1
  else:a['foto_origen_estado']='NO_EVALUADA';a['foto_url_original']=''
 return count
