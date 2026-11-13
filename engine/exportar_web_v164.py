"""Exporta solo páginas publicadas y recursos estáticos; excluye borradores y código."""
from pathlib import Path
import shutil, json
from publicaciones_v164 import publish
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'WEB_PUBLICA'
def main():
    # Revalidate scheduled publication dates before exporting; prevent future drafts leaking.
    published_editorials,published_critiques=publish()
    OUT.mkdir(exist_ok=True)
    for child in OUT.iterdir():
        if child.is_dir():shutil.rmtree(child)
        else:child.unlink()
    files=[ROOT/'PORTADA_DEMO.html',ROOT/'EDITORIAL.html',ROOT/'CINEMATOGRAFO.html']
    files += [ROOT/e['url'] for e in published_editorials+published_critiques]
    for name in ['icon-16.png','icon-32.png','icon-180.png','icon-192.png','icon-512.png','icon-48.png']:
        if (ROOT/name).exists():files.append(ROOT/name)
    for file in files:
        if file.is_file():shutil.copy2(file,OUT/('index.html' if file.name=='PORTADA_DEMO.html' else file.name))
    # links in archives point to PORTADA_DEMO.html, so keep alias alongside index.html.
    shutil.copy2(ROOT/'PORTADA_DEMO.html',OUT/'PORTADA_DEMO.html')
    (OUT/'.nojekyll').write_text('',encoding='utf-8')
    (OUT/'manifest.webmanifest').write_text(json.dumps({'name':'EL EDITOR','short_name':'EL EDITOR','start_url':'./index.html','display':'standalone','background_color':'#f5eedc','theme_color':'#f5eedc','icons':[{'src':'icon-192.png','sizes':'192x192','type':'image/png'},{'src':'icon-512.png','sizes':'512x512','type':'image/png'}]},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Exportacion publica:',OUT, '|',len(list(OUT.iterdir())),'archivos')
    print('ATENCION: el HTML generado puede contener noticias cacheadas; ejecuta INICIAR_PRUEBA.bat para datos recientes.')
if __name__=='__main__':main()
