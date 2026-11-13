"""EL EDITOR 1.6.8: selection by verified channel and time, with fallbacks per slot.
Sources: YouTube public search and the channel's official Atom feed when a
verified channel identifier is available. No placeholder or fabricated IDs.
"""
import concurrent.futures
import datetime as dt
import json
import random
import re
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from videos_v07 import fetch, text, simple, parse_views, translate_sims_title, HEADERS

ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/'video_slots_v166.json').read_text(encoding='utf-8'))
HISTORY=ROOT/'historial_videos_v166.json'
CACHE=ROOT/'videos_v166.json'
DETAIL=ROOT/'diagnostico_candidatos_v168.csv'


def normalized(s):
    s=unicodedata.normalize('NFKD',str(s or '').casefold())
    return re.sub(r'[^a-z0-9]+','', ''.join(c for c in s if not unicodedata.combining(c)))


def age_from_text(raw):
    s=str(raw or '').lower().strip()
    if not s:return None
    if any(x in s for x in ('hoy','today','just now','ahora mismo','ayer','yesterday')):return 0 if 'ayer' not in s and 'yesterday' not in s else 1
    match=re.search(r'(\d+)\s*(segundos?|seconds?|minutos?|minutes?|horas?|hours?|dias?|días?|days?|semanas?|weeks?|meses?|months?|anos?|años?|years?)',s)
    if not match:return None
    num=int(match.group(1));unit=normalized(match.group(2))
    if unit.startswith(('segund','second','minut','minute','hora','hour')):return 0
    if unit.startswith(('dia','day')):return num
    if unit.startswith(('semana','week')):return num*7
    if unit.startswith(('mes','month')):return num*30
    if unit.startswith(('ano','year')):return num*365
    return None


def age_from_iso(raw):
    try:
        d=dt.datetime.fromisoformat(str(raw).replace('Z','+00:00'))
        if d.tzinfo is None:d=d.replace(tzinfo=dt.timezone.utc)
        return max(0,int((dt.datetime.now(dt.timezone.utc)-d).total_seconds()/86400))
    except Exception:return None


def channel_id_from_video(v):
    for key in ('ownerText','longBylineText','shortBylineText'):
        for run in v.get(key,{}).get('runs',[]):
            endpoint=run.get('navigationEndpoint',{}).get('browseEndpoint',{})
            cid=endpoint.get('browseId','')
            if re.fullmatch(r'UC[A-Za-z0-9_-]{22}',cid):return cid
    return None


def candidates_from_rss(cid, cfg):
    if not cid:return [],'sin ID de canal en búsqueda'
    url='https://www.youtube.com/feeds/videos.xml?channel_id='+cid
    try:
        req=urllib.request.Request(url,headers=HEADERS)
        with urllib.request.urlopen(req,timeout=9) as response:xml=response.read(600000)
        root=ET.fromstring(xml)
    except Exception as exc:return [],f'RSS {type(exc).__name__}'
    ns={'a':'http://www.w3.org/2005/Atom','yt':'http://www.youtube.com/xml/schemas/2015'}
    result=[]
    for entry in root.findall('a:entry',ns):
        vid=entry.findtext('yt:videoId','',ns)
        title=entry.findtext('a:title','',ns)
        published=entry.findtext('a:published','',ns)
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}',vid):continue
        result.append({'id':vid,'title':title,'original_title':title,'age_days':age_from_iso(published),'duration':'',
                       'views':0,'rank':len(result),'channel':cfg['channel'],'translate_title':cfg.get('translate_title',False),
                       'origin':'feed del canal', 'published_at':published})
    return result,'RSS: '+str(len(result))+' vídeos'


def matches_channel(author,cfg):
    author=normalized(author)
    return bool(author and any(normalized(a) in author for a in cfg.get('match',[]) if normalized(a)))


def eligible(v,cfg):
    title=normalized(v['title'])
    if cfg.get('topic') and not any(normalized(t) in title for t in cfg['topic']):return 'tema distinto'
    if 'shorts' in title:return 'short excluido'
    age=v.get('age_days')
    maxmo=cfg.get('max_months') or 0
    if maxmo and age is None:return 'fecha desconocida'
    if maxmo and age>maxmo*31:return 'antigüedad excedida'
    return ''


