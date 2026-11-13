"""Genera el archivo de editoriales y páginas HTML desde los .txt de EDITORIALES."""
from pathlib import Path
import html,re,json,datetime
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'EDITORIALES'
def escape(s):return html.escape(str(s),quote=True)
def parse(path):
 lines=path.read_text(encoding='utf-8-sig').splitlines()
 title='';date='';body=[];in_body=False
 for line in lines:
  if not in_body and line.startswith('TÍTULO:'):title=line.split(':',1)[1].strip();continue
  if not in_body and line.startswith('FECHA:'):date=line.split(':',1)[1].strip();continue
  if not in_body and not line.strip():in_body=True;continue
  in_body=True;body.append(line)
 body='\n'.join(body).strip()
 if not title or not body:raise ValueError(f'{path.name}: falta TÍTULO o contenido')
 if date:
  try:datetime.date.fromisoformat(date)
  except ValueError:raise ValueError(f'{path.name}: FECHA debe ser AAAA-MM-DD')
 else:date='1970-01-01'
 return {'title':title,'date':date,'body':body,'file':path.name,'slug':re.sub(r'[^a-z0-9_-]+','-',path.stem.lower()).strip('-')}
def shell(title,inner):
 css=""":root{--paper:#f5eedc;--ink:#191814;--muted:#655e52;--rule:#afa38e}*{box-sizing:border-box}body{background:var(--paper);color:var(--ink);font-family:Georgia,'Times New Roman',serif;margin:0}.wrap{width:min(900px,calc(100% - 36px));margin:auto}header{text-align:center;border-bottom:3px double var(--ink);padding:25px 0 14px}header a{text-decoration:none;color:inherit}header .brand{font-size:clamp(44px,9vw,82px);font-weight:bold;letter-spacing:-.08em;line-height:1}header .strap{font:11px Arial,sans-serif;letter-spacing:.2em;margin-top:12px}nav{display:flex;justify-content:center;gap:25px;border-bottom:1px solid var(--rule);padding:13px 0;font:12px Arial,sans-serif;text-transform:uppercase}nav a{color:inherit;text-decoration:none}nav a:hover{text-decoration:underline}.kicker{font:700 12px Arial,sans-serif;letter-spacing:.14em;color:#8e4633;text-transform:uppercase;margin:48px 0 10px}h1{font-size:clamp(36px,6vw,64px);line-height:1.06;letter-spacing:-.04em;margin:0 0 18px}h2{font-size:clamp(22px,3vw,33px);margin:0 0 8px;line-height:1.12}.byline{font:13px Arial,sans-serif;color:var(--muted);border-bottom:1px solid var(--rule);padding-bottom:20px}.body{max-width:750px;margin:30px auto 75px;font-size:clamp(19px,2.7vw,24px);line-height:1.75}.body p{margin:0 0 1em}.entry{padding:24px 0;border-bottom:1px solid var(--rule)}.entry a{color:inherit;text-decoration:none}.entry a:hover{text-decoration:underline}.excerpt{font-size:17px;line-height:1.5;margin:8px 0 0}.back{display:inline-block;font:13px Arial,sans-serif;margin:14px 0 30px;color:inherit}footer{border-top:3px double var(--ink);padding:24px 0 40px;font:12px Arial,sans-serif;color:var(--muted)}"""
 return '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(title)+' · EL EDITOR</title><style>'+css+'</style></head><body><header class="wrap"><a href="PORTADA_DEMO.html"><div class="brand">EL EDITOR</div></a><div class="strap">DIARIO DE INFORMATIVOS</div></header><nav class="wrap"><a href="PORTADA_DEMO.html#politica">NOTICIAS</a><a href="EDITORIAL.html">EDITORIAL</a><a href="PORTADA_DEMO.html#videojuegos">GAME</a></nav><main class="wrap">'+inner+'</main><footer class="wrap">EL EDITOR · Editoriales de opinión firmadas por El Editor</footer></body></html>'
def publish():
 SRC.mkdir(exist_ok=True)
 items=sorted((parse(p) for p in SRC.glob('*.txt') if not p.name.startswith('_') and p.name != 'INSTRUCCIONES.txt'),key=lambda x:(x['date'],x['slug']),reverse=True)
 for it in items:
  text=''.join('<p>'+escape(p)+'</p>' for p in it['body'].split('\n') if p.strip())
  content='<div class="kicker">Editorial del Editor</div><h1>'+escape(it['title'])+'</h1><div class="byline">Por El Editor · '+escape(it['date'])+'</div><article class="body">'+text+'</article><a class="back" href="EDITORIAL.html">← Ver todas las editoriales</a>'
  it['url']='EDITORIAL_'+it['slug']+'.html'
  (ROOT/it['url']).write_text(shell(it['title'],content),encoding='utf-8')
 entries=''.join('<article class="entry"><div class="kicker">Editorial del Editor</div><h2><a href="'+escape(it['url'])+'">'+escape(it['title'])+'</a></h2><div class="byline">El Editor · '+escape(it['date'])+'</div><p class="excerpt">'+escape(' '.join(it['body'].splitlines()[:2]))+'</p></article>' for it in items)
 (ROOT/'EDITORIAL.html').write_text(shell('Editoriales','<div class="kicker">Opinión</div><h1>Editorial del Editor</h1><div class="byline">Archivo de columnas · Autor: El Editor</div>'+ (entries or '<p>Todavía no hay editoriales publicadas.</p>')),encoding='utf-8')
 (ROOT/'editoriales_publicadas.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
 return items
if __name__=='__main__':print('Editoriales publicadas:',len(publish()))
