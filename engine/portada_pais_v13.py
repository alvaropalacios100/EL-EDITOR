"""Recupera dos noticias generales recientes del RSS multimedia de portada de El País."""
import datetime as dt,email.utils,json,re,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
from motor_v02 import image_from,clean
RSS='https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada'
MAX_HOURS=72

def grab(e,tag):
 child=e.find(tag)
 return ''.join(child.itertext()).strip() if child is not None else ''

def is_recent(s):
 try:
  d=email.utils.parsedate_to_datetime(s)
  if d.tzinfo is None:d=d.replace(tzinfo=dt.timezone.utc)
  age=(dt.datetime.now(dt.timezone.utc)-d).total_seconds()/3600
  return (d.isoformat(), 0<=age<=MAX_HOURS)
 except Exception:return ('',False)

def valid_cache(cache):
 try:
  entries=json.loads(cache.read_text(encoding='utf8'))
  if not isinstance(entries,list):return []
  out=[]
  for a in entries:
   date=dt.datetime.fromisoformat(a['date'])
   if date.tzinfo and 0<=(dt.datetime.now(dt.timezone.utc)-date).total_seconds()/3600<=MAX_HOURS:out.append(a)
  return out[:2]
 except Exception:return []

def collect_pais_pair(online,root):
 cache=Path(root)/'portada_pais_v13.json'
 if not online:return valid_cache(cache)
 try:
  req=urllib.request.Request(RSS,headers={'User-Agent':'Mozilla/5.0 (EL EDITOR personal RSS reader)','Accept':'application/rss+xml, application/xml, text/xml'})
  with urllib.request.urlopen(req,timeout=16) as rsp:raw=rsp.read(2_000_000)
  rootxml=ET.fromstring(raw); candidates=[]
  for index,e in enumerate(rootxml.findall('.//item')):
   title=clean(grab(e,'title'));url=grab(e,'link');date,good=is_recent(grab(e,'pubDate'))
   if not title or not re.match(r'^https://(www\.)?elpais\.com/',url) or not good:continue
   cat=' '.join(grab(x,'') if False else ''.join(x.itertext()) for x in e.findall('category')).casefold()
   if any(x in cat for x in ['deportes','fútbol','futbol','opinión','opinion','cultura','gastronomía','gastronomia']):continue
   if any(x in title.casefold() for x in ['real madrid','horóscopo','horoscopo','liga de campeones']):continue
   candidate={'id':'elpais-'+str(index)+'-'+re.sub(r'[^0-9]','',date),'title':title,'url':url,'date':date,'source':'El País','primary':'Política','sections':['Política'],'topics':['Actualidad general'],'priorities':['media'],'score':0,'cross':False,'image':image_from(e,grab(e,'description'))}
   candidates.append(candidate)
  # Preferir fotografias validas sin salir de los articulos recientes del mismo RSS.
  candidates.sort(key=lambda a:bool(a.get('image')),reverse=True)
  result=[]
  for a in candidates:
   if any(a['url']==b['url'] or len(set(a['title'].lower().split())&set(b['title'].lower().split()))/max(1,len(set(a['title'].lower().split())|set(b['title'].lower().split())))>.78 for b in result):continue
   result.append(a)
   if len(result)==2:break
  if result:cache.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
  print('El País portada:',len(result),'noticias generales recientes')
  return result or valid_cache(cache)
 except Exception as exc:
  print('El País portada: RSS no accesible:',str(exc)[:150])
  return valid_cache(cache)
