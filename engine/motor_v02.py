"""EL EDITOR v0.2 - prueba RSS y reclasificación local, Python 3.10+, stdlib."""
import argparse,csv,datetime as dt,hashlib,html,json,re,unicodedata,urllib.request,urllib.parse,xml.etree.ElementTree as ET
from pathlib import Path

BASE=Path(__file__).resolve().parent
SOURCES=[('VidaExtra','Videojuegos','https://www.vidaextra.com/index.xml'),('Xataka','Entretenimiento','https://www.xataka.com/index.xml'),('Espinof','Entretenimiento','https://www.espinof.com/index.xml'),('Directo al Paladar','Varios','https://www.directoalpaladar.com/index.xml'),('elDiario.es','Política','https://www.eldiario.es/rss/'),('Vandal','Videojuegos','https://vandal.elespanol.com/xml.cgi'),('La Razón','Política','https://www.larazon.es/?outputType=xml'),('HuffPost','Entretenimiento','https://www.huffingtonpost.es/feeds/index.xml')]
# Fuentes nuevas v0.6. Los sitios sin RSS directo confirmado usan RSS de búsqueda de Google News,
# atribuyendo cada artículo a su medio real cuando se pueda identificar.
from urllib.parse import quote
V06_SOURCES = [('Europa Press', 'Política', 'https://www.europapress.es/rss/rss.aspx?ch=66', 'rss'), ('Nuevo Sureste', 'Política', 'https://nuevosureste.es/', 'google'), ('RTVE Noticias', 'Política', 'https://www.rtve.es/rss/', 'google'), ('ESCplus', 'Entretenimiento', 'https://www.escplus.es/', 'google'), ('Vertele', 'Entretenimiento', 'https://www.eldiario.es/vertele/rss/', 'rss'), ('FórmulaTV', 'Entretenimiento', 'https://www.formulatv.com/xml/formulatv.xml', 'rss'), ('Europa Press Cultura', 'Celebrities', 'https://www.europapress.es/cultura/', 'google'), ('LOS40', 'Celebrities', 'https://los40.com/', 'google'), ('Billboard', 'Celebrities', 'https://www.billboard.com/', 'google'), ('SimsVIP', 'Videojuegos', 'https://simsvip.com/', 'google'), ('Nintendúo', 'Videojuegos', 'https://nintenduo.com/', 'google'), ('VidaExtra', 'Videojuegos', 'https://www.vidaextra.com/index.xml', 'rss'), ('Teatro Madrid', 'Express', 'https://teatromadrid.com/', 'google'), ('Directo al Paladar', 'Express', 'https://www.directoalpaladar.com/index.xml', 'rss'), ('Madrid Destino', 'Express', 'https://www.madrid-destino.com/', 'google')]
for name, section, url, mode in V06_SOURCES:
    if any(oldname == name for oldname, _, _ in SOURCES):
        continue
    if mode == 'google':
        from urllib.parse import urlsplit
        domain=urlsplit(url).netloc.removeprefix('www.')
        query=quote('site:'+domain)
        feed='https://news.google.com/rss/search?q='+query+'&hl=es&gl=ES&ceid=ES:es'
    else:
        feed=url
    SOURCES.append((name, section, feed))

# v1.5.8: incorporate editorial sources configured in fuentes_v06.json (not just in a disconnected inventory).
try:
 _configured=json.loads((BASE/'fuentes_v06.json').read_text(encoding='utf-8'))
except (OSError,ValueError):_configured=[]
for _src in _configured:
 _name=_src.get('nombre','').strip();_url=_src.get('url','').strip();_section=_src.get('seccion','Política')
 if not _name or not _url or any(existing[0]==_name for existing in SOURCES):continue
 if _name=='El País':_feed='https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada'
 elif _src.get('modo')=='google':
  from urllib.parse import urlsplit as _urlsplit
  _domain=_urlsplit(_url).netloc.removeprefix('www.')
  _feed='https://news.google.com/rss/search?q='+quote('site:'+_domain)+'&hl=es&gl=ES&ceid=ES:es'
 else:_feed=_url
 SOURCES.append((_name,_section,_feed))

