"""Elige una noticia reciente de cine o series de SensaCine."""
import datetime as dt

def pick_sensacine(articles,online=True):
 if not online:return None
 now=dt.datetime.now(dt.timezone.utc);pool=[]
 for a in articles:
  if a.get('source')!='SensaCine':continue
  try:
   d=dt.datetime.fromisoformat(str(a.get('published_utc','')).replace('Z','+00:00'))
   age=(now-d).total_seconds()/3600
   if not 0<=age<=72:continue
  except (TypeError,ValueError):continue
  t=a.get('title','').casefold()
  score=(6 if any(x in t for x in ('estreno','película','cine','óscar','oscar','taquilla','tráiler')) else 0)+(3 if a.get('image_candidate') else 0)+max(0,4-age/18)
  pool.append((score,d,a))
 if not pool:return None
 a=max(pool,key=lambda x:(x[0],x[1]))[2]
 return {'id':a['id'],'title':a['title'],'source':'SensaCine','url':a['url'],'date':a.get('published_utc',''),'sections':['Entretenimiento'],'primary':'Entretenimiento','score':0,'cross':False,'topics':['Cine'],'priorities':['media'],'image':a.get('image_candidate','')}
