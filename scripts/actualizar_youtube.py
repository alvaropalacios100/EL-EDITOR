import os,json,re,urllib.request,urllib.parse,datetime,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
key=os.environ.get('YOUTUBE_API_KEY')
if not key: sys.exit('Falta el secreto YOUTUBE_API_KEY')
def api(resource,**params):
    params['key']=key
    try:
        with urllib.request.urlopen('https://www.googleapis.com/youtube/v3/'+resource+'?'+urllib.parse.urlencode(params),timeout=30) as r: return json.load(r).get('items',[])
    except Exception as e:
        raise RuntimeError('Error de YouTube: '+str(getattr(e,'code',type(e).__name__))) from None

def extract(path):
    s=path.read_text(); start=s.index('const VIDEOS=')+len('const VIDEOS='); obj,end=json.JSONDecoder().raw_decode(s[start:]); return s,start,end,obj
p=ROOT/'index.html'; s,start,end,data=extract(p)
now=datetime.datetime.now(datetime.timezone.utc)
entries=[(sec,e) for sec,ls in data['sections'].items() for e in ls]
ids=','.join(e['video']['id'] for _,e in entries)
try:
    originals={x['id']:x for x in api('videos',part='snippet',id=ids)}
    if not originals: raise RuntimeError('No se pudieron verificar los vídeos iniciales')
    channels={x['snippet']['channelId'] for x in originals.values()}
    playlists={x['id']:x['contentDetails']['relatedPlaylists']['uploads'] for x in api('channels',part='contentDetails',id=','.join(sorted(channels)))}
except RuntimeError as e: sys.exit(str(e))
used=set(); updated=0
for sec,e in entries:
    old=e['video']; orig=originals.get(old['id']); slot=e['slot']
    if not orig: continue
    cid=orig['snippet']['channelId']; playlist=playlists.get(cid)
    if not playlist: continue
    try:
        items=api('playlistItems',part='contentDetails',playlistId=playlist,maxResults=30)
        vids=[x['contentDetails']['videoId'] for x in items]
        if not vids: continue
        candidates=api('videos',part='snippet,contentDetails,statistics,status',id=','.join(vids))
        valid=[]
        for v in candidates:
            sn=v['snippet']; duration=v['contentDetails']['duration']; m=re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?',duration)
            if not m or sn['channelId']!=cid or v['id'] in used or sn.get('liveBroadcastContent')!='none' or v['status'].get('privacyStatus')!='public': continue
            h,mi,se=(int(x or 0) for x in m.groups()); seconds=h*3600+mi*60+se
            age=(now-datetime.datetime.fromisoformat(sn['publishedAt'].replace('Z','+00:00'))).days
            if seconds<90 or age<0: continue
            if sec=='entretenimiento' and slot in (4,5) and (age>60 or not re.search(r'tr[aá]iler|trailer|teaser|avance',sn['title'],re.I)): continue
            valid.append((v,age,seconds))
        if not valid: continue
        valid.sort(key=lambda x:x[1]); v,age,seconds=valid[0]; sn=v['snippet']; used.add(v['id'])
        if v['id']==old['id']: continue
        e['video']={**old,'id':v['id'],'title':sn['title'],'original_title':sn['title'],'age_days':age,'duration':f'{seconds//60}:{seconds%60:02d}','views':int(v.get('statistics',{}).get('viewCount',0)),'origin':'YouTube Data API v3','channel':old['channel']}
        data['status'][f'{sec}-{slot}']='OK (YouTube Data API v3)'; updated+=1
    except RuntimeError as err: print(f'{sec}-{slot}: {err}; se conserva el vídeo anterior')
if updated:
    data['generated_at']=now.isoformat()
    encoded=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
    for name in ('index.html','PORTADA_DEMO.html'):
        path=ROOT/name; src,a,b,_=extract(path); path.write_text(src[:a]+encoded+src[a+b:])
print(f'Vídeos actualizados: {updated}; los demás se conservan.')
