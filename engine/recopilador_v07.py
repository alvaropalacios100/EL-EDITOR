"""EL EDITOR v0.5: recopila, clasifica y genera portada offline. Python 3.10+ estándar."""
import sys,json,subprocess,re,unicodedata,html,base64,csv,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
cfg=json.loads((ROOT/'prioridades.json').read_text(encoding='utf-8'))
def norm(s):
 s=unicodedata.normalize('NFKD',str(s).casefold());return ''.join(c for c in s if not unicodedata.combining(c))
def hit(text,term):
 return bool(re.search(r'(?<![a-z0-9])'+re.escape(norm(term))+r'(?![a-z0-9])',norm(text)))
ALIASES={
 'Congreso de los Diputados':['congreso de los diputados','congreso','diputados','parlamento','hemiciclo'],
 'Metro de Madrid':['metro de madrid','metro','suburbano madrileño','linea 6','linea 11'],
 'EMT Madrid':['emt','autobuses municipales'],
 'Audiencias de televisión':['audiencias','cuota de pantalla','audiencia de television'],
 'La 1 (TVE)':['la 1','tve','television española'],
 'Los Javis':['los javis','javier calvo','javier ambrossi','la bola negra'],
 'La Oreja de Van Gogh':['la oreja de van gogh','lodvg'],
 'Leire Martínez':['leire martinez'],
 'Harry Potter':['harry potter','hogwarts'],
 'Juego de Tronos':['juego de tronos','game of thrones'],
 'La Casa del Dragón':['la casa del dragon','house of the dragon'],
 'Drag Race':['drag race','drag race españa'],
 'Operación Triunfo':['operacion triunfo','ot 2026','ot 2027'],
 'City builders (general)':['city builder','city builders','construccion de ciudades'],
 'Cities: Skylines':['cities skylines','cities: skylines'],
 'Los Sims':['los sims','the sims','sims 4'],
 'El Cañaveral':['el cañaveral','canaveral'],
 'Madrid (política y actualidad local)':['madrid'],
 'Vivienda':['vivienda','alquiler','hipoteca','pisos turisticos','zonas tensionadas'],
 'Familia Real':['familia real','rey felipe','reina letizia'],
 'Eurovisión':['eurovision'],
 'Benidorm Fest':['benidorm fest'],
 'Pokémon':['pokemon'],
 'Pokémon GO':['pokemon go'],
 'GTA':['gta','grand theft auto'],
 'Musicales de Madrid':['musicales de madrid','musical en madrid'],
}
CELEBS=set(cfg['Celebrities'])
RESTRICT_GENERIC={'Madrid (política y actualidad local)','Congreso de los Diputados','Vivienda','Netflix','Nintendo','Televisión española','La 1 (TVE)','GTA'}
EVENTS=('incendio','herido','bombero','accidente','atropello','rescate','suceso')
LOCAL_CONTEXT=('metro','emt','ayuntamiento','asamblea','urbanismo','vivienda','alquiler','transporte','obras','presupuesto','barrio','servicio publico','infraestructura','municipal')
HOUSING_CONTEXT=('alquiler','hipoteca','precio','zona tensionada','ley de vivienda','mercado inmobiliario','pisos turisticos','desahucio','residencial','segunda residencia','vivienda social')
PARLIAMENT_CONTEXT=('diputado','pleno','votacion','parlamentari','legislativ','congreso de los diputados','camara baja','comision')
def mentions(a,topic):
 title=norm(a.get('title',''));summary=norm(a.get('summary',''))
 aliases=ALIASES.get(topic,[topic]);t=any(hit(title,x) for x in aliases);s=any(hit(summary,x) for x in aliases)
 if not(t or s):return 0
 if topic=='Vivienda':
  if any(x in title for x in EVENTS) and not any(x in title for x in HOUSING_CONTEXT):return 0
  if not any(x in title+' '+summary for x in HOUSING_CONTEXT):return 0
 if topic=='Madrid (política y actualidad local)':
  if not t or not any(x in title+' '+summary for x in LOCAL_CONTEXT):return 0
  if any(x in title for x in EVENTS):return 0
 if topic=='Congreso de los Diputados':
  if 'candidatura' in title and not any(x in title+' '+summary for x in PARLIAMENT_CONTEXT):return 0
  if not any(x in title+' '+summary for x in PARLIAMENT_CONTEXT):return 0
 if topic=='Metro de Madrid' and not any(x in title+' '+summary for x in ('madrid','madrileñ','linea 6','linea 11')):return 0
 if topic=='GTA' and not t:return 0
 return 2 if t else 1