def one_variant(cfg):
    # Short channel-first searches give cleaner uploader IDs than long editorial phrases.
    source=cfg.get('channel','')
    queries=[cfg['query'],source.replace('_',' ')+' videos']
    if cfg.get('max_months')==2:queries.append(source.replace('_',' ')+' trailer')
    if cfg.get('topic'):queries.append(source+' '+cfg['topic'][0])
    queries=list(dict.fromkeys(q for q in queries if q.strip()))
    found=[];channel_ids=[];stats={'busquedas':0,'resultados':0,'autor_ajeno':0,'tema_distinto':0,'fecha_desconocida':0,'antiguedad_excedida':0,'errores':[]}
    for query in queries:
        try:
            videos=fetch(query)
            stats['busquedas']+=1;stats['resultados']+=len(videos)
        except Exception as exc:
            stats['errores'].append(f'{type(exc).__name__} en búsqueda');continue
        for rank,v in enumerate(videos):
            vid=v.get('videoId','')
            if not re.fullmatch(r'[A-Za-z0-9_-]{11}',vid):continue
            uploader=text(v.get('ownerText',{})) or text(v.get('longBylineText',{})) or text(v.get('shortBylineText',{}))
            if not matches_channel(uploader,cfg):
                stats['autor_ajeno']+=1;continue
            cid=channel_id_from_video(v)
            if cid and cid not in channel_ids:channel_ids.append(cid)
            title=text(v.get('title',{}))
            pub=text(v.get('publishedTimeText',{}))
            duration=text(v.get('lengthText',{}))
            item={'id':vid,'title':title,'original_title':title,'age_days':age_from_text(pub),
                  'duration':duration,'views':parse_views(v),'rank':rank,'channel':source,
                  'translate_title':cfg.get('translate_title',False),'origin':'búsqueda de YouTube','published_at':pub}
            found.append(item)
    # The official channel feed supplies dates and recent videos that search may omit.
    for cid in channel_ids[:2]:
        rss,rss_status=candidates_from_rss(cid,cfg)
        stats['rss']=rss_status
        found.extend(rss)
    unique={}
    for item in found:
        vid=item['id']
        if vid not in unique or (unique[vid].get('age_days') is None and item.get('age_days') is not None):unique[vid]=item
    accepted=[]
    for v in unique.values():
        why=eligible(v,cfg)
        if why:
            key={'tema distinto':'tema_distinto','fecha desconocida':'fecha_desconocida', 'antigüedad excedida':'antiguedad_excedida'}.get(why)
            if key:stats[key]+=1
        else:accepted.append(v)
    accepted.sort(key=lambda x:(x['age_days'] if x['age_days'] is not None else 999999,x['rank']))
    stats['aceptados']=len(accepted)
    return accepted[:30],stats


def order_candidates(videos, cfg, previous):
    if not videos:return []
    mode=cfg.get('mode','latest')
    ordered=list(videos)
    if mode in ('random','random_latest','last10','last10_old'):
        sample=ordered[:10] if mode!='random' else ordered
        random.shuffle(sample)
        ordered=sample+[x for x in ordered if x not in sample]
    elif mode=='latest_old' and previous and previous.get('recent',False) and len(ordered)>1:
        ordered=ordered[1:]+ordered[:1]
    prior_id=previous.get('id') if previous else None
    if prior_id and mode!='latest':ordered.sort(key=lambda x:x['id']==prior_id)
    return ordered


def cached_allowed(cached,cfg,elapsed):
    if not cached:return False
    age=cached.get('age_days')
    maxmo=cfg.get('max_months',0)
    if maxmo and (not isinstance(age,(int,float)) or age+elapsed>maxmo*31):return False
    return bool(re.fullmatch(r'[A-Za-z0-9_-]{11}',cached.get('id','')))


