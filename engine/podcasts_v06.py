"""Episodios desde los RSS oficiales, sin inventar audios ni alojarlos."""
import json,urllib.request,xml.etree.ElementTree as ET,datetime
PODCASTS=[
 ('ser','Las 8 de Hoy por Hoy','https://fapi-top.prisasd.com/podcast/playser/las_8_de_hoy_por_hoy_3131/itunestfp/podcast.xml','https://cadenaser.com/podcast/cadena-ser/hoy-por-hoy/hoy-por-hoy-las-8-de-hoy-por-hoy/3131/'),
 ('onda','El Gabinete','https://www.ondacero.es/rss/podcast/8323/podcast.xml','https://www.ondacero.es/programas/julia-en-la-onda/audios-podcast/el-gabinete/')]
def collect_podcasts(online,root):
 result={}
 for key,name,url,page in PODCASTS:
  episodes=[];error='Sin actualizar: ejecuta la recopilación con Internet'
  if online:
   try:
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 EL EDITOR/0.6','Accept':'application/rss+xml,application/xml,text/xml'})
    with urllib.request.urlopen(req,timeout=16) as r: xml=r.read(3_000_000)
    feed=ET.fromstring(xml)
    for item in feed.findall('.//item')[:6]:
     title=item.findtext('title','').strip();link=item.findtext('link','').strip()
     enc=item.find('enclosure');audio=enc.get('url','') if enc is not None else ''
     if audio.startswith('https://') and title:
      episodes.append({'title':title,'audio':audio,'link':link if link.startswith('http') else page,'date':item.findtext('pubDate','')})
    error='' if episodes else 'El RSS no incluye archivos de audio reproducibles'
   except Exception as exc:error=type(exc).__name__+': '+str(exc)[:150]
  result[key]={'name':name,'page':page,'episodes':episodes,'status':error}
 (root/'podcasts_v06.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 return result