# Fuentes complementarias para EXPRESS NEWS: búsquedas dirigidas a noticias publicadas,
# no se crea contenido ficticio para completar las tarjetas.
EXPRESS_QUERIES=[
 ('Teatro y musicales Madrid', 'site:esmadrid.com/agenda-teatro-madrid teatro musical estreno Madrid'),
 ('Cartelera Madrid', 'site:teatromadrid.com estrenos musicales Madrid'),
 ('Cultura Madrid', 'site:madrid.es cultura teatro exposiciones programación'),
 ('Recetas vegetarianas', 'site:directoalpaladar.com vegetariana receta'),
 ('El Comidista', 'site:elpais.com/gastronomia/el-comidista receta vegetales'),
 ('Madrid Destino cultura', 'site:madrid-destino.com teatro exposiciones')
]
for name,query in EXPRESS_QUERIES:
    SOURCES.append((name,'Express','https://news.google.com/rss/search?q='+quote(query)+'&hl=es&gl=ES&ceid=ES:es'))

# v1.3: comprobación externa de Nintenderos /feed/ y FórmulaTV /xml/formulatv.xml.
# Fuentes especializadas adicionales: las búsquedas Google News son alternativas,
# NO equivalen a un RSS oficial y su éxito se reflejará en informe_fuentes_v04.csv.
SOURCES.append(('Nintenderos','Videojuegos','https://www.nintenderos.com/feed/'))
SOURCES.append(('SensaCine','Entretenimiento','https://www.sensacine.com/rss/noticias.xml'))
# v1.5.9: direct RSS with actual publisher URLs; supplement Google News rather than replacing it.
SOURCES.append(('3DJuegos','Videojuegos','https://www.3djuegos.com/feedburner.xml'))
# Specific Spain feed avoids the Google News proxy and improves image matching.
SOURCES=[(n,sec,('https://rss.elconfidencial.com/espana/' if n=='El Confidencial' else u)) for n,sec,u in SOURCES]
SOURCES.append(('GTA actualidad','Videojuegos','https://news.google.com/rss/search?q='+quote('GTA 6 OR GTA VI OR Grand Theft Auto site:3djuegos.com OR site:vidaextra.com OR site:vandal.elespanol.com when:14d')+'&hl=es&gl=ES&ceid=ES:es'))
SOURCES.append(('Decoesfera','Express','https://www.decoesfera.com/index.xml'))
for name,query in [
 ('Verdecora blog','site:verdecora.es/blog plantas jardinería huerto'),
 ('Madrid Actual Teatro','site:madridactual.es/que-hacer/teatro/ estreno teatro musical'),
 ('Teatro y musicales esMadrid','site:esmadrid.com/agenda-musicales OR site:esmadrid.com/agenda-teatro-madrid'),
 ('IKEA hogar','site:ikea.com/es/es/newsroom/ hogar mobiliario'),
 ('Decoración hogar','site:decoesfera.com tendencias decoración muebles'),
 ('Agenda cultural Madrid','site:madrid.es agenda teatro museos exposiciones')
]:
 SOURCES.append((name,'Express','https://news.google.com/rss/search?q='+quote(query)+'&hl=es&gl=ES&ceid=ES:es'))

