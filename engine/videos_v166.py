"""EL EDITOR v1.6.6: rotación verificada por huecos de vídeos.
El origen es YouTube; no fabrica IDs. Las búsquedas no equivalen a un feed cronológico garantizado.
"""
import json,random,re,datetime,concurrent.futures,urllib.parse,urllib.request,unicodedata
from pathlib import Path
from videos_v07 import fetch,text,simple,parse_views,translate_sims_title
ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/'video_slots_v166.json').read_text(encoding='utf-8'))
HISTORY=ROOT/'historial_videos_v166.json'
CACHE=ROOT/'videos_v166.json'
HEADERS={'User-Agent':'Mozilla/5.0','Accept-Language':'es-ES,es;q=0.9'}
def age_days(raw):
 s=simple(raw).strip()
 if any(x in s for x in ('hace un momento','just now','today','hoy','yesterday','ayer')):return 0
 m=re.search(r'(\d+)\s*(seconds?|segundos?|minutes?|minutos?|hours?|horas?|days?|dias?|weeks?|semanas?|months?|meses?|years?|anos?)',s)
 if not m:return None
 n=int(m.group(1)); unit=m.group(2)
 if any(x in unit for x in ('year','ano')):return n*365
 if any(x in unit for x in ('month','mes')):return n*30
 if any(x in unit for x in ('week','semana')):return n*7
 if any(x in unit for x in ('day','dia')):return n
 return 0
def clean(s):return ''.join(c for c in unicodedata.normalize('NFKD',simple(s)) if not unicodedata.combining(c)).replace(' ', '').replace('.', '')
def select_variant(cfg):
 """Try a targeted and then a broad channel search; never pass an unverified uploader."""
 queries=[cfg['query']]
 broad=(cfg.get('channel') or '').replace(' · Hoy por Hoy','').replace('_',' ')+' '+('trailer' if cfg.get('max_months')==2 else 'videos')
 if clean(broad)!=clean(cfg['query']):queries.append(broad)
 outcomes=[];errors=[];seen=set()
 for query in queries:
  try:found=fetch(query)
  except Exception as e:errors.append(type(e).__name__+': '+str(e)[:100]);continue
  for rank,v in enumerate(found):
   vid=v.get('videoId','');title=text(v.get('title',{}))
   author=text(v.get('ownerText',{})) or text(v.get('longBylineText',{}))
   if not re.fullmatch(r'[A-Za-z0-9_-]{11}',vid) or vid in seen:continue
   # The uploader MUST be identifiable; never infer the real channel from the query.
   if not author or not any(clean(x) in clean(author) for x in cfg.get('match',[])):continue
   if cfg.get('topic') and not any(clean(x) in clean(title) for x in cfg['topic']):continue
   pub=text(v.get('publishedTimeText',{}));age=age_days(pub)
   maxmo=cfg.get('max_months',0)
   if maxmo and (age is None or age>maxmo*31):continue
   if age is not None and age<0:continue
   duration=text(v.get('lengthText',{}))
   try:seconds=sum(int(n)*60**i for i,n in enumerate(reversed(duration.split(':')))) if duration else None
   except Exception:seconds=None
   min_seconds=45 if cfg['channel'] in ('WarnerBros.PicturesEspaña','SonyPicturesSpain','ParamountPicturesES','HBOMaxES','NetflixEspana','disneyspain','disneypluses','Universal_Spain','National Geographic España · Mario de Wonder') else 120
   # YouTube sometimes omits lengthText for real uploads; don't reject those.
   if seconds is not None and seconds<min_seconds:continue
   if 'shorts' in clean(title):continue
   seen.add(vid)
   outcomes.append({'id':vid,'title':title,'channel':cfg['channel'],'original_title':title,
        'duration':duration,'age_days':age,'rank':rank+len(outcomes)*0.01,'views':parse_views(v),
        'translate_title':cfg.get('translate_title',False)})
  if outcomes:break
 return outcomes[:15],('; '.join(errors) if errors else 'Sin vídeo de este canal que cumpla tema y antigüedad')
