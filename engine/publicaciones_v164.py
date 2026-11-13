# Publica piezas originales programadas en hora peninsular. No exporta textos futuros.
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import html,re,json
ROOT=Path(__file__).resolve().parent
try:
    TZ=ZoneInfo('Europe/Madrid')
except ZoneInfoNotFoundError:
    # Python en Windows puede carecer de la base IANA. Se usa la zona del PC (configurarlo en Madrid).
    TZ=datetime.now().astimezone().tzinfo

def esc(t): return html.escape(str(t),quote=True)
def parse(path):
    raw=path.read_text(encoding='utf-8-sig')
    lines=raw.splitlines();headers={};start=0
    for i,line in enumerate(lines):
        if not line.strip(): start=i+1;break
        if ':' in line:
            key,val=line.split(':',1)
            headers[key.strip().upper()]=val.strip()
        else: raise ValueError(f'{path.name}: cabecera inválida')
    title=headers.get('TÍTULO') or headers.get('TITULO')
    date=headers.get('FECHA_PUBLICACION') or headers.get('FECHA')
    hour=headers.get('HORA_PUBLICACION') or '00:00'
    body='\n'.join(lines[start:]).strip()
    if not title or not date or not body: raise ValueError(f'{path.name}: requiere TÍTULO, FECHA y texto')
    try: when=datetime.fromisoformat(date+'T'+hour).replace(tzinfo=TZ)
    except ValueError as e: raise ValueError(f'{path.name}: fecha/hora inválida: {e}')
    slug=re.sub('[^a-z0-9_-]+','-',path.stem.casefold()).strip('-')
    return {'title':title,'date':date,'time':hour,'body':body,'slug':slug,'file':path.name,'when':when}

def shell(title,contents,back,kind):
    css='''*{box-sizing:border-box}body{margin:0;background:#f5eedc;color:#211f1b;font-family:Georgia,"Times New Roman",serif}.wrap{max-width:880px;margin:auto;padding:0 20px}header{text-align:center;padding:26px 0 20px;border-bottom:3px double #30291f}header a{text-decoration:none;color:inherit}header h1{font-size:clamp(43px,8vw,76px);margin:0;letter-spacing:-.07em}.strap{font:11px Arial;letter-spacing:.25em}nav{padding:15px 0;border-bottom:1px solid #b8ad97;display:flex;justify-content:center;gap:24px}nav a{font:12px Arial;color:#29251f;text-decoration:none}.kicker{font:700 12px Arial;letter-spacing:.16em;text-transform:uppercase;color:#865240;margin-top:44px}.article-title{font-size:clamp(34px,6vw,58px);line-height:1.1;margin:14px 0}.byline{font:13px Arial;color:#65594d;padding:8px 0 20px;border-bottom:1px solid #b8ad97}.prose{max-width:735px;margin:33px auto 55px;font-size:clamp(18px,2vw,23px);line-height:1.75}.prose p{margin:0 0 1.2em}.entry{padding:25px 0;border-bottom:1px solid #b8ad97}.entry h2{font-size:clamp(22px,4vw,32px);margin:10px 0}.entry a{color:inherit;text-decoration:none}.entry .excerpt{font-size:17px;line-height:1.5}.back{font:14px Arial;color:#5a4c3d;display:inline-block;margin-bottom:60px}footer{font:12px Arial;color:#71695e;border-top:3px double #30291f;padding:20px 0 35px}'''
    return '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+' · EL EDITOR</title><style>'+css+'</style></head><body><header class="wrap"><a href="PORTADA_DEMO.html"><h1>EL EDITOR</h1></a><div class="strap">DIARIO DE INFORMATIVOS</div></header><nav class="wrap"><a href="PORTADA_DEMO.html#politica">NOTICIAS</a><a href="EDITORIAL.html">EDITORIAL</a><a href="CINEMATOGRAFO.html">EL CINEMATÓGRAFO</a></nav><main class="wrap">'+contents+'</main><footer class="wrap">EL EDITOR · Por El Editor</footer></body></html>'

def publish_folder(folder,stem,archive,kind,now=None):
    path=ROOT/folder;path.mkdir(exist_ok=True)
    now=now or datetime.now(TZ)
    texts=sorted([p for p in path.glob('*.txt') if p.name.upper()!='INSTRUCCIONES.TXT' and not p.name.startswith('_')])
    published=[];future=[]
    for file in texts:
        entry=parse(file)
        (published if entry['when']<=now else future).append(entry)
    published.sort(key=lambda x:(x['when'],x['slug']),reverse=True)
    # Remove formerly generated pages for withdrawn or rescheduled items.
    # The future .txt remains local, but no corresponding HTML or public index entry is built.
    for old in ROOT.glob(stem+'*.html'): old.unlink()
    for item in published:
        item['url']=stem+item['slug']+'.html'
        paras=''.join('<p>'+esc(p.strip())+'</p>' for p in re.split(r'\n\s*\n',item['body']) if p.strip())
        content='<div class="kicker">'+esc(kind)+'</div><h1 class="article-title">'+esc(item['title'])+'</h1><div class="byline">El Editor · '+esc(item['date'])+'</div><article class="prose">'+paras+'</article><a class="back" href="'+archive+'">← Volver al archivo</a>'
        (ROOT/item['url']).write_text(shell(item['title'],content,archive,kind),encoding='utf-8')
    content='<div class="kicker">'+('Archivo' if folder=='EDITORIALES' else 'Desde la butaca')+'</div><h1 class="article-title">'+('La Editorial del Editor' if folder=='EDITORIALES' else esc(kind))+'</h1><div class="byline">Columnas publicadas · El Editor</div>'
    for item in published:
        content+='<article class="entry"><h2><a href="'+esc(item['url'])+'">'+esc(item['title'])+'</a></h2><div class="byline">El Editor · '+esc(item['date'])+'</div><p class="excerpt">'+esc(' '.join(item['body'].split())[:260])+'…</p></article>'
    if not published:content+='<p>No hay columnas publicadas todavía.</p>'
    (ROOT/archive).write_text(shell(kind,content,archive,kind),encoding='utf-8')
    public=[{k:v for k,v in entry.items() if k not in ('when','file')} for entry in published]
    return public,{'publicadas':len(published),'programadas':len(future),'proximas_fechas':[f['date']+' '+f['time'] for f in sorted(future,key=lambda e:e['when'])]}

def publish(now=None):
    e,es=publish_folder('EDITORIALES','EDITORIAL_','EDITORIAL.html','Editorial del Editor',now)
    c,cs=publish_folder('CINEMATOGRAFO','CINEMATOGRAFO_','CINEMATOGRAFO.html','El Cinematógrafo',now)
    (ROOT/'diagnostico_programacion_v164.json').write_text(json.dumps({'editoriales':es,'cinematografo':cs},ensure_ascii=False,indent=2),encoding='utf-8')
    return e,c
if __name__=='__main__':
    e,c=publish();print('Editoriales publicadas:',len(e),'| Cinematógrafo:',len(c))