# Configuración editable: cada tema se aplica solo a sus secciones; nunca a toda la web.
TOPICS={
'Política':{'Gabriel Rufián':['gabriel rufian','rufian'],'Congreso':['congreso de los diputados','congreso','camara baja'],'Vivienda':['vivienda','alquiler','hipoteca'],'El Cañaveral':['el canaveral'],'Villaverde':['villaverde'],'Letizia':['letizia'],'Madrid':['madrid'],'EMT':['emt madrid','empresa municipal de transportes'],'Metro':['metro de madrid'],'Zohran Mamdani':['zohran mamdani','mamdani'],'Pablo Iglesias':['pablo iglesias'],'Irene Montero':['irene montero'],'Pedro Sánchez':['pedro sanchez'],'Yolanda Díaz':['yolanda diaz'],'Ada Colau':['ada colau'],'Mónica García':['monica garcia'],'Manuela Bergerot':['manuela bergerot','bergerot'],'Eduardo Rubiño':['eduardo rubino']},
'Entretenimiento':{'Eurovisión':['eurovision','eurovision song contest'],'Benidorm Fest':['benidorm fest','benidormfest'],'Drag Race':['drag race'],'Los Javis':['los javis','javier ambrossi','javier calvo'],'Spider-Man':['spider-man','spiderman','spider man'],'Vengadores':['vengadores','avengers'],'Timothée Chalamet':['timothee chalamet','chalamet'],'Lady Gaga':['lady gaga'],'Madonna':['madonna'],'Netflix':['netflix'],'HBO':['hbo','max'],'Disney':['disney'],'Star Wars':['star wars'],'Harry Potter':['harry potter'],'La 1':['la 1','la uno','tve 1'],'Audiencias':['audiencias de television','audiencia televisiva'],'Televisión española':['television espanola','rtve'],'Familia Real':['familia real'],'Rosalía':['rosalia'],'Beyoncé':['beyonce'],'Taylor Swift':['taylor swift'],'Operación Triunfo':['operacion triunfo'],'Supremme Deluxe':['supremme deluxe'],'Los Simpson':['los simpson'],'Brava Madrid':['brava madrid'],'Chueca':['chueca'],'LGTB':['lgtb','lgbt']},
'Videojuegos':{'Los Sims':['los sims','the sims','sims 4','sims 5'],'Nintendo':['nintendo','nintendo switch','zelda','mario kart','super mario'],'Pokémon':['pokemon','pokemon go'],'GTA':['gta','gta vi','grand theft auto'],'Cities Skylines':['cities skylines'],'Animal Crossing':['animal crossing'],'Fortnite':['fortnite'],'inZOI':['inzoi'],'Paralives':['paralives'],'City Builders':['city builder','city builders']},
'Varios':{'Recetas vegetarianas':['receta vegetariana','recetas vegetarianas','cocina vegetariana','plato vegetariano'],'Verdecora':['verdecora'],'El Comidista':['el comidista'],'Ikea':['ikea'],'Carrefour':['carrefour'],'Teatros de Madrid':['teatros de madrid','teatro en madrid'],'Musicales de Madrid':['musicales de madrid','musical en madrid']}}
EXCLUDED_EL_MUNDO={'Pablo Iglesias','Irene Montero','Pedro Sánchez','Yolanda Díaz','Ada Colau','Mónica García','Manuela Bergerot','Eduardo Rubiño'}
PRIORITY=['Eurovisión','Benidorm Fest','Drag Race','Los Sims','Gabriel Rufián','Congreso','Spider-Man','Vengadores','Timothée Chalamet','Lady Gaga']
NS_ATOM='{http://www.w3.org/2005/Atom}'
def normalize(s):
 s=unicodedata.normalize('NFKD',html.unescape(str(s or '')))
 return ''.join(c for c in s if not unicodedata.combining(c)).casefold()
def clean(s):return re.sub(r'\s+',' ',re.sub(r'<[^>]*>',' ',html.unescape(s or ''))).strip()
def contains(text,phrase):
 p=normalize(phrase).strip();t=normalize(text)
 return bool(p and re.search(r'(?<!\w)'+re.escape(p)+r'(?!\w)',t))
def classify(a):
 title=a.get('title',''); summary=a.get('summary',''); section=a.get('section','')
 matches=[]; evidence={}
 for topic,aliases in TOPICS.get(section,{}).items():
  if a.get('source')=='El Mundo' and topic in EXCLUDED_EL_MUNDO:continue
  in_title=[p for p in aliases if contains(title,p)]
  in_summary=[p for p in aliases if contains(summary,p)]
  if in_title or in_summary:
   matches.append(topic);evidence[topic]='titular' if in_title else 'resumen'
 # Sin sumar múltiples sinónimos del mismo tema; el titular pesa más que el resumen.
 score=sum(10 if evidence[t]=='titular' else 3 for t in matches)
 score+=8*max(0,len(matches)-1) # temas cruzados
 score+=sum(max(0,10-i) for i,t in enumerate(PRIORITY) if t in matches)
 return matches,evidence,score

def child_text(e,names):
 for name in names:
  x=e.find(name)
  if x is not None and x.text:return x.text.strip()
 return ''
def image_from(e,desc):
 # URL candidata, no implica licencia de reproducción.
 for child in e.iter():
  tag=child.tag.split('}')[-1].lower()
  if tag in ('thumbnail','content','enclosure'):
   url=child.attrib.get('url','')
   typ=child.attrib.get('type','')
   if url.startswith('https://') and (tag=='thumbnail' or typ.startswith('image/') or re.search(r'\.(jpg|jpeg|png|webp)(\?|$)',url,re.I)):return url
 m=re.search(r'<img\b[^>]*\bsrc=["\'](https://[^"\']+)',desc or '',re.I)
 return html.unescape(m.group(1)) if m else ''
