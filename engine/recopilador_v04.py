"""EL EDITOR v0.4: portada de prueba + clasificación contextual sin dependencias."""
import argparse,csv,datetime as dt,html,json,re,unicodedata,urllib.request
from pathlib import Path
import motor_v02 as base
ROOT=Path(__file__).resolve().parent
T=base.TOPICS
# Reglas editoriales específicas. El RSS de origen no determina la sección final.
T['Entretenimiento'].update({'Los Javis':['los javis','javier calvo','javier ambrossi','la bola negra'],'La 1':['la 1','la uno','tve 1'],'Movistar Plus':['movistar plus','movistar+'],'Universo DC':['universo dc','dc comics','clayface'],'Audiencias':['audiencias','cuota de pantalla']})
T['Política'].update({'Metro':['metro de madrid','metro','linea 6','linea 11'],'EMT':['emt','autobuses municipales'],'Vivienda':['vivienda','alquiler','zonas tensionadas','pisos turisticos','mercado inmobiliario']})
T['Videojuegos'].update({'Nintendo':['nintendo','zelda','mario kart','switch'],'Pokémon':['pokemon','pokémon']})
ALL={k:(sec,aliases) for sec,topics in T.items() for k,aliases in topics.items()}
PREF=set(base.PRIORITY)
HOUSING=r'\b(alquiler\w*|inquilin\w*|hipotec\w*|inmobiliari\w*|vivienda\w*|pisos? turistic\w*|zonas? tensionad\w*|desahuci\w*|residencial\w*|mercado de la vivienda|segundas? residencias?)\b'
HOUSING_EVENT=r'\b(incendio|bomberos|herid\w*|fallecid\w*|robo|explosion|explosión|rescate)\b'
PARLIAMENT=r'\b(congreso de los diputados|diputad\w*|hemiciclo|sesion plenaria|pleno del congreso|debate parlamentario|comision parlamentaria|votacion parlamentaria|camara baja|iniciativa legislativa)\b'
CANDIDATE=r'\b(candidatur\w*|listas electorales|encabeza la lista|candidato\w* al congreso)\b'
LOCAL=r'\b(metro|emt|movilidad|transporte publico|linea [0-9]+|estaciones|ayuntamiento|comunidad de madrid|asamblea de madrid|urbanismo|obras|infraestructura|presupuesto|barrios?|vivienda|alquiler|municipal)\b'
SOFT={'Netflix','HBO','Disney','Madrid','Nintendo','Congreso','GTA','Vengadores','La 1'}
SPECIFIC={'Los Javis','Madonna','Lady Gaga','Timothée Chalamet','Gabriel Rufián','Spider-Man','Eurovisión','Benidorm Fest','Drag Race','El Cañaveral','Villaverde','EMT','Metro','Vivienda','Familia Real','Letizia'}
def norm(x):return base.normalize(x)
def found(text,aliases):return any(base.contains(text,a) for a in aliases)
def topic_result(topic,section,title,summary):
 aliases=T[section][topic];t=found(title,aliases);s=found(summary,aliases)
 if not(t or s):return None
 both=title+' '+summary
 if topic=='Vivienda':
  if re.search(HOUSING_EVENT,title) and not re.search(r'\b(precios?|alquiler|hipoteca|mercado|politica|ley)\b',title):return None
  if not re.search(HOUSING,both):return None
  if not t and re.search(r'\b(ley de vivienda|zona\w* tensionad\w*|crisis de la vivienda|mercado inmobiliario|precios? de la vivienda|expulsad\w* del mercado inmobiliario)\b',summary):return 'principal', 'contexto'
 if topic=='Congreso':
  if re.search(CANDIDATE,title) and not re.search(PARLIAMENT,both):return None
  if not re.search(PARLIAMENT,both):return None
 if topic=='Madrid':
  if not re.search(r'\b(madrid|madrilen\w*)\b',title):return None
  if not re.search(LOCAL,both):return None
 if topic=='Metro':
  if not re.search(r'\b(metro|linea [0-9]+|estaciones)\b',title):return None
  if not re.search(r'\b(madrid|madrilen\w*|metro de madrid|suburbano madrilen\w*|linea 6|linea 11)\b',both):return None
 if topic=='Nintendo' and not re.search(r'\b(nintendo|switch|zelda|mario|pokemon|pokémon)\b',title):return None
 if topic in {'GTA','Vengadores','Eurovisión','HBO','Disney'} and not t:return None
 if topic=='Netflix' and not t:
  if not re.search(r'\b(serie|pelicula|estreno|cancelacion|produccion)\b',title):return None
 if topic=='Los Javis' and 'la bola negra' in norm(title) and not re.search(r'\b(javis|calvo|ambrossi)\b',both):return None
 return ('principal','titular') if t else ('secundario','resumen')
