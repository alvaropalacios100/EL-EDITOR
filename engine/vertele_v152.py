import datetime as dt

def pick_vertele(articles,online=True):
 if not online:return None
 now=dt.datetime.now(dt.timezone.utc)
 pool=[]
 for a in articles:
  if a.get('source')!='Vertele' or a.get('possible_duplicate_of'):continue
  try:
   d=dt.datetime.fromisoformat(str(a.get('published_utc','')).replace('Z','+00:00'))
   if d.tzinfo is None:continue
   age=(now-d).total_seconds()/3600
   if not 0<=age<=72:continue
  except (ValueError,TypeError):continue
  t=a.get('title','').casefold()
  interest=5 if any(k in t for k in ('televisi','audiencia','estreno','programa','entrevista','cadena','presentador','serie','la revuelta','salvados','évole','intxaurrondo','giro')) else 0
  pool.append((interest+max(0,6-age/12),d,a))
 if not pool:return None
 a=max(pool,key=lambda p:(p[0],p[1]))[2]
 return {'id':a['id'],'title':a['title'],'source':'Vertele','url':a['url'],'date':a.get('published_utc',''),'sections':['Entretenimiento'],'primary':'Entretenimiento','score':0,'cross':False,'topics':['Actualidad televisiva'],'priorities':['media'],'image':a.get('image_candidate','')}
