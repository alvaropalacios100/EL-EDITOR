"""PWA assets and idempotent public-shell integration."""
from pathlib import Path
import re, shutil
ROOT=Path(__file__).resolve().parent
HEAD='''<!-- EL EDITOR PWA v1.9.0 -->
<link rel="manifest" href="/EL-EDITOR/manifest.webmanifest">
<link rel="apple-touch-icon" href="/EL-EDITOR/icon-180.png">
<meta name="theme-color" content="#f5eedc">
<script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
<script>window.OneSignalDeferred=window.OneSignalDeferred||[];
window.OneSignalDeferred.push(async function(OneSignal){
 await OneSignal.init({appId:"806d2657-187f-471e-9e5d-0a3a8583ca9c",serviceWorkerPath:"/EL-EDITOR/OneSignalSDKWorker.js",serviceWorkerParam:{scope:"/EL-EDITOR/"}});
});</script>
<style>.editor-push{display:flex;justify-content:center;align-items:center;padding:8px 0;flex-wrap:wrap;gap:8px}.editor-push .onesignal-customlink-container{max-width:100%}</style>
<!-- /EL EDITOR PWA -->'''
BUTTON='<div class="editor-push"><div class="onesignal-customlink-container"></div></div>'
def integrate(s):
    s=re.sub(r'<!-- EL EDITOR PWA v1\.9\.0 -->.*?<!-- /EL EDITOR PWA -->','',s,flags=re.S)
    s=re.sub(r'<link\b[^>]*\brel=["\'](?:manifest|apple-touch-icon)["\'][^>]*>','',s,flags=re.I)
    s=re.sub(r'<meta\b[^>]*\bname=["\']theme-color["\'][^>]*>','',s,flags=re.I)
    s=s.replace('</head>',HEAD+'\n</head>',1)
    if BUTTON not in s:
        s=s.replace('</header>',BUTTON+'</header>',1)
    return s

def publish_assets(dest):
    for name in ('manifest.webmanifest','OneSignalSDKWorker.js','OneSignalSDKUpdaterWorker.js','icon-180.png','icon-192.png','icon-512.png'):
        shutil.copy2(ROOT/name,dest/name)