def classify(a):
 title=norm(a.get('title',''));summary=norm(a.get('summary',''));source=a.get('source','')
 matches=[]
 for section,topics in T.items():
  for topic in topics:
   if source=='El Mundo' and topic in base.EXCLUDED_EL_MUNDO:continue
   result=topic_result(topic,section,title,summary)
   if result:matches.append({'topic':topic,'section':section,'level':result[0],'where':result[1]})
 # Una noticia puede estar en varias secciones, sin generar copias.
 sections=sorted(set(x['section'] for x in matches),key=lambda x:['Política','Entretenimiento','Videojuegos','Varios'].index(x))
 # Seleccionar la sección más relacionada con el tema, no la del RSS.
 bysec={s:sum(8 if x['level']=='principal' else 4 for x in matches if x['section']==s) for s in sections}
 primary=max(sections,key=lambda s:bysec[s]) if sections else ''
 # Evitar premiar plataforma o marca mencionada tangencialmente.
 strong=[x for x in matches if x['level']=='principal' and x['topic'] not in SOFT]
 secondary=[x for x in matches if x['level']=='secundario' and x['topic'] in SPECIFIC]
 cross=len({x['topic'] for x in strong})>=2 or bool(strong and secondary)
 score=sum(10 if x['level']=='principal' else 4 for x in matches)
 score+=sum(3 for x in matches if x['topic'] in PREF and x['level']=='principal')
 score+=8 if cross else 0
 # Umbral editorial flexible: secundarios con contexto relevante entran en sección.
 if not matches:state='descartada'
 elif cross and score>=18:state='destacada'
 elif score>=19 and any(x['level']=='principal' for x in matches):state='destacada'
 elif score>=4:state='seccion'
 else:state='descartada'
 return matches,sections,primary,score,cross,state

