"""Agrupación conservadora de noticias sobre el mismo acontecimiento, entre medios."""
import re,unicodedata,datetime as dt,math
from collections import Counter
from difflib import SequenceMatcher
STOP=set('de del la las el los un una unos unas en a al y o por para con sin que como sobre tras ante entre segun su sus se ha han fue ser esta este estos estas desde hasta hoy ayer manana nuevo nueva asi mas ya lo le les es son dan da hace dado habla revela anuncia confirma cuenta esto todo toda entrevista especial periodista cadena programa television tv noticia noticia actualidad'.split())

def tokens(title):
 t=''.join(c for c in unicodedata.normalize('NFKD',str(title).casefold()) if not unicodedata.combining(c))
 return [w for w in re.findall(r'[a-z0-9]+',t) if len(w)>=3 and w not in STOP]

def date_of(a):
 try:return dt.datetime.fromisoformat(str(a.get('date','')).replace('Z','+00:00'))
 except:return None

EVENT_GENERIC=set('salvados programa emision entrevista entrevistado belen rueda jordi evole episodio serie estreno television actriz actor rtve television cine'.split())

def event_signature(title):
 t=' '.join(tokens(title))
 # Compare explicit events, not just named people. The guest and the event must agree.
 if 'salvados' in t and ('sanchez' in t or 'pedro' in t) and any(w in t for w in ('grab','cancel','emit','bulo')):return 'salvados:sanchez:entrevista-no-grabada'
 return ''

def duplicate(a,b):
 if str(a.get('url','')).split('?')[0]==str(b.get('url','')).split('?')[0]:return True
 da,db=date_of(a),date_of(b)
 if da and db and abs((da-db).total_seconds())>4*86400:return False
 signature_a,signature_b=event_signature(a.get('title','')),event_signature(b.get('title',''))
 if signature_a and signature_a==signature_b:return True
 ta,tb=tokens(a.get('title','')),tokens(b.get('title',''))
 sa,sb=set(ta),set(tb);common=sa&sb
 if min(len(sa),len(sb))<3 or len(common)<3:return False
 ratio=len(common)/min(len(sa),len(sb));jacc=len(common)/len(sa|sb)
 seq=SequenceMatcher(None,' '.join(ta),' '.join(tb)).ratio()
 # Reduce the threshold only if the shared terms describe an event,
 # not merely a celebrity or the name of a TV programme.
 event_words=common-EVENT_GENERIC
 return (ratio>=.77 and jacc>=.45 and len(event_words)>=2) or (ratio>=.66 and jacc>=.38 and seq>=.61 and len(event_words)>=3)

def choose(articles):
 """Prefer article image then news relevance; return winners and a diagnostic."""
 ranked=sorted(articles,key=lambda a:(bool(a.get('image_data')),bool(a.get('image')),float(a.get('score',0)),a.get('date','')),reverse=True)
 kept=[];excluded=[]
 for a in ranked:
  matched=next((b for b in kept if duplicate(a,b)),None)
  if matched:excluded.append((a,matched))
  else:kept.append(a)
 return sorted(kept,key=lambda a:(float(a.get('score',0)),a.get('date','')),reverse=True),excluded
