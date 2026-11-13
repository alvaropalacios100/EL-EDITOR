import json,re,sys,html,datetime,base64
from pathlib import Path
from zoneinfo import ZoneInfo
from publicaciones_v164 import shell
site=Path(sys.argv[1]); private=Path(sys.argv[2]); now=datetime.datetime.now(ZoneInfo('Europe/Madrid'))
def edition_time(day):
 return datetime.datetime.combine(day, datetime.time(6), tzinfo=datetime.timezone.utc).astimezone(ZoneInfo('Europe/Madrid'))
cutoff=(now.date()-datetime.timedelta(days=now < edition_time(now.date()))).isoformat()
rows=json.loads((private/'articulos.json').read_text()) if (private/'articulos.json').exists() else []
assert isinstance(rows,list)
esc=lambda x:html.escape(str(x),quote=True)
legal='EL EDITOR es un medio digital independiente que reúne información de actualidad de distintos medios y ofrece contenidos propios de opinión y cultura. Las noticias enlazadas pertenecen a sus respectivos medios y autores. Los titulares, imágenes y extractos de terceros se muestran con finalidad informativa y remiten a sus fuentes originales. Las opiniones de Editorial y El Cinematógrafo corresponden a sus autores. © 2026 EL EDITOR.'
index=(site/'index.html').read_text()
for section,constant,archive,prefix,label in [('Editorial','EDITORIALES','EDITORIAL.html','EDITORIAL_','Editorial del Editor'),('Cinematógrafo','CINEMATOGRAFO','CINEMATOGRAFO.html','CINEMATOGRAFO_','El Cinematógrafo')]:
 m=re.search(r'\bconst '+constant+r'\s*=\s*',index); start=m.end(); old,n=json.JSONDecoder().raw_decode(index[start:]); entries=list(old)
 for a in rows:
  if a.get('section')!=section or a.get('status') not in ('scheduled','immediate'):continue
  date=datetime.date.fromisoformat(a['date']).isoformat()
  if date>(now.date().isoformat() if a['status']=='immediate' else cutoff):continue
  slug=a['id']; assert re.fullmatch(r'[a-z0-9-]{1,80}',slug)
  url=prefix+'redaccion-'+slug+'.html'; title=a['title']; body=a['body']; author=a.get('author') or 'El Editor'; sub=a.get('subtitle',''); img=''
  if a.get('image'):
   mime,data=a['image'].split(',',1); ext={'data:image/jpeg;base64':'jpg','data:image/png;base64':'png','data:image/webp;base64':'webp'}[mime]; raw=base64.b64decode(data,validate=True); assert len(raw)<=750000
   fn='redaccion-'+slug+'.'+ext; (site/fn).write_bytes(raw); img=f'<img src="{fn}" alt="" style="max-width:100%;height:auto">'
  paras=''.join('<p>'+esc(p).replace('\n','<br>')+'</p>' for p in re.split(r'\n\s*\n',body) if p.strip())
  content=f'<div class="kicker">{esc(label)}</div><h1 class="article-title">{esc(title)}</h1><p>{esc(sub)}</p><div class="byline">{esc(author)} · {date}</div>{img}<article class="prose">{paras}</article><a class="back" href="{archive}">← Volver al archivo</a>'
  (site/url).write_text(shell(title,content,archive,label))
  entries.append(dict(title=title,body=body,date=date,time=edition_time(datetime.date.fromisoformat(date)).strftime('%H:%M'),slug=slug,url=url,author=author))
 entries.sort(key=lambda a:a['date'],reverse=True)
 index=index[:start]+json.dumps(entries,ensure_ascii=False).replace('<','\\u003c')+index[start+n:]
 content=f'<div class="kicker">Archivo</div><h1 class="article-title">{esc(label)}</h1>'
 for a in entries:content+=f'<article class="entry"><h2><a href="{esc(a["url"])}">{esc(a["title"])}</a></h2><div class="byline">{esc(a.get("author","El Editor"))} · {esc(a["date"])}</div><p class="excerpt">{esc(a["body"][:260])}…</p></article>'
 (site/archive).write_text(shell(label,content,archive,label))
index=re.sub(r"document\.getElementById\('status'\)\.textContent=`[^`]*`", "document.getElementById('status').hidden=true",index)
(site/'index.html').write_text(index)
for p in site.glob('*.html'):
 s=p.read_text(); s=s.replace('PORTADA_DEMO.html','index.html'); s=re.sub(r'<footer\b[^>]*>.*?</footer>',lambda m:'<footer class="wrap footer">'+legal+'</footer>',s,flags=re.S); p.write_text(s)
(site/'PORTADA.html').write_text((site/'index.html').read_text()); (site/'PORTADA_DEMO.html').write_text('<!doctype html><html lang="es"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=index.html"><title>EL EDITOR</title><a href="index.html">EL EDITOR</a></html>')
print('Redacción: edición pública preparada')
