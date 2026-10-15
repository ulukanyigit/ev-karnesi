# GitHub Pages sitesi: site/index.html + site/data/<ilçe>.json
import json, subprocess, os, sys
KEYS=sys.argv[1:] or sorted(json.load(open('prov/districts.json')).keys())
os.makedirs('site/data',exist_ok=True)
idx=[]
for k in KEYS:
    subprocess.run(['python3','compact.py',k],check=True)
    os.replace(f'dist/data/{k}.json', f'site/data/{k}.json')
    d=json.load(open(f'site/data/{k}.json'))
    mo=sum(v.get('osm',0) for v in d['mah'].values()); mt=sum(v['total'] for v in d['mah'].values() if v.get('osm'))
    idx.append(dict(key=k,name=d['name'],n=len(d['b']),cov=round(mo/mt*100) if mt else None))
import locale
idx.sort(key=lambda x: x['name'].translate(str.maketrans('ÇĞİÖŞÜÂ','CGIOSUA'))+'~')
s=open('app.html').read()
css=open('/mnt/user-data/uploads/EV KARNESİ/data/raw/maplibre-gl.css').read()
s=s.replace('/*MAPLIBRE_CSS*/',css).replace('/*ENGINE*/',open('engine.js').read())
s=s.replace('/*DATA*/','window.EVINDEX='+json.dumps(idx,ensure_ascii=False)+';')
head='<!doctype html>\n<html lang="tr">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<style>html,body{margin:0;height:100%}[hidden]{display:none!important}:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>\n'
open('site/index.html','w').write(head+s+'\n</html>\n')
open('site/.nojekyll','w').write('')
tot=sum(os.path.getsize('site/data/'+f) for f in os.listdir('site/data'))
print('site ok', len(idx),'ilçe, veri %.1f MB'%(tot/1e6), [ (x['name'],x['n']) for x in idx])
