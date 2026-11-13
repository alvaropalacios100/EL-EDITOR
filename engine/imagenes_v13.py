"""Obtiene URL de miniaturas publicadas en metadatos de noticias de origen.
Solo se consulta en modo online y no se almacenan ni redistribuyen archivos de imagen.
Las webs originales pueden impedir el acceso externo a sus imágenes.
"""
from html.parser import HTMLParser
from urllib.parse import urlparse,urljoin
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
import ipaddress,re

class MetaImage(HTMLParser):
 def __init__(self):super().__init__();self.options=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='meta' and (a.get('property','').lower() in ('og:image','og:image:url') or a.get('name','').lower() in ('twitter:image','twitter:image:src')):
   if a.get('content'):self.options.append(a['content'])
  if tag=='link' and a.get('rel','').lower()=='image_src' and a.get('href'):self.options.append(a['href'])

def safe_url(url):
 try:
  p=urlparse(url)
  if p.scheme!='https' or not p.hostname:return False
  if p.username or p.password:return False
  try:
   addr=ipaddress.ip_address(p.hostname)
   if not addr.is_global:return False
  except ValueError:pass
  return True
 except:return False

def google_original(page_url):
 """Only use a verified external article URL, never infer one from a headline."""
 try:
  if urlparse(page_url).hostname!='news.google.com':return page_url
  req=Request(page_url,headers={'User-Agent':'Mozilla/5.0','Accept':'text/html'})
  with urlopen(req,timeout=7) as res:
   final=res.geturl()
   if safe_url(final) and urlparse(final).hostname not in ('news.google.com','www.google.com'):return final
   page=res.read(350_000).decode('utf-8','replace')
  # News articles sometimes publish their canonical original link as a data attribute.
  for pattern in (r'data-n-au=["\'](https://[^"\']+)',r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\'](https://[^"\']+)'):
   for candidate in re.findall(pattern,page,re.I):
    candidate=candidate.replace('&amp;','&')
    if safe_url(candidate) and urlparse(candidate).hostname not in ('news.google.com','www.google.com'):return candidate
 except Exception:pass
 return ''
def find_meta_image(page_url):
 if not safe_url(page_url):return ''
 host=urlparse(page_url).hostname or ''
 if host.endswith('news.google.com'):
  page_url=google_original(page_url)
  if not page_url:return ''
 elif host.endswith('google.com'):return '' 
 try:
  req=Request(page_url,headers={'User-Agent':'Mozilla/5.0 (compatible; ElEditorPersonal/1.3; rss images)', 'Accept':'text/html,application/xhtml+xml'})
  with urlopen(req,timeout=5) as res:
   if not safe_url(res.geturl()):return ''
   typ=res.headers.get('content-type','')
   if 'html' not in typ:return ''
   contents=res.read(650_000)
  html=contents.decode('utf-8','replace'); parser=MetaImage();parser.feed(html)
  for item in parser.options:
   img=urljoin(page_url,item.strip())
   if safe_url(img) and not img.lower().split('?')[0].endswith(('.svg','.gif','.ico')):return img
 except Exception:pass
 return ''

def enrich(articles,limit=25):
 todo=[a for a in articles if not a.get('image') and safe_url(a.get('url',''))]
 todo=todo[:limit]
 if not todo:return 0
 with ThreadPoolExecutor(max_workers=6) as executor:
  matches=list(executor.map(lambda a:find_meta_image(a['url']),todo))
 found=0
 for a,img in zip(todo,matches):
  if img:a['image']=img;found+=1
 return found
