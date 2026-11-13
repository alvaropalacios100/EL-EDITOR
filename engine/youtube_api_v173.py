import os,json,re,urllib.request,urllib.parse,threading,time
from pathlib import Path
from functools import lru_cache
ROOT=Path(__file__).resolve().parent
FILE=ROOT/'reserva_youtube_v173.json'
try: reserve=json.loads(FILE.read_text())
except Exception: reserve={}
lock=threading.RLock()
MAP=ROOT/'canales_api_v173.json'
try: channel_ids=json.loads(MAP.read_text())
except Exception: channel_ids={}
searches=0

def api(resource,**params):
    key=os.environ.get('YOUTUBE_API_KEY')
    if not key: raise RuntimeError('Falta YOUTUBE_API_KEY')
    params['key']=key
    try:
        with urllib.request.urlopen('https://www.googleapis.com/youtube/v3/'+resource+'?'+urllib.parse.urlencode(params),timeout=25) as r: return json.load(r)
    except Exception as e: raise RuntimeError('YouTube HTTP '+str(getattr(e,'code',type(e).__name__))) from None
@lru_cache(maxsize=256)
def channel_pool(name,aliases):
    # Search channels only, then verify the actual uploader before using uploads.
    global searches
    cid=channel_ids.get(name)
    handles={'La Base':'@La_Base_','MundoSamsung205':'@MundoSamsung205','topesdegama':'@topesdegama','TUTECNOMUNDO':'@tutecnomundo','ProAndroid':'@ProAndroid'}
    if name in handles:
        from videos_v169 import matches_channel
        items=api('channels',part='id,snippet',forHandle=handles[name]).get('items',[])
        if not items or not matches_channel(items[0].get('snippet',{}).get('title',''),{'match':aliases}):
            raise RuntimeError('No se pudo verificar '+handles[name])
        cid=items[0]['id']
        channel_ids[name]=cid
        MAP.write_text(json.dumps(channel_ids,ensure_ascii=False))
        # Do not mix previously misidentified uploads with verified channels.
        reserve[name]=[v for v in reserve.get(name,[]) if v.get('channel_id')==cid]
    if isinstance(cid,dict):
        if time.time()-cid.get("failed",0)<7*86400:return []
        cid=None
    if not cid:
        if searches>=35: return []
        searches+=1
        items=api('search',part='snippet',type='channel',q=name,maxResults=10).get('items',[])
        from videos_v169 import matches_channel,normalized
        valid=[x for x in items if matches_channel(x['snippet']['title'],{'match':aliases})]
        valid.sort(key=lambda x:normalized(x['snippet']['title'])!=normalized(name))
        if not valid:
            channel_ids[name]={"failed":time.time()}; MAP.write_text(json.dumps(channel_ids,ensure_ascii=False)); return []
        cid=valid[0]['id']['channelId']; channel_ids[name]=cid
        MAP.write_text(json.dumps(channel_ids,ensure_ascii=False))
    ch=api('channels',part='contentDetails',id=cid).get('items',[])
    if not ch:return []
    playlist=ch[0]['contentDetails']['relatedPlaylists']['uploads']; ids=[]; token=None
    for _ in range(2):
        args=dict(part='contentDetails',playlistId=playlist,maxResults=50)
        if token:args['pageToken']=token
        page=api('playlistItems',**args); ids.extend(x['contentDetails']['videoId'] for x in page.get('items',[])); token=page.get('nextPageToken')
        if not token:break
    result=[]
    for i in range(0,len(ids),50):
        result.extend(api('videos',part='snippet,contentDetails,statistics,status',id=','.join(ids[i:i+50])).get('items',[]))
    return [v for v in result if v['snippet']['channelId']==cid]
def candidates(cfg, matches, eligible, priority, age):
    name=cfg['channel']; stats=dict(busquedas=0,resultados=0,aceptados=0,autor_ajeno=0,tema_distinto=0,fecha_desconocida=0,antiguedad_excedida=0,errores=[],rss='API oficial')
    # Serialize cached discovery to avoid duplicate quota-heavy searches.
    with lock:
        try:
            raw=channel_pool(name,tuple(cfg['match'])); stats['busquedas']=1
            fresh=[]
            for v in raw:
                sn=v.get('snippet') or {}; details=v.get('contentDetails') or {}; status=v.get('status') or {}
                duration=details.get('duration')
                if not isinstance(duration,str) or not all(sn.get(k) for k in ('title','publishedAt')) or not v.get('id'):continue
                m=re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?',duration)
                if not m or sn.get('liveBroadcastContent')!='none' or status.get('privacyStatus')!='public' or not status.get('embeddable',True):continue
                h,mi,se=(int(x or 0) for x in m.groups()); seconds=h*3600+mi*60+se
                if not seconds:continue
                fresh.append(dict(id=v['id'],title=sn['title'],original_title=sn['title'],published_at=sn['publishedAt'],duration=f'{seconds//60}:{seconds%60:02d}',views=int(v.get('statistics',{}).get('viewCount',0)),channel=name,channel_id=sn.get('channelId'),origin='YouTube Data API v3',rank=len(fresh),translate_title=cfg.get('translate_title',False)))
            if fresh:
                merged={v['id']:v for v in fresh}; merged.update({v['id']:v for v in reserve.get(name,[]) if v['id'] not in merged}); reserve[name]=list(merged.values())[:200]
        except (RuntimeError, KeyError, TypeError, ValueError) as e:stats['errores'].append(type(e).__name__+': '+str(e))
        pool=[dict(v) for v in reserve.get(name,[])]; FILE.write_text(json.dumps(reserve,ensure_ascii=False))
    stats['channel_id']=channel_ids.get(name) if isinstance(channel_ids.get(name),str) else ''; stats['resultados']=len(pool); accepted=[]
    for v in pool:
        v['age_days']=age(v['published_at']); why=eligible(v,cfg)
        if not why:accepted.append(v)
        else:
            k={'tema distinto':'tema_distinto','fecha desconocida':'fecha_desconocida','antigüedad excedida':'antiguedad_excedida'}.get(why)
            if k:stats[k]+=1
    accepted.sort(key=lambda v:(priority(v),v['age_days'] if v['age_days'] is not None else 999999,v['rank']))
    stats['aceptados']=len(accepted); return accepted[:100],stats
