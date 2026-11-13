"""Descarga miniaturas públicas de imágenes enlazadas por feeds; las incrusta en HTML personal local.
No modifica el artículo original. Límite de tamaño y de respuesta para evitar descargas excesivas.
"""
from urllib.request import Request,urlopen
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
try:
 from PIL import Image,ImageOps
except ImportError:
 Image=None
 ImageOps=None
import base64,ipaddress

def valid(u):
 try:
  p=urlparse(u)
  if p.scheme!='https' or not p.hostname or p.username or p.password:return False
  try:
   if not ipaddress.ip_address(p.hostname).is_global:return False
  except ValueError:pass
  return True
 except Exception:return False

def fetch(url):
 if not valid(url):return ''
 try:
  req=Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; EL EDITOR personal preview; image cache)','Accept':'image/avif,image/webp,image/jpeg,image/png,image/*;q=0.7','Referer':'https://'+urlparse(url).netloc+'/'})
  with urlopen(req,timeout=7) as r:
   if not valid(r.geturl()):return ''
   mime=r.headers.get('Content-Type','').lower().split(';')[0].strip()
   if mime not in ('image/jpeg','image/png','image/webp','image/avif'):return ''
   raw=r.read(3_000_001)
  if len(raw)>3_000_000:return ''
  if Image is None:
   if len(raw)>3_000_000:return ''
   return 'data:'+mime+';base64,'+base64.b64encode(raw).decode('ascii')
  im=Image.open(BytesIO(raw));im=ImageOps.exif_transpose(im);im.thumbnail((1000,720),Image.Resampling.LANCZOS)
  if im.width<150 or im.height<90:return ''
  if im.mode not in ('RGB','L'):im=im.convert('RGB')
  buf=BytesIO();im.save(buf,'JPEG',quality=78,optimize=True)
  return 'data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode('ascii')
 except Exception:return ''

def embed(articles,max_articles=100):
 selected=[a for a in articles if valid(a.get('image',''))][:max_articles]
 urls=list(dict.fromkeys(a['image'] for a in selected))
 if not urls:return (0,0)
 with ThreadPoolExecutor(max_workers=8) as pool:
  output=dict(zip(urls,pool.map(fetch,urls)))
 count=0
 for a in selected:
  if output.get(a['image']):a['image_data']=output[a['image']];count+=1
 return count,len(urls)