def main():
 p=argparse.ArgumentParser();p.add_argument('--archivo',default=str(ROOT/'datos_v03.json'));p.add_argument('--online',action='store_true');args=p.parse_args()
 report=[];items=[]
 if args.online:
  for name,section,url in base.SOURCES:
   row={'fuente':name,'estado':'','leidas':0,'detalle':''}
   try:
    # v1.5.1: priorizar RSS directo; Google News no adjunta imágenes de origen.
    direct={
      'Nintendúo':'https://nintenduo.com/feed/',
      'SimsVIP':'https://simsvip.com/feed/',
      'ESCplus':'https://www.escplus.es/feed/',
      'Nuevo Sureste':'https://nuevosureste.es/feed/',
      'Teatro Madrid':'https://teatromadrid.com/feed/',
      'Billboard':'https://www.billboard.com/feed/',
    }
    candidate_urls=[direct[name],url] if name in direct and direct[name]!=url else [url]
    got=[];issues=[];used=''
    for candidate in candidate_urls:
     try:
      req=urllib.request.Request(candidate,headers={'User-Agent':'Mozilla/5.0 (compatible; ElEditor/1.5.1)','Accept':'application/rss+xml,application/atom+xml,application/xml,text/xml'})
      with urllib.request.urlopen(req,timeout=13) as r:body=r.read(3_000_001)
      if len(body)>3_000_000:raise ValueError('Feed demasiado grande')
      parsed=base.parse_feed(body,name,section)
      if not parsed:raise ValueError('RSS vacío o sin artículos válidos')
      got=parsed;used=candidate;break
     except Exception as subexc:issues.append(str(subexc)[:75])
    if not got:raise ValueError('; '.join(issues))
    items.extend(got);row.update(estado='OK',leidas=len(got),detalle=('RSS DIRECTO' if used!=url else 'Google News / RSS anterior')+' | '+used[:95])
   except Exception as exc:row.update(estado='ERROR',detalle=str(exc)[:200])
   report.append(row)
 else:items=json.loads(Path(args.archivo).read_text(encoding='utf-8-sig'))['articles']
 processed,dupes=base.process(items)
 for a in processed:
  match,sections,primary,score,cross,state=classify(a)
  a.update(topics=[x['topic'] for x in match],topic_evidence=match,sections=sections,primary_section=primary,score=score,cruce_validado=cross,estado_editorial=state,image_approved=False)
 # Deduplicación conservadora de noticias de distintas cabeceras, por titular muy similar.
 def signature(a):
  words=re.findall(r'[a-z0-9]+',norm(a['title']));stop={'de','la','el','los','las','en','un','una','que','por','para','del','al','con','y','su','se','a','es','tras','sobre'}
  return set(w for w in words if len(w)>3 and w not in stop)
 kept=[];near=[]
 for a in sorted(processed,key=lambda x:(x['score'],x.get('published_utc','')),reverse=True):
  sig=signature(a);match=None
  if len(sig)>=5:
   for b,bsig in kept:
    if a['source']==b['source']:continue
    if len(bsig)>=5 and len(sig&bsig)/len(sig|bsig)>=.83:match=b;break
  if match:near.append({'titular':a['title'],'similar_a':match['title'],'fuente':a['source']});a['possible_duplicate_of']=match['id']
  else:kept.append((a,sig))
 # Mantener todos en diagnóstico; no publicar repetidos detectados.
 for a in processed:
  if a.get('possible_duplicate_of'):a['estado_editorial']='duplicado_posible'
 processed.sort(key=lambda a:(a['estado_editorial']=='destacada',a['estado_editorial']=='seccion',a['score'],a.get('published_utc','')),reverse=True)
 out={'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'total':len(processed),'duplicates_url':dupes,'possible_duplicates':len(near),'articles':processed}
 (ROOT/'noticias_v04.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 with (ROOT/'diagnostico_v04.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['estado','seccion_principal','secciones','puntos','cruce','temas','fuente','titular','url'])
  for a in processed:w.writerow([a['estado_editorial'],a['primary_section'],' | '.join(a['sections']),a['score'],a['cruce_validado'],' | '.join(a['topics']),a['source'],a['title'],a['url']])
 if report:
  with (ROOT/'informe_fuentes_v04.csv').open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(report[0]));w.writeheader();w.writerows(report)
 template=(ROOT/'plantilla.html').read_text(encoding='utf-8')
 safe=json.dumps([{'id':a['id'],'title':a['title'],'source':a['source'],'url':a['url'],'date':a.get('published_utc',''),'topics':a['topics'],'sections':a['sections'],'primary':a['primary_section'],'score':a['score'],'cross':a['cruce_validado'],'state':a['estado_editorial'],'hasImage':bool(a.get('image_candidate'))} for a in processed if a['estado_editorial'] in ('destacada','seccion')],ensure_ascii=False).replace('<','\\u003c')
 (ROOT/'PORTADA_DEMO.html').write_text(template.replace('/*__DATA__*/','const ARTICLES='+safe+';'),encoding='utf-8')
 from collections import Counter
 print('Noticias:',len(processed),'Estados:',dict(Counter(a['estado_editorial'] for a in processed)),'Cruces:',sum(a['cruce_validado'] for a in processed),'Posibles duplicados:',len(near))
 print('Abrir PORTADA_DEMO.html para ver la portada sin conexión')
if __name__=='__main__':main()