def collect(online=False):
 if not online:
  try:return json.loads(CACHE.read_text(encoding='utf-8'))
  except Exception:return {'sections':{},'status':{},'generated_at':None}
 try:hist=json.loads(HISTORY.read_text(encoding='utf-8'))
 except Exception:hist={}
 try:old=json.loads(CACHE.read_text(encoding='utf-8'))
 except Exception:old={'sections':{},'generated_at':None}
 old_by_slot={(sec,x['slot']):x['video'] for sec,entries in old.get('sections',{}).items() for x in entries if x.get('video')}
 try:
  past=datetime.datetime.fromisoformat(old.get('generated_at',''))
  elapsed=max(0,(datetime.datetime.now(datetime.timezone.utc)-past).total_seconds()/86400)
 except Exception:elapsed=99999

 all_slots=[(sec,i,entry) for sec,entries in CFG.items() for i,entry in enumerate(entries)]
 # Pick the next candidate for each slot. Try a different source if that candidate is unavailable.
 # When both slots can show Alán, pick opposite sources.
 choice={}
 for sec,i,entry in all_slots:
  k=f'{sec}-{i}'
  n=len(entry['candidates'])
  choice[k]=((hist.get(k,{}).get('index',-1)+1)%n) if n else 0
 if choice['gabinete-0']==0: choice['gabinete-1']=1
 else:choice['gabinete-1']=0
 work=[]
 for sec,i,entry in all_slots:
  k=f'{sec}-{i}';n=len(entry['candidates'])
  order=[(choice[k]+j)%n for j in range(n)]
  work.append((sec,i,entry,order))
 def one(job):
  sec,i,entry,order=job
  for idx in order:
   cfg=entry['candidates'][idx]
   results,error=select_variant(cfg)
   if results:
    prior_id=hist.get(f'{sec}-{i}',{}).get('id')
    mode=cfg.get('mode','latest')
    # Un hueco 'latest' debe conservar el más reciente; no forzar uno viejo por rotación.
    candidates=results if mode=='latest' else ([v for v in results if v['id']!=prior_id] or results)
    if mode in ('random','random_latest'):
     selected=random.choice(candidates[:10])
    elif mode=='last10':
     selected=random.choice(candidates[:10])
    elif mode=='last10_old':
     selected=random.choice(candidates[:10])
    elif mode=='latest_old' and hist.get(f'{sec}-{i}',{}).get('recent',False) and len(candidates)>1:
     selected=random.choice(candidates[1:])
    else:
     # For recent: only choose records with known dates if any, ordered by age then search rank.
     dated=[v for v in candidates if v['age_days'] is not None]
     selected=sorted(dated or candidates,key=lambda v:(v['age_days'] if v['age_days'] is not None else 100000,v['rank']))[0]
    return idx,selected,'OK'
  return None,None,'Ninguna alternativa devolvió un vídeo verificable (canal, tema o fecha)' 
 result={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sections':{},'status':{}}
 translations_path=ROOT/'traducciones_v166.json'
 try:translations=json.loads(translations_path.read_text(encoding='utf-8'))
 except Exception:translations={}
 print('YouTube: comprobando 24 huecos y sus canales autorizados...',flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
  results=list(pool.map(one,work))
 used=set()
 for (sec,i,entry,_),(idx,v,status) in zip(work,results):
  k=f'{sec}-{i}'
  result['status'][k]=status
  if not v:
   previous=old_by_slot.get((sec,i))
   if previous:
    maxmonths=max([x.get('max_months',0) for x in entry.get('candidates',[])],default=0)
    age=previous.get('age_days')
    if not maxmonths or (isinstance(age,(int,float)) and age+elapsed<=maxmonths*31):
     v=dict(previous)
     result['status'][k]='Último vídeo verificado conservado: búsqueda actual sin coincidencias'
   if not v:continue
  # If the second Alán slot cannot safely be disambiguated, do not duplicate its video.
  if v['id'] in used:
   result['status'][k]='Vídeo duplicado, omitido';continue
  used.add(v['id'])
  v['slot_label']=entry.get('label','')
  if v.get('translate_title'):
   v['title']=translate_sims_title(v['title'],translations)
  result['sections'].setdefault(sec,[]).append({'slot':i,'video':v})
  hist[k]={'index':idx,'id':v['id'],'recent':not hist.get(k,{}).get('recent',False)}
 print('YouTube: vídeos seleccionados',sum(len(x) for x in result['sections'].values()),'de 24 huecos.',flush=True)
 CACHE.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 HISTORY.write_text(json.dumps(hist,ensure_ascii=False,indent=2),encoding='utf-8')
 if translations:translations_path.write_text(json.dumps(translations,ensure_ascii=False,indent=2),encoding='utf-8')
 return result
if __name__=='__main__':
 import sys
 r=collect('--online' in sys.argv)
 print({k:len(v) for k,v in r['sections'].items()})
