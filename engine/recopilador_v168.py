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
 'La bola negra':['la bola negra'],
 'Pluribus':['pluribus'],
 'Paquita Salas':['paquita salas'],
 'Hacks':['hacks serie', 'hacks hbo', 'serie hacks'],
 'Chicote':['alberto chicote', 'chicote'],
 'Make Up Stars':['make up stars', 'makeup stars'],
 'Ice Age 6':['ice age 6', 'la era de hielo 6'],
 'Frozen 3':['frozen 3', 'frozen iii'],
 'Shrek 5':['shrek 5'],
 'James Gunn':['james gunn'],
 'Wonder Woman':['wonder woman'],
 'Iron Man':['iron man', 'hombre de hierro'],
 'Samantha Ballentines':['samantha ballentines'],
 'Muertos S.L.':['muertos sl', 'muertos s.l.'],
 'La casa de papel':['la casa de papel', 'money heist'],
 'Margot Robbie':['margot robbie'],
 'Greta Gerwig':['greta gerwig'],
 'La Odisea':['la odisea nolan', 'the odyssey christopher nolan'],
 'Nolan':['christopher nolan', 'nolan'],
 'Tarantino':['quentin tarantino', 'tarantino'],
 'Villeneuve':['denis villeneuve', 'villeneuve'],
 'Almodóvar':['pedro almodovar', 'almodovar'],
 'Amenábar':['alejandro amenabar', 'amenabar'],

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
 'Ofertas de Steam':['ofertas de steam', 'rebajas de steam', 'steam sale', 'descuentos de steam', 'festival de ofertas de steam'],
 'Los Simpson en Fortnite':['los simpson en fortnite', 'simpsons fortnite', 'fortnite x simpsons', 'fortnite los simpson'],
 'Hogwarts Legacy':['hogwarts legacy'],
 'Trópico 7':['tropico 7', 'trópico 7'],
 'Rockstar':['rockstar games', 'rockstar'],
 'Red Dead Redemption':['red dead redemption', 'red dead online'],
 'Nintendo DS':['nintendo ds', 'nintendo dsi', 'nds'],
 'Switch 2':['nintendo switch 2', 'switch 2', 'switch ii'],
 'Pokémon Viento y Oleaje':['pokemon viento y oleaje', 'pokémon viento y oleaje', 'pokemon winds and waves'],
 'Hit & Run':['simpsons hit and run', 'simpson hit & run', 'hit & run', 'hit and run'],
 'Playus':['playus'],
 'Builders of Egypt':['builders of egypt'],
 'Planet Zoo':['planet zoo'],
 'Two Point Hospital':['two point hospital'],
 'DC Comics en Fortnite':['dc comics en fortnite', 'dc x fortnite', 'fortnite dc comics', 'batman en fortnite', 'superman en fortnite'],

 'Musicales de Madrid':['musicales de madrid','musical en madrid','teatro musical en madrid','estreno del musical'],
 'Premios Óscar':['premios oscar','premios óscar','los oscar','los óscar','academia de hollywood','academy awards'],
 'Jordi Évole':['jordi evole','jordi évolé','jordi évole'],
 'Salvados':['salvados','programa salvados'],
 'Marc Giró':['marc giro','marc giró'],
 'Silvia Intxaurrondo':['silvia intxaurrondo'],
 'La Revuelta':['la revuelta','david broncano'],
 'La Séptima (canal de televisión)':['la septima television','la séptima television','la septima canal','la séptima canal','canal la septima','canal la séptima'],
 'Nintendo':['nintendo','switch','zelda','super mario','mario kart','metroid','kirby','game boy','pokémon','pokemon','animal crossing'],
 'Plantas y jardinería':['plantas','jardineria','huerto','cultivo','flores','arbustos','semillas','bonsai'],
 'Hogar y decoración':['decoracion','muebles','interiorismo','ikea','ordenar la casa','organizacion del hogar'],
 'Cartelera de teatro en Madrid':['cartelera teatral de madrid','cartelera de madrid','teatros de madrid','teatro español','teatros del canal','teatro real','estreno teatral en madrid'],
 'Agenda cultural de Madrid':['agenda cultural madrid','exposicion en madrid','museo del prado','matadero madrid','centro cultural conde duque','festival cultural en madrid'],
 'Cocina vegetariana':['receta vegetariana','recetas vegetarianas','receta vegana','recetas veganas','cocina vegetariana','plato vegetariano'],
 'Obama':['barack obama', 'expresidente obama', 'ex presidente obama'],
 'Presidente del Gobierno de España':['presidente del gobierno', 'presidente del ejecutivo español', 'presidencia del gobierno de españa'],
 'Gobierno de España':['gobierno de españa', 'gobierno español', 'ejecutivo español', 'consejo de ministros'],
 'Gobierno británico':['gobierno britanico', 'gobierno del reino unido', 'primer ministro britanico', 'downing street', 'gobierno laborista britanico'],
 'Unión Europea':['union europea', 'comision europea', 'parlamento europeo', 'consejo europeo', 'bruselas'],
 'Donald Trump':['donald trump', 'presidente trump'],
 'Ministerio del Interior':['ministerio del interior', 'ministro del interior', 'fernando grande-marlaska'],
 'Vicepresidencia del Gobierno de España':['vicepresidencia del gobierno', 'vicepresidente del gobierno', 'vicepresidenta del gobierno', 'vicepresidencias del gobierno'],
 'Ministerio de Igualdad':['ministerio de igualdad', 'ministra de igualdad'],
 'Encuestas electorales':['encuesta electoral', 'sondeo electoral', 'estimacion de voto', 'estimación de voto', 'barometro electoral', 'barómetro electoral', 'intencion de voto', 'intención de voto'],
 'Elecciones España':['elecciones generales', 'elecciones legislativas en españa', 'elecciones en españa', 'elecciones españolas', 'elecciones al congreso'],
 'Elecciones Madrid':['elecciones comunidad de madrid', 'elecciones autonomicas de madrid', 'elecciones autonómicas de madrid', 'elecciones municipales en madrid', 'elecciones madrid'],
 'Podemos':['podemos', 'ione belarra'],
 'Frente Amplio':['frente amplio'],
 'PSOE':['psoe', 'partido socialista obrero español'],
 'VOX':['vox', 'santiago abascal'],
 'PP':['partido popular', 'partido popular español', 'feijoo', 'feijóo', 'alberto nunez feijoo', 'alberto núñez feijóo'],
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
  # Mentions of mortgages in movie/celebrity headlines are not housing reporting.
  if a.get('source') in {'SensaCine','Espinof','FórmulaTV','Vertele','LOS40','Billboard','Europa Press Cultura'}:return 0
  if any(x in title for x in ('adios hipoteca','pagar la hipoteca','pago la hipoteca','maletines','george clooney')) and not any(x in title for x in ('ley de vivienda','precio de vivienda','mercado inmobiliario','tipo de interes')):return 0
  if any(x in title for x in EVENTS) and not any(x in title for x in HOUSING_CONTEXT):return 0
  if not any(x in title+' '+summary for x in HOUSING_CONTEXT):return 0
 if topic=='Madrid (política y actualidad local)':
  if not t or not any(x in title+' '+summary for x in LOCAL_CONTEXT):return 0
  if any(x in title for x in EVENTS):return 0
 if topic=='Congreso de los Diputados':
  if 'candidatura' in title and not any(x in title+' '+summary for x in PARLIAMENT_CONTEXT):return 0
  if not any(x in title+' '+summary for x in PARLIAMENT_CONTEXT):return 0
 if topic=='Metro de Madrid' and not any(x in title+' '+summary for x in ('madrid','madrileñ','linea 6','linea 11')):return 0
 if topic in {'Presidente del Gobierno de España','Gobierno de España','Gobierno británico','Unión Europea','Ministerio del Interior','Vicepresidencia del Gobierno de España','Ministerio de Igualdad','Encuestas electorales','Elecciones España','Elecciones Madrid','Podemos','Frente Amplio','PSOE','VOX','PP'} and not t:return 0
 if topic=='Unión Europea' and not any(x in title for x in ('union europea','comision europea','parlamento europeo','consejo europeo')):return 0
 if topic=='Frente Amplio' and not any(x in title+' '+summary for x in ('españa','espanol','español','politica española','alianza de izquierdas','sumar','podemos','elecciones')):return 0
 if topic=='Leonor' and not any(x in title+' '+summary for x in ('princesa leonor','princesa de asturias','leonor de borbon','leonor de borbón','heredera al trono','infanta leonor')):return 0
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
  if a.get('source')=='GTA actualidad' and any(hit(a.get('title',''),x) for x in ('gta','gta 6','gta vi','grand theft auto')) and not any(m['topic']=='GTA' for m in matches):
   matches.append({'topic':'GTA','section':'Videojuegos','priority':'media','centrality':'titular','strength':2})
  # preserve evidence of contextual match from prior engine when its topic is an alias of the new taxonomy
  for m in a.get('topic_evidence',[]):
   topic=m.get('topic','');section=m.get('section','')
   rename={'Metro':'Metro de Madrid','EMT':'EMT Madrid','La 1':'La 1 (TVE)','Audiencias':'Audiencias de televisión','Movistar Plus':'Movistar Plus+','Madrid':'Madrid (política y actualidad local)'}
   topic=rename.get(topic,topic);section='Express' if section=='Varios' else section
   if section not in cfg or topic not in cfg[section]:continue
   if any(x['topic']==topic and x['section']==section for x in matches):continue
   if mentions(a,topic):matches.append({'topic':topic,'section':section,'priority':cfg[section][topic],'centrality':'resumen','strength':1})
  # v1.6.0: el contenido de videojuegos no salta a EL ESPECTADOR por mencionar
  # Harry Potter, Batman, Los Simpson, etc. 3DJuegos es una fuente exclusiva de GAME.
  gaming_title=norm(a.get('title',''))
  gaming_summary=norm(a.get('summary',''))
  gaming_title_terms=('hogwarts legacy','fortnite','videojuego','videojuegos','juego de pc',
   'nintendo ds','switch 2','nintendo switch','steam','rockstar games','red dead redemption',
   'tropico 7','builders of egypt','planet zoo','two point hospital',
   'pokemon viento y oleaje','pokemon winds and waves','simpsons hit and run',
   'cities skylines','los sims','grand theft auto','gta vi','gta 6','pokemon')
  known_game=any(x in gaming_title for x in gaming_title_terms)
  specialized=a.get('source') in {'3DJuegos','VidaExtra','Nintenderos','Nintendúo',
    'Vandal','SimsVIP','GTA actualidad'}
  if known_game or specialized:
   # Un videojuego puede referirse a una película, pero su sección es GAME.
   matches=[m for m in matches if m['section'] not in ('Entretenimiento','Celebrities')]
   if not any(m['section']=='Videojuegos' for m in matches):
    if known_game or (specialized and any(x in gaming_title for x in ('juego','videojuego','gaming','consola','pc'))):
     matches.append({'topic':'Actualidad de videojuegos','section':'Videojuegos',
       'priority':'aleatoria','centrality':'titular','strength':2})
  if a.get('source')=='3DJuegos':
   matches=[m for m in matches if m['section'] not in ('Política','Express')]
  # v1.5.5: editorial source restrictions precede ranking, not only UI display.
  # SensaCine publishes cinema; a metaphor about a mortgage cannot be a housing news article.
  if a.get('source') in {'SensaCine','Espinof'}:
   matches=[m for m in matches if m['section']!='Política']
  # v1.3: medios especializados de EXPRESS; permitir la actualidad relevante
  # aunque no coincida literalmente con una palabra clave original.
  source=a.get('source',''); title=norm(a.get('title','')); summary=norm(a.get('summary',''))
  if 'Express' in cfg and not any(m['section']=='Express' for m in matches):
   related=(('teatro' in title or 'musical' in title or 'obra' in title or 'cartelera' in title or 'estreno' in title) and source in
          ('Teatro Madrid','Madrid Destino','Madrid Actual Teatro','Teatro y musicales esMadrid','Cartelera Madrid','Teatro y musicales Madrid','Cultura Madrid','Agenda cultural Madrid'))
   garden=(source in ('Verdecora blog','Decoesfera','Decoración hogar','IKEA hogar') and
           any(w in title for w in ('planta','jardin','huerto','decoracion','mueble','casa','hogar','ikea','cultiv','flor','balcon','terraza')))
   culture=(source in ('Madrid Destino','Cultura Madrid','Agenda cultural Madrid') and
            any(w in title for w in ('museo','exposicion','teatro','estreno','musical','agenda cultural','festival')))
   if related or garden or culture:
    topic='Musicales de Madrid' if 'musical' in title else ('Plantas y jardinería' if garden and any(w in title for w in ('planta','jardin','huerto','cultiv','flor')) else ('Hogar y decoración' if garden else 'Agenda cultural de Madrid'))
    matches.append({'topic':topic,'section':'Express','priority':'media' if related else 'aleatoria','centrality':'titular','strength':2})
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
 articles=[{'id':a['id'],'title':a['title'],'summary':a.get('summary',''),'source':a['source'],'url':a['url'],'date':a.get('published_utc',''),'sections':a['sections'],'primary':a['primary_section'],'score':a['score_v05'],'cross':a['cruce_validado_v05'],'state':a['estado_v05'],'topics':[m['topic'] for m in a['matches_v05']],'priorities':[m['priority'] for m in a['matches_v05']],'image':a.get('image_candidate','') if str(a.get('image_candidate','')).startswith('https://') else ''} for a in data['articles'] if a['estado_v05'] in ('destacada','seccion')]
 # Política editorial: nunca publicar noticias de más de 21 días ni fechas desconocidas.
 # En prueba sin Internet conservamos el histórico para visualizar el diseño, con aviso visible.
 if online:
  def recent(a):
   try:
    d=datetime.datetime.fromisoformat(str(a.get('date','')).replace('Z','+00:00'))
    if d.tzinfo is None:return False
    age=(datetime.datetime.now(datetime.timezone.utc)-d).total_seconds()
    return -3600 <= age <= 21*86400
   except (ValueError,TypeError,OverflowError):return False
  before=len(articles);articles=[a for a in articles if recent(a)]
  print('Filtro de actualidad (21 días):',len(articles),'de',before,'seleccionadas; sin fecha y antiguas descartadas')
 articles.sort(key=lambda a:(a['score'],a['date']),reverse=True)
 # v1.5.3: evitar la misma noticia redactada por medios diferentes.
 # Aplicar al conjunto elegido antes de descargar miniaturas y renderizar.
 from duplicados_v153 import choose
 articles,duplicate_pairs=choose(articles)
 with (ROOT/'diagnostico_duplicados_v153.csv').open('w',encoding='utf-8-sig',newline='') as df:
  dw=csv.writer(df);dw.writerow(['titular_descartado','medio_descartado','titular_conservado','medio_conservado'])
  for discarded,winner in duplicate_pairs:
   dw.writerow([discarded['title'],discarded['source'],winner['title'],winner['source']])
 print('Duplicados entre medios excluidos:',len(duplicate_pairs))

 from collections import Counter
 with (ROOT/'diagnostico_cobertura_v13.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['fuente','articulos_recibidos','seleccionados','con_foto_rss','seccion_principal'])
  sources=sorted({a.get('source','') for a in data['articles']})
  for source in sources:
   raw=[a for a in data['articles'] if a.get('source')==source]
   sel=[a for a in raw if a['estado_v05'] in ('destacada','seccion')]
   winner=Counter(a.get('primary_section','') for a in sel).most_common(1)
   w.writerow([source,len(raw),len(sel),sum(bool(a.get('image_candidate')) for a in sel),winner[0][0] if winner else ''])
 with (ROOT/'diagnostico_imagenes_por_medio_v151.csv').open('w',encoding='utf-8-sig',newline='') as _fi:
  _writer=csv.writer(_fi);_writer.writerow(['medio','seleccionadas','con_url_imagen_al_inicio'])
  for _source in sorted(set(x['source'] for x in articles)):
   _items=[x for x in articles if x['source']==_source]
   _writer.writerow([_source,len(_items),sum(bool(x.get('image')) for x in _items)])
 print('Fotos disponibles en RSS para tarjetas:',sum(bool(a['image']) for a in articles),'de',len(articles))
 if online:
  from imagenes_v159 import enrich
  more=enrich(articles)
  print('Fotos adicionales localizadas mediante metadatos de origen:',more)
 if online:
  from miniaturas_v14 import embed
  good,total=embed(articles,max_articles=len(articles))
  print('Miniaturas incrustadas directamente en el HTML:',good,'de',total,'direcciones únicas')
  import csv as _csv
  with (ROOT/'diagnostico_imagenes_v15.csv').open('w',encoding='utf-8-sig',newline='') as _f:
   _w=_csv.writer(_f);_w.writerow(['medio','titulo','url_imagen_detectada','descarga_incrustada','url_noticia'])
   for _a in articles:_w.writerow([_a['source'],_a['title'],_a.get('image',''),bool(_a.get('image_data')),_a['url']])
 # v1.5.6: per-article missing-photo root cause for actionability.
 with (ROOT/'diagnostico_fotos_v156.csv').open('w',encoding='utf-8-sig',newline='') as _report:
  _writer=csv.writer(_report);_writer.writerow(['medio','titular','estado_fotografia','motivo_probable','url_noticia','url_imagen'])
  for _a in articles:
   _embedded=bool(_a.get('image_data'))
   _hasurl=bool(_a.get('image'))
   _google='news.google.com' in _a.get('url','')
   _status='INCRUSTADA' if _embedded else ('URL_SIN_DESCARGA' if _hasurl else 'SIN_URL')
   _reason=('OK' if _embedded else ('Se detectó URL pero no se pudo incrustar (verificar HTTP, tamaño y formato)' if _hasurl else ('Resultado indirecto de Google News sin imagen' if _google else 'RSS y metadatos sin imagen')))
   _writer.writerow([_a['source'],_a['title'],_status,_reason,_a.get('url',''),_a.get('image','')])
 with (ROOT/'diagnostico_fotos_v159.csv').open('w',encoding='utf-8-sig',newline='') as _diag:
  _w=csv.writer(_diag);_w.writerow(['medio','titular','resultado_final','extraccion_origen','url_articulo','url_original_resuelta','url_fotografia','foto_incrustada'])
  for _a in articles:
   _estado='INCRUSTADA' if _a.get('image_data') else ('DESCARGA_FALLIDA' if _a.get('image') else 'SIN_URL')
   _w.writerow([_a.get('source',''),_a.get('title',''),_estado,_a.get('foto_origen_estado','SIN_DATOS'),_a.get('url',''),_a.get('foto_url_original',''),_a.get('image',''),bool(_a.get('image_data'))])
 with (ROOT/'diagnostico_game_v154.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['medio','titulo','fecha','clasificacion','seleccionada'])
  for a in data['articles']:
   if a.get('source')=='GTA actualidad' or 'GTA' in [x.get('topic') for x in a.get('matches_v05',[])]:
    w.writerow([a['source'],a['title'],a.get('published_utc',''),a.get('primary_section',''),a['id'] in {x['id'] for x in articles}])
 # v1.6.4: feed internacional original de cultura, titular traducido cuando el servicio responde.
 from espectador_internacional_v164 import collect as collect_thr
 thr_articles=collect_thr(online=online)
 articles.extend(thr_articles)
 # International foreign press: a separate editorial module, no longer classified inside NOTICIAS.
 from internacional_v158 import collect as collect_international
 international=collect_international(online=online)
 foreign=international.get('articles',[])
 if online and foreign:
  from miniaturas_v14 import embed as embed_foreign
  embed_foreign(foreign,max_articles=len(foreign))
 articles.extend(foreign) # Allows saving international articles using existing favorites.
 # Variety supplies culture and celebrity stories in their original outlet, translated for display.
 from variety_v166 import collect as collect_variety
 variety=collect_variety(online=online)
 if variety:
  existing={a.get('url') for a in articles}
  variety=[a for a in variety if a.get('url') not in existing]
  if online and variety:
   from miniaturas_v14 import embed as embed_variety
   embed_variety(variety,max_articles=len(variety))
  articles.extend(variety)
 payload=json.dumps(articles,ensure_ascii=False).replace('<',chr(92)+'u003c')
 from publicaciones_v164 import publish as publish_columns
 editoriales,cinematografo=publish_columns()
 template=(ROOT/'plantilla_v168.html').read_text(encoding='utf-8')
 trophy=base64.b64encode((ROOT/'estatuilla_celebrities.png').read_bytes()).decode()
 output=template.replace('/*__ARTICLES__*/','const ARTICLES='+payload+';')
 output=output.replace('/*__EDITORIALES__*/','const EDITORIALES='+json.dumps(editoriales,ensure_ascii=False).replace('<','\\u003c')+';').replace('__TROPHY_BASE64__',trophy)
 output=output.replace('/*__CINEMATOGRAFO__*/','const CINEMATOGRAFO='+json.dumps(cinematografo,ensure_ascii=False).replace('<','\\u003c')+';')
 output=output.replace('__WOLF_BASE64__',base64.b64encode((ROOT/'lobo_cabecera.png').read_bytes()).decode('ascii'))
 output=output.replace('__FAVICON_BASE64__',base64.b64encode((ROOT/'icon-32.png').read_bytes()).decode('ascii'))
 output=output.replace('__GAME_BASE64__',base64.b64encode((ROOT/'game_cabecera.png').read_bytes()).decode('ascii'))
 output=output.replace('__CAMERA_BASE64__',base64.b64encode((ROOT/'camara_espectador.png').read_bytes()).decode('ascii'))
 output=output.replace('__SER_BASE64__',base64.b64encode((ROOT/'logo_cadena_ser.svg').read_bytes()).decode('ascii'))
 output=output.replace('__GLOBE_BASE64__',base64.b64encode((ROOT/'globo_espana.png').read_bytes()).decode('ascii'))
 output=output.replace('__ONDA_BASE64__',base64.b64encode((ROOT/'logo_onda_cero.jpg').read_bytes()).decode('ascii'))
 # v0.6: podcast feed audio links are collected server-side, not by browser (avoids CORS).
 from podcasts_v06 import collect_podcasts
 episodes=collect_podcasts(online=online, root=ROOT)
 output=output.replace('/*__INTERNATIONAL__*/','const INTERNATIONAL='+json.dumps(international,ensure_ascii=False).replace('<','\\u003c')+';')
 output=output.replace('/*__PODCASTS__*/','const PODCASTS='+json.dumps(episodes,ensure_ascii=False).replace('<','\\u003c')+';')
 output=output.replace('/*__THR__*/','const THR_ARTICLES='+json.dumps(thr_articles,ensure_ascii=False).replace('<','\\u003c')+';')
 from videos_v168 import collect
 videos=collect(online=online)
 with (ROOT/'diagnostico_videos_v168.csv').open('w',encoding='utf-8-sig',newline='') as _df:
  _vw=csv.writer(_df);_vw.writerow(['seccion','hueco','canal','titulo','edad_aproximada_dias','url','estado'])
  for _sec,_slots in json.loads((ROOT/'video_slots_v166.json').read_text(encoding='utf-8')).items():
   _by={x['slot']:x['video'] for x in videos.get('sections',{}).get(_sec,[])}
   for _i in range(len(_slots)):
    _v=_by.get(_i,{})
    _vw.writerow([_sec,_i+1,_v.get('channel',''),_v.get('title',''),_v.get('age_days',''),_v.get('id') and 'https://www.youtube.com/watch?v='+_v['id'] or '',videos.get('status',{}).get(f'{_sec}-{_i}','Sin resultado')])
 output=output.replace('/*__VIDEOS__*/','const VIDEOS='+json.dumps(videos,ensure_ascii=False).replace('<','\\u003c')+';')
 from nature_v166 import collect as collect_nature
 nature=collect_nature(online=online)
 with (ROOT/'diagnostico_nature_v168.csv').open('w',encoding='utf-8-sig',newline='') as _nf:
  _nw=csv.writer(_nf);_nw.writerow(['medio','estado_rss','hueco_seleccionado','titular','url'])
  _indexed={entry['article']['source']:[] for entry in nature.get('articles',[])}
  for _entry in nature.get('articles',[]):_indexed.setdefault(_entry['article']['source'],[]).append(_entry)
  for _name,_stat in nature.get('status',{}).items():
   _items=_indexed.get(_name,[])
   if not _items:_nw.writerow([_name,_stat,'','',''])
   for _item in _items:_nw.writerow([_name,_stat,_item['slot']+1,_item['article']['title'],_item['article']['url']])
 if online and nature.get('articles'):
  from miniaturas_v14 import embed as embed_nature
  _n=[entry['article'] for entry in nature['articles']]
  embed_nature(_n,max_articles=len(_n))
 output=output.replace('/*__NATURE__*/','const NATURE_NEWS='+json.dumps(nature,ensure_ascii=False).replace('<','\\u003c')+';')
 output=output.replace('__NATURE_BASE64__',base64.b64encode((ROOT/'nature_cabecera_recorte.png').read_bytes()).decode('ascii'))
 
 
 # Dos noticias generales de portada de El País, con imágenes del MRSS.
 from portada_pais_v13 import collect_pais_pair
 pais=collect_pais_pair(online=online,root=ROOT)
 output=output.replace('/*__PAIS__*/','const PAIS_NEWS='+json.dumps(pais,ensure_ascii=False).replace('<','\\u003c')+';')
 from portada_eldiario_v155 import collect_eldiario
 eldiario=collect_eldiario(online=online,root=ROOT)
 from xataka_v162 import collect as collect_xataka
 xataka=collect_xataka(online=online)
 output=output.replace('/*__XATAKA__*/','const XATAKA_NEWS='+json.dumps(xataka,ensure_ascii=False).replace('<','\\u003c')+';')
 output=output.replace('/*__ELDIARIO__*/','const ELDIARIO_NEWS='+json.dumps(eldiario,ensure_ascii=False).replace('<','\\u003c')+';')
 from vertele_v152 import pick_vertele
 vertele=pick_vertele(data['articles'],online=online)
 output=output.replace('/*__VERTELE__*/','const VERTELE_NEWS='+json.dumps(vertele,ensure_ascii=False).replace('<','\u003c')+';')
 from sensacine_v154 import pick_sensacine
 sensacine=pick_sensacine(data['articles'],online=online)
 output=output.replace('/*__SENSACINE__*/','const SENSACINE_NEWS='+json.dumps(sensacine,ensure_ascii=False).replace('<','\\u003c')+';')
 from formulatv_v13 import pick_formula
 formula=pick_formula(data['articles']) if online else None
 output=output.replace('/*__FORMULA__*/','const FORMULA_NEWS='+json.dumps(formula,ensure_ascii=False).replace('<','\\u003c')+';')
 (ROOT/'PORTADA_DEMO_v168.html').write_text(output,encoding='utf-8')
 (ROOT/'PORTADA_DEMO.html').write_text(output,encoding='utf-8')
 from collections import Counter
 print('EL EDITOR v1.6.8:',len(data['articles']),'analizadas,',data['matches_v05'],'seleccionadas; estados:',dict(Counter(a['estado_v05'] for a in data['articles'])))
 print('Abrir PORTADA_DEMO_v168.html')
if __name__=='__main__':main()
