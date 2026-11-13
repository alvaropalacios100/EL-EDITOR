"""Una noticia de FórmulaTV que sea reciente, sin inventar resultados."""
import datetime as dt,re

def pick_formula(articles):
 now=dt.datetime.now(dt.timezone.utc)
 pool=[]
 for a in articles:
  if a.get('source')!='FórmulaTV' or a.get('possible_duplicate_of'):continue
  date=a.get('published_utc','')
  try:
   d=dt.datetime.fromisoformat(date.replace('Z','+00:00'))
   age=(now-d).total_seconds()/3600
   if not 0<=age<=72:continue
  except:continue
  title=a.get('title','');t=title.casefold()
  # Importancia aproximada: noticias de televisión relevantes, actualidad y recencia.
  extra=5 if any(k in t for k in ['audiencias','estreno','drag race','operación triunfo','eurovisión','benidorm fest','la 1','rtve','televisión','audiencia']) else 0
  extra+=2 if any(k in t for k in ['serie','programa','presentador','cadena','cancelación','renueva','estren']) else 0
  score=extra+max(0,6-age/12)
  pool.append((score,d,a))
 if not pool:return None
 a=max(pool,key=lambda x:(x[0],x[1]))[2]
 return {'id':a['id'],'title':a['title'],'source':a['source'],'url':a['url'],'date':a.get('published_utc',''),'sections':['Entretenimiento'],'primary':'Entretenimiento','score':0,'cross':False,'topics':['Actualidad televisiva'],'priorities':['media'],'image':a.get('image_candidate','')}
