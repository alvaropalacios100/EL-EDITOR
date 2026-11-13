"""Pick a recent lead from Xataka RSS as Express News fixed position."""
import datetime
from internacional_v158 import rss_read,fresh
RSS='https://www.xataka.com/index.xml'
def collect(online=False):
 if not online:return None
 now=datetime.datetime.now(datetime.timezone.utc)
 items=rss_read(RSS,'Xataka','es')
 valid=[a for a in items if fresh(a,now) and a.get('url','').startswith('https://')]
 if not valid:return None
 a=valid[0]
 from email.utils import parsedate_to_datetime
 try:a['date']=parsedate_to_datetime(a['date']).isoformat()
 except Exception:pass
 a['id']='xataka-'+str(abs(hash(a['url'])))
 a['primary']='Express';a['score']=30;a['topics']=['Tecnología'];return a
