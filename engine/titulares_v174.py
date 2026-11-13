"""Translate known foreign feeds at the final editorial boundary."""
import json, concurrent.futures
from pathlib import Path
from internacional_v158 import SOURCES, translate, headline_language
ROOT=Path(__file__).resolve().parent
CACHE=ROOT/'titulares_v174.json'
LANG={k:v[2] for k,v in SOURCES.items()}
LANG.update({'Variety':'en','Billboard':'en','SimsVIP':'en','The Hollywood Reporter':'en'})
def clean(articles,online):
    try: cache=json.loads(CACHE.read_text())
    except Exception: cache={}
    def one(a):
        lang=LANG.get(a.get('source'))
        if not lang:return a
        if a.get('translation_ok') or a.get('translated'):return a
        original=a.get('original_title') or a.get('title','')
        lang=headline_language(original,lang)
        if lang=='es':return a
        if not online:
            return a if a.get('title')!=original else None
        shown,ok=translate(original,lang,cache)
        if not ok:return None
        return dict(a,title=shown,original_title=original,translation_ok=True,translated=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        result=list(pool.map(one,articles))
    CACHE.write_text(json.dumps(cache,ensure_ascii=False),encoding='utf-8')
    print('Titulares extranjeros: omitidos sin traducción:',sum(x is None for x in result),flush=True)
    return [x for x in result if x is not None]
