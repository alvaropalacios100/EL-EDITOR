"""Fuente de noticias audiovisuales en inglés, sin inventar contenido."""
from pathlib import Path
from email.utils import parsedate_to_datetime
from datetime import datetime,timezone
import json,re,hashlib,urllib.request,xml.etree.ElementTree as ET,html
ROOT=Path(__file__).resolve().parent
URL='https://www.hollywoodreporter.com/feed/'
CACHE=ROOT/'espectador_internacional_v164.json'
TRANS=ROOT/'traducciones_espectador_v164.json'
HEAD={'User-Agent':'Mozilla/5.0 (EL EDITOR personal RSS reader)','Accept-Language':'en-US,en;q=.8'}
def request(url,timeout=11):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=HEAD),timeout=timeout) as r:return r.read(2200000)
    except Exception:return b''
def translate(t,cache):
    if t in cache:return cache[t]
    from urllib.parse import urlencode
    raw=request('https://translate.googleapis.com/translate_a/single?'+urlencode({'client':'gtx','sl':'en','tl':'es','dt':'t','q':t}),7)
    try:
        response=json.loads(raw);out=''.join(row[0] for row in response[0] if row and row[0]).strip()
        if out and out!=t:cache[t]=out;return out
    except Exception:pass
    return t

def collect(online=False):
    if not online:
        try:return json.loads(CACHE.read_text(encoding='utf-8'))
        except Exception:return []
    raw=request(URL)
    try:root=ET.fromstring(raw)
    except ET.ParseError:return collect(False)
    except Exception:return collect(False)
    NS={'m':'http://search.yahoo.com/mrss/'}
    try:trans=json.loads(TRANS.read_text(encoding='utf-8'))
    except Exception:trans={}
    output=[];now=datetime.now(timezone.utc)
    for node in root.findall('.//item')[:35]:
        get=lambda name:(node.findtext(name) or '').strip()
        title=html.unescape(re.sub('<[^>]+>','',get('title')))
        link=get('link');date=get('pubDate')
        try:dt=parsedate_to_datetime(date).astimezone(timezone.utc)
        except Exception:continue
        if not 0<=(now-dt).total_seconds()<21*86400:continue
        if not link.startswith('https://www.hollywoodreporter.com/') or not title:continue
        # Distinguish industry coverage from gaming news.
        if re.search(r'\b(video game|videogame|gaming|playstation|xbox)\b',title,re.I):continue
        img=''
        for child in node.findall('m:content',NS)+node.findall('m:thumbnail',NS)+node.findall('enclosure'):
            candidate=child.attrib.get('url','')
            if candidate.startswith('https://') and not img:img=candidate
        display=translate(title,trans)
        output.append({'id':'thr-'+hashlib.sha1(link.encode()).hexdigest()[:15],'source':'The Hollywood Reporter','title':display,'original_title':title,'url':link,'date':dt.isoformat(),'image':img,'primary':'Entretenimiento','score':28,'topics':['Cine y televisión internacional'],'sections':['Entretenimiento'],'translation_ok':display!=title})
    if output:
        # Validate images before slot #5 selects its article; same original-source image strategy as the other stories.
        from imagenes_v159 import enrich
        from miniaturas_v14 import embed
        shortlist=output[:16]
        enrich(shortlist)
        embed(shortlist,max_articles=len(shortlist))
        output.sort(key=lambda a:(bool(a.get('image_data')),bool(a.get('image')),a['date']),reverse=True)
        CACHE.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
        TRANS.write_text(json.dumps(trans,ensure_ascii=False,indent=2),encoding='utf-8')
        return output
    return collect(False)
