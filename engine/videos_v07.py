"""Busca vídeos de YouTube con biblioteca estándar; no inventa identificadores."""
import json,re,urllib.request,urllib.parse,datetime,random,concurrent.futures
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/'canales_youtube.json').read_text(encoding='utf-8'))
CACHE=ROOT/'videos_v07.json'
HISTORY=ROOT/'historial_celebrities.json'
EXPRESS_HISTORY=ROOT/'historial_podcast_express.json'
HEADERS={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36','Accept-Language':'es-ES,es;q=0.9'}
def simple(t):
 return str(t or '').lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
def text(obj):
 if not isinstance(obj,dict):return ''
 return obj.get('simpleText') or ''.join(x.get('text','') for x in obj.get('runs',[]))
def walk(obj):
 if isinstance(obj,dict):
  if 'videoRenderer' in obj:yield obj['videoRenderer']
  for x in obj.values():yield from walk(x)
 elif isinstance(obj,list):
  for x in obj:yield from walk(x)
def fetch(q):
 url='https://www.youtube.com/results?'+urllib.parse.urlencode({'search_query':q,'sp':'EgIQAQ%3D%3D'})
 req=urllib.request.Request(url,headers=HEADERS)
 with urllib.request.urlopen(req,timeout=16) as resp:html=resp.read(5_000_000).decode('utf-8','replace')
 m=re.search(r'var ytInitialData\s*=\s*({.*?});\s*</script>',html,re.S)
 if not m:m=re.search(r'ytInitialData\s*=\s*({.*?});\s*</script>',html,re.S)
 if not m:raise ValueError('YouTube no ha entregado resultados legibles')
 return list(walk(json.loads(m.group(1))))
def parse_views(v):
 s=simple(text(v.get('viewCountText',{})))
 m=re.search(r'([\d.,]+)\s*(millones|mill[oó]n|mil|k|m)?',s)
 if not m:return 0
 try:
  num=float(m.group(1).replace('.','').replace(',','.'))
  return int(num*(1_000_000 if m.group(2) in ('millones','millon','millón','m') else 1000 if m.group(2) in ('mil','k') else 1))
 except:return 0
def select(cfg,used):
 try:videos=fetch(cfg['query'])
 except Exception as e:return [],str(e)
 options=[]
 for pos,v in enumerate(videos):
  vid=v.get('videoId','');title=text(v.get('title',{}));author=text(v.get('ownerText',{})) or text(v.get('longBylineText',{}))
  if not re.fullmatch('[a-zA-Z0-9_-]{11}',vid) or vid in used:continue
  if not any(simple(k) in simple(author) for k in cfg['match']):continue
  if any(simple(x) in simple(author) for x in cfg.get('exclude',[])):continue
  if cfg['topic'] and not any(simple(x) in simple(title) for x in cfg['topic']):continue
  if cfg.get('exclude_topics') and any(simple(x) in simple(title) for x in cfg['exclude_topics']):continue
  if cfg.get('archive'):
   pub=simple(text(v.get('publishedTimeText',{})))
   if not any(k in pub for k in ('year','año','years','años','months','meses')):continue
  duration=text(v.get('lengthText',{}));parts=duration.split(':')
  try:seconds=sum(int(x)*60**i for i,x in enumerate(reversed(parts)))
  except:seconds=0
  if seconds<180 or 'shorts' in simple(title) or 'en directo' in simple(title):continue
  # Recent relevance first, views as secondary signal; YouTube search is not a guaranteed chronological feed.
  views=parse_views(v)
  score=max(0,100-pos*4)+min(views,1000000)/100000
  options.append((score,{'id':vid,'title':title,'channel':cfg['channel'],'url':'https://www.youtube.com/watch?v='+vid,'views':views,'duration':duration, 'translate_title':bool(cfg.get('translate_title'))}))
 options.sort(key=lambda x:x[0],reverse=True)
 return [x[1] for x in options[:cfg['count']]],''
def translate_sims_title(title, cache):
 """Only use a confirmed translation; never invent Spanish titles."""
 if title in cache:return cache[title]
 try:
  url='https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode({'client':'gtx','sl':'en','tl':'es','dt':'t','q':title})
  req=urllib.request.Request(url,headers=HEADERS)
  with urllib.request.urlopen(req,timeout=7) as resp:payload=json.loads(resp.read(400000).decode('utf-8'))
  result=''.join(row[0] for row in payload[0] if row and row[0]).strip()
  if result and result!=title:cache[title]=result;return result
 except Exception:pass
 return title

def collect(online=False):
 prior={}
 if CACHE.exists():
  try:prior=json.loads(CACHE.read_text(encoding='utf-8'))
  except Exception:pass
 if not online:return prior
 history={'last_channels':[], 'previous_channels':[], 'last_video_ids':[]}
 if HISTORY.exists():
  try:history.update(json.loads(HISTORY.read_text(encoding='utf-8')))
  except Exception:pass
 result={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sections':{},'status':{}}
 translations_path=ROOT/'traducciones_sitycims.json'
 try: translations=json.loads(translations_path.read_text(encoding='utf-8'))
 except Exception: translations={}
 used=set()
 # Fetch in parallel: each source is independent, so one slow channel won't stall all the others.
 def one(c):
  try:return select(c,set())
  except Exception as ex:return [],str(ex)
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
  found_by_channel=list(executor.map(one,CFG))
 pool=[]
 express_pool=[]
 for c,(found,error) in zip(CFG,found_by_channel):
  if not found:
   old=prior.get('sections',{}).get(c['section'],[])
   found=[x for x in old if x.get('channel')==c['channel']][:c['count']]
  if c['section']=='express_podcast':
   if found:express_pool.append(found[0])
   result['status'][c['channel']]='OK' if found else 'Sin vídeo verificable'+(': '+error[:100] if error else '')
   continue
  if c['section']=='celebrities':
   if found:
    v=found[0].copy();v['group']=c.get('group');pool.append(v)
   result['status'][c['channel']]='OK' if found else 'Sin vídeo verificable'+(': '+error[:100] if error else '')
   continue
  accepted=[]
  for item in found:
   if c.get('translate_title'):
    item=item.copy();item['original_title']=item['title'];item['title']=translate_sims_title(item['title'],translations)
   if item.get('id') not in used:
    used.add(item['id']);accepted.append(item)
  result['sections'].setdefault(c['section'],[]).extend(accepted)
  result['status'][c['channel']]='OK: '+str(len(accepted)) if accepted else 'Sin vídeo verificable'+(': '+error[:100] if error else '')
 if translations:translations_path.write_text(json.dumps(translations,ensure_ascii=False,indent=2),encoding='utf-8')
 # v1.3: one video per fixed group, rotate independently by previous channels.
 last_by_group=history.get('last_by_group',{})
 previous_by_group=history.get('previous_by_group',{})
 prev_ids=set(history.get('last_video_ids',[]))
 chosen=[];new_by_group={}
 for group in (1,2,3):
  candidates=[v for v in pool if v.get('group')==group]
  random.SystemRandom().shuffle(candidates)
  last=last_by_group.get(str(group),'');prev=previous_by_group.get(str(group),'')
  candidates.sort(key=lambda x:(x['channel']==last,x['channel']==prev,x['id'] in prev_ids))
  if candidates:
   chosen.append(candidates[0]);new_by_group[str(group)]=candidates[0]['channel']
 result['sections']['celebrities']=chosen
 # One rotating podcast video in Express; persist last shown channel to reduce repeats.
 previous_express={}
 if EXPRESS_HISTORY.exists():
  try:previous_express=json.loads(EXPRESS_HISTORY.read_text(encoding='utf-8'))
  except Exception:pass
 last_express=previous_express.get('last_channel','')
 random.SystemRandom().shuffle(express_pool)
 express_pool.sort(key=lambda x:x['channel']==last_express)
 if express_pool:
  selected_express=express_pool[0]
  result['sections'].setdefault('express',[]).append(selected_express)
  EXPRESS_HISTORY.write_text(json.dumps({'last_channel':selected_express['channel'],'last_video_id':selected_express['id']},ensure_ascii=False,indent=2),encoding='utf-8')
 result['status']['Podcast rotativo Express']='OK' if express_pool else 'Sin vídeo verificable'
 # Do not advance rotation history when no candidates are available.
 if chosen:
  HISTORY.write_text(json.dumps({'last_by_group':new_by_group,'previous_by_group':last_by_group,'last_channels':[x['channel'] for x in chosen],'last_video_ids':[x['id'] for x in chosen]},ensure_ascii=False,indent=2),encoding='utf-8')
 print('YouTube Celebrities:',len(chosen),'de 3 vídeos verificados; canales:',', '.join(x['channel'] for x in chosen) or '(sin resultados)')
 CACHE.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 return result
if __name__=='__main__':collect(True)
