# adm6.geojson'dan İstanbul ilçelerini bul, her biri için osmium extract + extract_pbf.py çalıştır
import json, subprocess, re, sys, os
ALL=['Adalar','Arnavutköy','Ataşehir','Avcılar','Bağcılar','Bahçelievler','Bakırköy','Başakşehir','Bayrampaşa','Beşiktaş','Beykoz','Beylikdüzü','Beyoğlu','Büyükçekmece','Çatalca','Çekmeköy','Esenler','Esenyurt','Eyüpsultan','Fatih','Gaziosmanpaşa','Güngören','Kadıköy','Kağıthane','Kartal','Küçükçekmece','Maltepe','Pendik','Sancaktepe','Sarıyer','Silivri','Sultanbeyli','Sultangazi','Şile','Şişli','Tuzla','Ümraniye','Üsküdar','Zeytinburnu']
def slug(n):
    t=n.lower().translate(str.maketrans('çğıöşüâîû','cgiosuaiu')).replace('i̇','i')
    return re.sub(r'[^a-z0-9]','',t)
want={slug(n):n for n in ALL}
g=json.load(open('prov/adm6.geojson'))
found={}
for f in g['features']:
    n=f['properties'].get('name'); k=slug(n or '')
    if k in want and k not in found:
        cs=[c for poly in (f['geometry']['coordinates'] if f['geometry']['type']=='MultiPolygon' else [f['geometry']['coordinates']]) for ring in poly for c in ring]
        xs=[c[0] for c in cs]; ys=[c[1] for c in cs]
        found[k]=(n,(min(xs)-0.012,min(ys)-0.012,max(xs)+0.012,max(ys)+0.012))
print('bulunan',len(found),'eksik',[want[k] for k in want if k not in found])
json.dump({k:dict(name=v[0],bbox=v[1]) for k,v in found.items()},open('prov/districts.json','w'),ensure_ascii=False)
keys=sys.argv[1:] or sorted(found)
for k in keys:
    n,bb=found[k]
    subprocess.run(['osmium','extract','-b',','.join(f'{x:.4f}' for x in bb),'prov/ist.osm.pbf','-o',f'prov/{k}.osm.pbf','--overwrite','-s','smart'],check=True,capture_output=True)
    r=subprocess.run(['python3','extract_pbf.py','--pbf',f'prov/{k}.osm.pbf',k],capture_output=True,text=True)
    print((r.stdout.strip().splitlines() or ['?'])[-1], r.stderr[-300:] if r.returncode else '', flush=True)
# coastline -> Overpass biçimi
c=json.load(open('prov/coast.geojson'))
els=[dict(type='way',geometry=[dict(lat=round(y,7),lon=round(x,7)) for x,y in f['geometry']['coordinates']]) for f in c['features'] if f['geometry']['type']=='LineString']
json.dump(dict(elements=els),open('prov/coastline_prov.json','w')); print('kıyı parçaları',len(els))