def parse_feed(data,source,section):
 root=ET.fromstring(data);entries=root.findall('.//item');atom=False
 if not entries:entries=root.findall(f'.//{NS_ATOM}entry');atom=True
 out=[]
 for e in entries:
  title=clean(child_text(e,['title',NS_ATOM+'title']))
  if atom:
   links=e.findall(NS_ATOM+'link');link=next((x.get('href','') for x in links if x.get('rel','alternate')=='alternate'), '') or next((x.get('href','') for x in links),'')
  else:link=child_text(e,['link'])
  if not isinstance(link,str):link=''
  date=child_text(e,['pubDate',NS_ATOM+'published',NS_ATOM+'updated','{http://purl.org/dc/elements/1.1/}date'])
  raw=child_text(e,['description',NS_ATOM+'summary','{http://purl.org/rss/1.0/modules/content/}encoded'])
  if not title or not link.startswith(('http://','https://')):continue
  out.append({'title':title,'url':link,'date':date,'summary':clean(raw)[:600],'image_candidate':image_from(e,raw),'source':source,'section':section})
 return out

def date_iso(s):
 from email.utils import parsedate_to_datetime
 try:return parsedate_to_datetime(s).astimezone(dt.timezone.utc).isoformat()
 except (ValueError,TypeError,IndexError):
  try:return dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(dt.timezone.utc).isoformat()
  except (ValueError,TypeError,AttributeError):return ''
def canonical(url):
 p=urllib.parse.urlsplit(url);path=p.path.rstrip('/') or '/'
 return urllib.parse.urlunsplit((p.scheme.lower(),p.netloc.lower().removeprefix('www.'),path,'',''))
def process(articles):
 seen=set();result=[];dupes=0
 for a in articles:
  if not isinstance(a,dict) or not a.get('url'):continue
  key=canonical(a['url'])
  if key in seen:dupes+=1;continue
  seen.add(key)
  a=dict(a);a['id']=hashlib.sha256(key.encode()).hexdigest()[:20]
  a['published_utc']=date_iso(a.get('date',''))
  a['topics'],a['topic_evidence'],a['score']=classify(a)
  a['image_candidate']=a.get('image_candidate','')
  a['image_approved']=False # no se publica sin verificación de derechos
  result.append(a)
 result.sort(key=lambda a:(bool(a['topics']),a['score'],a['published_utc']),reverse=True)
 return result,dupes

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--archivo',help='Reprocesar un noticias_prueba.json existente sin Internet');args=ap.parse_args()
 report=[];articles=[]
 if args.archivo:
  obj=json.loads(Path(args.archivo).read_text(encoding='utf-8-sig'));articles=obj['articles']
  print('Modo local: reclasificando',len(articles),'noticias')
 else:
  for name,section,url in SOURCES:
   row={'source':name,'section':section,'feed':url,'status':'','entries':0,'matches':0,'detail':''}
   try:
    req=urllib.request.Request(url,headers={'User-Agent':'EL-EDITOR-RSS-Diagnostic/0.2','Accept':'application/rss+xml, application/atom+xml, application/xml, text/xml'})
    with urllib.request.urlopen(req,timeout=18) as r:
     body=r.read(3_000_001)
     if len(body)>3_000_000:raise ValueError('Canal mayor de 3 MB')
    items=parse_feed(body,name,section)
    row['entries']=len(items);row['matches']=sum(bool(classify(x)[0]) for x in items)
    row['status']='OK' if items else 'VACÍO';articles.extend(items)
   except Exception as exc:row['status']='ERROR';row['detail']=f'{type(exc).__name__}: {exc}'[:250]
   report.append(row);print(name,row['status'],row['entries'],row['detail'])
 processed,dupes=process(articles)
 if report:
  with (BASE/'informe_fuentes_v02.csv').open('w',newline='',encoding='utf-8-sig') as f:
   w=csv.DictWriter(f,fieldnames=list(report[0]));w.writeheader();w.writerows(report)
 output={'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'total':len(processed),'matches':sum(bool(a['topics']) for a in processed),'duplicates_removed':dupes,'articles':processed}
 (BASE/'noticias_v02.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
 with (BASE/'seleccion_v02.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['fuente','seccion','fecha_utc','puntuacion','temas','titular','url','imagen_candidata'])
  for a in processed:
   if a['topics']:w.writerow([a.get('source'),a.get('section'),a['published_utc'],a['score'],' | '.join(a['topics']),a['title'],a['url'],a['image_candidate']])
 print('TOTAL',len(processed),'COINCIDENCIAS',output['matches'],'DUPLICADOS',dupes)
 print('Generados noticias_v02.json y seleccion_v02.csv')
if __name__=='__main__':main()
