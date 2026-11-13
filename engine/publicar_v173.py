import json,sys,shutil,datetime,re
from pwa_v190 import integrate, publish_assets
from pathlib import Path
ROOT=Path(__file__).resolve().parent
repo=Path(sys.argv[1]).resolve(); dest=Path(sys.argv[2]).resolve()
old=(repo/'index.html').read_text(encoding='utf-8'); new=(ROOT/'PORTADA_DEMO.html').read_text(encoding='utf-8')
def extract(s,name):
    m=re.search(r'\bconst '+name+r'\s*=\s*',s); a=m.end(); obj,end=json.JSONDecoder().raw_decode(s[a:]); return a,a+end,obj
names=['ARTICLES','THR_ARTICLES','PAIS_NEWS','ELDIARIO_NEWS','FORMULA_NEWS','VERTELE_NEWS','SENSACINE_NEWS','INTERNATIONAL','XATAKA_NEWS','PODCASTS','VIDEOS','NATURE_NEWS','ANDROID_NEWS']
articles=extract(new,'ARTICLES')[2]
now=datetime.datetime.now(datetime.timezone.utc)
def recent(a):
    try:return 0 <= (now-datetime.datetime.fromisoformat(a['date'].replace('Z','+00:00'))).total_seconds() < 3*86400
    except Exception:return False
if '--offline-test' not in sys.argv and not any(recent(a) for a in articles):raise SystemExit('No se obtuvieron noticias recientes; se conserva la web publicada.')
for name in names:
    a,b,previous=extract(old,name); value=extract(new,name)[2]
    if not value: value=previous
    if name=='VIDEOS' and not value.get('sections'):value=previous
    old=old[:a]+json.dumps(value,ensure_ascii=False).replace('<','\\u003c')+old[b:]

# v1.8.3: update presentation functions in the existing public shell.
for name in ('renderVideos','renderInternational','internationalMissingCard','renderSection'):
    pattern=r'(?m)^function '+name+r'\([^\n]*?\).*?(?=^function |^renderVideos\(\);|\Z)'
    # function boundaries use the next top-level declaration; renderSection is one line.
    if name in ('internationalMissingCard','renderSection'): pattern=r'(?m)^function '+name+r'\([^\n]*$'
    match=re.search(pattern,new,re.S); previous=re.search(pattern,old,re.S)
    if not match or not previous: raise RuntimeError('No se pudo actualizar '+name)
    old=old[:previous.start()]+match.group()+old[previous.end():]
old=old.replace('return [...list,...others];','return [...list,...others].filter(a=>!a.internationalEmpty);')
old=old.replace('</head>', '<style>[hidden]{display:none!important}.video-grid,.gabinete-scroll .video-grid{grid-template-columns:repeat(var(--visible-cols,3),minmax(0,1fr))}.international-grid{grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr))}@media(max-width:800px){.video-grid,.gabinete-scroll .video-grid{grid-template-columns:repeat(min(2,var(--visible-cols,3)),minmax(0,1fr))}}@media(max-width:550px){.video-grid,.gabinete-scroll .video-grid{grid-template-columns:1fr!important}}</style>'+ '</head>',1)
# Do not expose internal per-slot diagnostics in public JSON.
a,b,value=extract(old,'VIDEOS'); value.pop('status',None); old=old[:a]+json.dumps(value,ensure_ascii=False).replace('<','\\u003c')+old[b:]

dest.mkdir(parents=True,exist_ok=True)
for p in repo.iterdir():
    if p.is_file() and (p.suffix in ('.html','.png','.webmanifest') or p.name=='.nojekyll'):shutil.copy2(p,dest/p.name)
if (repo/'assets').exists():shutil.copytree(repo/'assets',dest/'assets',dirs_exist_ok=True)
old=integrate(old)
publish_assets(dest)
for name in ('index.html','PORTADA_DEMO.html'):(dest/name).write_text(old,encoding='utf-8')
print('Publicación preparada:',len(articles),'noticias; recientes:',sum(recent(a) for a in articles))