def main():
 online='--online' in sys.argv
 cmd=[sys.executable,str(ROOT/'recopilador_v04.py')]+(['--online'] if online else ['--archivo',str(ROOT/'datos_v03.json')])
 subprocess.run(cmd,cwd=ROOT,check=True)
 data=json.loads((ROOT/'noticias_v04.json').read_text(encoding='utf-8'))
 for a in data['articles']:
  matches=[]
  for sec,topics in cfg.items():
   if sec=='El Gabinete':continue
   for topic,priority in topics.items():
    if a.get('source')=='El Mundo' and topic in ('Pablo Iglesias','Irene Montero','Pedro Sánchez','Yolanda Díaz','Ada Colau','Mónica García','Manuela Bergerot','Eduardo Rubiño'):continue
    m=mentions(a,topic)
    if m:matches.append({'topic':topic,'section':sec,'priority':priority,'centrality':'titular' if m==2 else 'resumen','strength':m})
  # preserve evidence of contextual match from prior engine when its topic is an alias of the new taxonomy
  for m in a.get('topic_evidence',[]):
   topic=m.get('topic','');section=m.get('section','')
   rename={'Metro':'Metro de Madrid','EMT':'EMT Madrid','La 1':'La 1 (TVE)','Audiencias':'Audiencias de televisión','Movistar Plus':'Movistar Plus+','Madrid':'Madrid (política y actualidad local)'}
   topic=rename.get(topic,topic);section='Express' if section=='Varios' else section
   if section not in cfg or topic not in cfg[section]:continue
   if any(x['topic']==topic and x['section']==section for x in matches):continue
   if mentions(a,topic):matches.append({'topic':topic,'section':section,'priority':cfg[section][topic],'centrality':'resumen','strength':1})
  # filter out generic side references; favor central headline topic and meaningful summary mentions
  if matches:
   secscore={s:sum((2 if m['strength']==2 else 1)*{'alta':4,'media':2,'aleatoria':1}[m['priority']] for m in matches if m['section']==s) for s in cfg}
   sections=[s for s,v in secscore.items() if v>0]
   primary=max(sections,key=lambda s:secscore[s])
   score=sum((9 if m['strength']==2 else 3)*{'alta':3,'media':2,'aleatoria':1}[m['priority']] for m in matches)
   strong=[m for m in matches if m['strength']==2 and m['topic'] not in RESTRICT_GENERIC]
   cross=len(set(m['topic'] for m in strong))>1
   if cross:score+=9
   state='destacada' if (cross and score>=25) or (score>=27 and any(m['priority']=='alta' and m['strength']==2 for m in matches)) else 'seccion'
  else:sections=[];primary='';score=0;cross=False;state='descartada'
  if a.get('possible_duplicate_of'):state='duplicado_posible'
  a.update(matches_v05=matches,sections=sections,primary_section=primary,score_v05=score,cruce_validado_v05=cross,estado_v05=state)
 data['matches_v05']=sum(a['estado_v05'] in ('destacada','seccion') for a in data['articles'])
 data['generated_at_v05']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 (ROOT/'noticias_v05.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 with (ROOT/'diagnostico_v05.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['estado','seccion','puntuacion','prioridades','temas','fuente','titular','url'])
  for a in data['articles']:
   w.writerow([a['estado_v05'],a['primary_section'],a['score_v05'],' | '.join(m['priority'] for m in a['matches_v05']),' | '.join(m['topic'] for m in a['matches_v05']),a['source'],a['title'],a['url']])
 articles=[{'id':a['id'],'title':a['title'],'source':a['source'],'url':a['url'],'date':a.get('published_utc',''),'sections':a['sections'],'primary':a['primary_section'],'score':a['score_v05'],'cross':a['cruce_validado_v05'],'state':a['estado_v05'],'topics':[m['topic'] for m in a['matches_v05']],'priorities':[m['priority'] for m in a['matches_v05']]} for a in data['articles'] if a['estado_v05'] in ('destacada','seccion')]
 articles.sort(key=lambda a:(a['score'],a['date']),reverse=True)
 payload=json.dumps(articles,ensure_ascii=False).replace('<',chr(92)+'u003c')
 template=(ROOT/'plantilla_v07.html').read_text(encoding='utf-8')
 trophy=base64.b64encode((ROOT/'estatuilla_celebrities.png').read_bytes()).decode()
 output=template.replace('/*__ARTICLES__*/','const ARTICLES='+payload+';').replace('__TROPHY_BASE64__',trophy)
 # v0.6: podcast feed audio links are collected server-side, not by browser (avoids CORS).
 from podcasts_v06 import collect_podcasts
 episodes=collect_podcasts(online=online, root=ROOT)
 output=output.replace('/*__PODCASTS__*/','const PODCASTS='+json.dumps(episodes,ensure_ascii=False).replace('<','\\u003c')+';')
 from videos_v07 import collect
 videos=collect(online=online)
 output=output.replace('/*__VIDEOS__*/','const VIDEOS='+json.dumps(videos,ensure_ascii=False).replace('<','\\u003c')+';')
 (ROOT/'PORTADA_DEMO_v07.html').write_text(output,encoding='utf-8')
 from collections import Counter
 print('EL EDITOR v0.6:',len(data['articles']),'analizadas,',data['matches_v05'],'seleccionadas; estados:',dict(Counter(a['estado_v05'] for a in data['articles'])))
 print('Abrir PORTADA_DEMO_v07.html')
if __name__=='__main__':main()