def collect(online=False):
    if not online:
        try:return json.loads(CACHE.read_text(encoding='utf-8'))
        except Exception:return {'sections':{},'status':{},'generated_at':None}
    try:hist=json.loads(HISTORY.read_text(encoding='utf-8'))
    except Exception:hist={}
    try:old=json.loads(CACHE.read_text(encoding='utf-8'))
    except Exception:old={'sections':{}}
    old_by_slot={(sec,x['slot']):x['video'] for sec,entries in old.get('sections',{}).items() for x in entries if x.get('video')}
    try:elapsed=max(0,(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(old.get('generated_at',''))).total_seconds()/86400)
    except Exception:elapsed=99999
    jobs=[(sec,i,entry,j,cfg) for sec,slots in CFG.items() for i,entry in enumerate(slots) for j,cfg in enumerate(entry['candidates'])]
    # Each variant is independent; one unavailable channel cannot block the others.
    print('YouTube: consultando canales y fechas de 24 huecos...',flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        outputs=list(pool.map(lambda x:one_variant(x[4]),jobs))
    pool_by={(s,i,j):(found,diag) for (s,i,e,j,cfg),(found,diag) in zip(jobs,outputs)}
    byslot={(s,i):[] for s,slots in CFG.items() for i in range(len(slots))}
    for s,i,e,j,cfg in jobs:
        found,diag=pool_by[s,i,j]
        prior=hist.get(f'{s}-{i}',{})
        ordered=order_candidates(found,cfg,prior)
        for item in ordered:byslot[s,i].append((j,item,False))
        # Only use a formerly verified candidate from the very same source.
        previous=old_by_slot.get((s,i))
        if previous and previous.get('channel')==cfg['channel'] and cached_allowed(previous,cfg,elapsed):
            stale=dict(previous)
            if isinstance(stale.get('age_days'),(int,float)):stale['age_days']+=int(elapsed)
            byslot[s,i].append((j,stale,True))
    result={'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'sections':{},'status':{}}
    selections={};used=set()
    # Gabinete alternates between two fully coordinated options, never duplicates Alán.
    desired=(hist.get('gabinete_pair',-1)+1)%2
    patterns=[[(0,0),(1,1)],[(0,1),(1,0)]]
    patterns=patterns[desired:]+patterns[:desired]
    pair_choice=None
    for pattern in patterns:
        picks=[];ids=set();valid=True
        for i,j in pattern:
            alternatives=[x for x in byslot['gabinete',i] if x[0]==j and x[1]['id'] not in ids]
            if not alternatives:valid=False;break
            pick=alternatives[0];picks.append((i,pick));ids.add(pick[1]['id'])
        if valid:
            for i,p in picks:selections['gabinete',i]=p
            used.update(ids);pair_choice=pattern;break
    if pair_choice is not None:hist['gabinete_pair']=0 if pair_choice==patterns[0] and desired==0 else (0 if pair_choice==[ (0,0),(1,1)] else 1)
    # If the pair cannot be completed, still display nonduplicate valid videos.
    if pair_choice is None:
        for i in (0,1):
            candidates=byslot['gabinete',i]
            for item in candidates:
                if item[1]['id'] not in used and not (i==1 and item[1]['channel']=='Alán Barroso' and selections.get(('gabinete',0),(None,{}))[1].get('channel')=='Alán Barroso'):
                    selections['gabinete',i]=item;used.add(item[1]['id']);break
    for sec,slots in CFG.items():
        for i,entry in enumerate(slots):
            key=(sec,i)
            if key in selections:continue
            for item in byslot[key]:
                if item[1]['id'] not in used:
                    selections[key]=item;used.add(item[1]['id']);break
    translations_path=ROOT/'traducciones_v166.json'
    try:translations=json.loads(translations_path.read_text(encoding='utf-8'))
    except Exception:translations={}
    for sec,slots in CFG.items():
        for i,entry in enumerate(slots):
            k=f'{sec}-{i}'
            if (sec,i) not in selections:
                issues=[]
                for j,cfg in enumerate(entry['candidates']):
                    stats=pool_by[sec,i,j][1]
                    issues.append(f"{cfg['channel']}: {stats.get('aceptados',0)} válidos; {stats.get('fecha_desconocida',0)} sin fecha; {stats.get('antiguedad_excedida',0)} antiguos; {stats.get('autor_ajeno',0)} canal ajeno"+(' / error de red' if stats['errores'] else ''))
                result['status'][k]=' | '.join(issues) or 'Sin resultados';continue
            idx,v,from_cache=selections[sec,i]
            v=dict(v);v['slot_label']=entry.get('label','')
            if v.get('translate_title'):v['title']=translate_sims_title(v.get('original_title') or v['title'],translations)
            result['sections'].setdefault(sec,[]).append({'slot':i,'video':v})
            result['status'][k]='OK'+(' (reserva previamente verificada)' if from_cache else ' ('+v.get('origin','búsqueda')+')')
            previous=hist.get(k,{})
            hist[k]={'index':idx,'id':v['id'],'recent':not previous.get('recent',False)}
    import csv
    with DETAIL.open('w',encoding='utf-8-sig',newline='') as fd:
        w=csv.writer(fd);w.writerow(['seccion','hueco','canal','busquedas','resultados','aceptados','autor_ajeno','tema_distinto','fecha_desconocida','antiguedad_excedida','errores','rss'])
        for sec,i,entry,j,cfg in jobs:
            z=pool_by[sec,i,j][1]
            w.writerow([sec,i+1,cfg['channel'],z.get('busquedas',0),z.get('resultados',0),z.get('aceptados',0),z.get('autor_ajeno',0),z.get('tema_distinto',0),z.get('fecha_desconocida',0),z.get('antiguedad_excedida',0),'; '.join(z['errores']),z.get('rss','')])
    CACHE.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    HISTORY.write_text(json.dumps(hist,ensure_ascii=False,indent=2),encoding='utf-8')
    if translations:translations_path.write_text(json.dumps(translations,ensure_ascii=False,indent=2),encoding='utf-8')
    print('YouTube:',sum(map(len,result['sections'].values())),'de 24 huecos.',flush=True)
    return result
