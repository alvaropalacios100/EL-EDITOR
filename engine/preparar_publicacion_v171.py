"""Generate the static public snapshot and a separate GitHub Pages upload folder.
Never copy Python, RSS config, unpublished TXT, or debugging data.
"""
from pathlib import Path
import shutil
from exportar_web_v164 import main as export_public

ROOT=Path(__file__).resolve().parent
PUBLIC=ROOT/'WEB_PUBLICA'
REPO=ROOT/'PUBLICAR_GITHUB'
WORKFLOW='''name: Publicar EL EDITOR
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: false
jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Obtener el sitio
        uses: actions/checkout@v4
      - name: Configurar GitHub Pages
        uses: actions/configure-pages@v5
      - name: Subir archivos publicos
        uses: actions/upload-pages-artifact@v4
        with:
          path: .
      - name: Publicar en GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
'''
NOTE='''EL EDITOR 1.7.2 — DIRECTORIO SOLO PÚBLICO

Sube el CONTENIDO de esta carpeta a la raíz de un repositorio público de GitHub.
En Settings > Pages selecciona GitHub Actions.
Esta versión publica una FOTO ESTÁTICA de la edición; las noticias y las
columnas NO se actualizan automáticamente en el alojamiento hasta construir
una edición nueva y volver a subir los archivos.

NO subas a GitHub el ZIP local completo: contiene posibles borradores,
claves futuras, configuración y datos que no son públicos.

El mecanismo de despliegue está en .github/workflows/publicar.yml.
Las publicaciones futuras no han sido exportadas.
Antes de abrir al público, revisa los derechos sobre fotos y textos de medios.
'''


def main():
    export_public()
    if REPO.exists():shutil.rmtree(REPO)
    REPO.mkdir()
    for file in PUBLIC.iterdir():
        if not file.is_file():continue
        shutil.copy2(file,REPO/file.name)
    wf=REPO/'.github'/'workflows'/'publicar.yml'
    wf.parent.mkdir(parents=True)
    wf.write_text(WORKFLOW,encoding='utf-8')
    (REPO/'LEEME_PUBLICACION.txt').write_text(NOTE,encoding='utf-8')
    allowed={'.html','.png','.webmanifest','.txt'}
    for file in REPO.rglob('*'):
        if file.is_file() and file.suffix.lower() not in allowed and file.name not in ('.nojekyll','publicar.yml'):
            raise ValueError('Archivo inesperado en exportación: '+str(file))
    if not (REPO/'index.html').exists():raise ValueError('Falta index.html')
    print('Directorio listo para repositorio público:',REPO)

if __name__=='__main__':main()
