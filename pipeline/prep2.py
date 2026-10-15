"""Ev Karnesi — ilçe veri hazırlığı.  python prep2.py kadikoy|umraniye"""
import json, math, re, sys, csv, io, numpy as np, tifffile
from shapely.geometry import Polygon, Point, LineString, box, shape
from shapely.ops import unary_union, polygonize, linemerge
from shapely import STRtree
from scipy.spatial import cKDTree
from scipy import ndimage
import networkx as nx
RAW = "/mnt/user-data/uploads/EV KARNESİ/data/raw/"
RAWP = "/home/claude/evk/raw_pbf/"
CFG = {
 'kadikoy': dict(name='Kadıköy', ilce='KADIKÖY', raw=RAWP+'kadikoy/', seaBB=None, seaRange=9000, rail={}, sample='Moda Caddesi No: 120-128',
   places=None, landmarks='city', coast=RAW+'coastline_city.json'),
 'umraniye': dict(name='Ümraniye', ilce='ÜMRANİYE', raw=RAWP+'umraniye/', seaBB=None, coast=RAW+'coastline_city.json', seaRange=9000, rail={}, sample=None, places=None,
   landmarks=[dict(name='Büyük Çamlıca Camii',lon=29.07031,lat=41.03443,z=330),dict(name='15 Temmuz Şehitler Köprüsü',lon=29.03433,lat=41.04546,z=165),
     dict(name='Fatih Sultan Mehmet Köprüsü',lon=29.06117,lat=41.09130,z=105),dict(name='Kız Kulesi',lon=29.00406,lat=41.02111,z=30),
     dict(name='Galata Kulesi',lon=28.97421,lat=41.02563,z=100),dict(name='Tarihi Yarımada',lon=28.98018,lat=41.00857,z=90)]),
}
CITY_LM=[dict(name='Kız Kulesi',lon=29.00406,lat=41.02111,z=30),dict(name='Galata Kulesi',lon=28.97421,lat=41.02563,z=100),
  dict(name='Tarihi Yarımada',lon=28.98018,lat=41.00857,z=90),dict(name='Süleymaniye',lon=28.96401,lat=41.01606,z=105),
  dict(name='15 Temmuz Şehitler Köprüsü',lon=29.03433,lat=41.04546,z=165),dict(name='Fatih Sultan Mehmet Köprüsü',lon=29.06117,lat=41.09130,z=105),
  dict(name='Büyük Çamlıca Camii',lon=29.07031,lat=41.03443,z=330),dict(name='Haydarpaşa Garı',lon=29.01917,lat=40.99657,z=40),
  dict(name='Dolmabahçe Sarayı',lon=29.0005,lat=41.0392,z=25),dict(name='Adalar',lon=29.05,lat=40.9097,z=110),dict(name='Fenerbahçe Feneri',lon=29.03647,lat=40.96942,z=20)]
NAMES={'kadikoy':'Kadıköy','umraniye':'Ümraniye','besiktas':'Beşiktaş','sisli':'Şişli','beyoglu':'Beyoğlu','fatih':'Fatih','uskudar':'Üsküdar','atasehir':'Ataşehir','bakirkoy':'Bakırköy','maltepe':'Maltepe'}
key = sys.argv[1]
if key not in CFG:
    CFG[key]=dict(name=NAMES[key], ilce=None, raw=RAWP+key+'/', seaBB=None, seaRange=9000, rail={}, sample=None, places=None, landmarks='city', coast=RAW+'coastline_city.json')
C = CFG[key]; R = C['raw']
if C['ilce'] is None: C['ilce']=C['name'].replace('i','İ').replace('ı','I').upper()
def tr_up(s): return s.replace('i','İ').replace('ı','I').upper()

# ---------- district boundary / center ----------
ilce_poly = None
try:
    el = [e for e in json.load(open(R+'ilce.json'))['elements'] if e['tags'].get('name')==C['name'] and e['tags'].get('admin_level')=='6'][0]
    outers=[LineString([(p['lon'],p['lat']) for p in m['geometry']]) for m in el['members'] if m['type']=='way' and m['role']=='outer']
    ilce_poly = unary_union(list(polygonize(unary_union(outers))))
except FileNotFoundError: pass
if 'center' not in C:
    c = ilce_poly.centroid; C['center'] = (round(c.x,4), round(c.y,4))
    b = ilce_poly.bounds; C['bounds'] = [[b[0]-0.01, b[1]-0.01],[b[2]+0.01, b[3]+0.01]]
if C['seaBB'] is None:
    b = ilce_poly.bounds; C['seaBB'] = (b[0]-0.09, b[1]-0.07, b[2]+0.09, b[3]+0.07)
LON0, LAT0 = C['center']
KX = 111320*math.cos(math.radians(LAT0)); KY = 110574
def P(lon,lat): return ((lon-LON0)*KX, (lat-LAT0)*KY)
def INV(x,y): return (LON0+x/KX, LAT0+y/KY)

# ---------- DEM ----------
import os as _os
if C['seaBB'] is None:
    b_ = ilce_poly.bounds; C['seaBB'] = (b_[0]-0.09, b_[1]-0.07, b_[2]+0.09, b_[3]+0.07)
_dp = R+"dem_cop30.tif" if _os.path.exists(R+"dem_cop30.tif") else RAW+"dem_city.tif"
t=tifffile.TiffFile(_dp); dem=t.pages[0].asarray().astype(float)
sc=t.pages[0].tags['ModelPixelScaleTag'].value; tp=t.pages[0].tags['ModelTiepointTag'].value
dlon0, dlat0, dstep = tp[3], tp[4], sc[0]
if _dp.endswith('dem_city.tif'):
    W_,S_,E_,N_ = C['seaBB']
    c0=max(0,int((W_-dlon0)/dstep)); c1=min(dem.shape[1],int((E_-dlon0)/dstep)+1)
    r0=max(0,int((dlat0-N_)/dstep)); r1=min(dem.shape[0],int((dlat0-S_)/dstep)+1)
    dem=dem[r0:r1,c0:c1]; dlon0=dlon0+c0*dstep; dlat0=dlat0-r0*dstep
dem[~np.isfinite(dem)] = 0
g = np.clip(ndimage.gaussian_filter(ndimage.minimum_filter(dem, size=3), 1.0), 0, None)
dsm = np.clip(ndimage.gaussian_filter(dem, 0.5), 0, None)  # binalar/ağaçlar dahil yüzey (uzak engeller için)
def ground(lon,lat):
    c=(lon-dlon0)/dstep-0.5; r=(dlat0-lat)/dstep-0.5
    c0=int(np.clip(np.floor(c),0,g.shape[1]-2)); r0=int(np.clip(np.floor(r),0,g.shape[0]-2))
    fc=np.clip(c-c0,0,1); fr=np.clip(r-r0,0,1)
    return float(g[r0,c0]*(1-fc)*(1-fr)+g[r0,c0+1]*fc*(1-fr)+g[r0+1,c0]*(1-fc)*fr+g[r0+1,c0+1]*fc*fr)

# ---------- sea ----------
cst=json.load(open(C.get('coast', R+"coastline.json")))['elements']
bb=box(*C['seaBB'])
cst=[e for e in cst if any(bb.intersects(Point(p['lon'],p['lat'])) for p in e['geometry'][::5]+e['geometry'][-1:])] if C.get('coast') else cst
merged=linemerge([LineString([(p['lon'],p['lat']) for p in e['geometry']]) for e in cst])
segs=list(merged.geoms) if hasattr(merged,'geoms') else [merged]
polys=list(polygonize(unary_union([bb.boundary]+[s.intersection(bb) for s in segs])))
seaP=[];landP=[]
for s in segs:
    cs=np.array(s.coords)
    for i in range(0,len(cs)-1,2):
        a,b2=cs[i],cs[i+1]; d=b2-a; n=np.hypot(*d)
        if n==0: continue
        m=(a+b2)/2; r=np.array([d[1],-d[0]])/n*0.00015
        seaP.append(Point(m+r)); landP.append(Point(m-r))
st=STRtree(seaP); lt=STRtree(landP); out=[]
for p in polys:
    ns=len(st.query(p,predicate='contains')); nl=len(lt.query(p,predicate='contains'))
    if ns>nl: out.append(p)
sea=unary_union(out).simplify(0.00005)
seaGeoms = list(sea.geoms) if hasattr(sea,'geoms') else [sea]
print('sea pieces',len(seaGeoms),'area km2 %.1f'%(sea.area*KX*KY/1e6))

# ---------- mahalle + İBB stats ----------
mh=json.load(open(R+"mahalle.json"))['elements']; mpolys=[]
for e in mh:
    outers=[LineString([(p['lon'],p['lat']) for p in m['geometry']]) for m in e['members'] if m['type']=='way' and m['role']=='outer']
    ps=list(polygonize(unary_union(outers)))
    if ps: mpolys.append((e['tags']['name'].replace(' Mahallesi',''), unary_union(ps)))
if ilce_poly is not None: mpolys=[(n,p) for n,p in mpolys if ilce_poly.buffer(-0.0005).intersects(p.representative_point())]
mtree=STRtree([p for _,p in mpolys])
def rd(fn):
    return list(csv.DictReader(io.StringIO(open(RAW+fn,'rb').read().decode('cp1254')), delimiter=';'))
dep={r['mahalle_adi']:r for r in rd('ibb_deprem_senaryo.csv') if r['ilce_adi']==C['ilce']}
bina={r['mahalle_adi']:r for r in rd('ibb_mahalle_bina.csv') if r['ilce_adi']==C['ilce']}
alld=rd('ibb_deprem_senaryo.csv'); allb={(r['ilce_adi'],r['mahalle_adi']):r for r in rd('ibb_mahalle_bina.csv')}
ratios=[]
for r in alld:
    b=allb.get((r['ilce_adi'],r['mahalle_adi']))
    if not b: continue
    tot=sum(int(b[k] or 0) for k in ['1980_oncesi','1980-2000_arasi','2000_sonrasi'])
    if tot>50: ratios.append((int(r['cok_agir_hasarli_bina_sayisi'])+int(r['agir_hasarli_bina_sayisi']))/tot)
ratios=np.array(ratios)
def norm(s): return re.sub(r'[^A-ZÇĞİÖŞÜ0-9]','',tr_up(s))
depN={norm(k):v for k,v in dep.items()}; binaN={norm(k):v for k,v in bina.items()}
mstats={}
for name,_ in mpolys:
    k=norm(name)
    def fz(D):  # ör. '19 Mayıs' ~ '19.May'
        if k in D: return D[k]
        c=[x for x in D if len(x)>=4 and (k.startswith(x) or x.startswith(k))]
        return D[c[0]] if len(c)==1 else None
    d=fz(depN); b=fz(binaN)
    if not d or not b: print('  İBB eşleşmedi:',name); continue
    tot=sum(int(b[x]) for x in ['1980_oncesi','1980-2000_arasi','2000_sonrasi'])
    heavy=int(d['cok_agir_hasarli_bina_sayisi'])+int(d['agir_hasarli_bina_sayisi']); ratio=heavy/tot
    mstats[name]=dict(total=tot, pre80=int(b['1980_oncesi']), y80_00=int(b['1980-2000_arasi']), post00=int(b['2000_sonrasi']),
        heavy=heavy, medium=int(d['orta_hasarli_bina_sayisi']), ratio=round(ratio*100,2), pctile=round(float((ratios<ratio).mean()*100)), shelter=int(d['gecici_barinma']))

# ---------- buildings ----------
B=json.load(open(R+"buildings.json"))['elements']
SKIP={'roof','garage','garages','shed','kiosk','hut','toilets','construction','carport','greenhouse','ruins','transformer_tower'}
blds=[]
for e in B:
    t=e.get('tags',{})
    if e['type']=='way':
        if 'geometry' not in e: continue
        ring=[(p['lon'],p['lat']) for p in e['geometry']]
    else:
        outs=[m for m in e.get('members',[]) if m.get('role')=='outer' and m.get('geometry')]
        if not outs: continue
        ps=list(polygonize(unary_union([LineString([(p['lon'],p['lat']) for p in m['geometry']]) for m in outs])))
        if not ps: continue
        ring=list(max(ps,key=lambda p:p.area).exterior.coords)
    if len(ring)<4: continue
    if ilce_poly is not None and not ilce_poly.contains(Point(ring[0])): continue
    pl=Polygon([P(*c) for c in ring])
    if not pl.is_valid: pl=pl.buffer(0)
    if pl.is_empty or pl.area<8: continue
    if pl.geom_type!='Polygon': pl=max(pl.geoms,key=lambda p:p.area)
    pl=pl.simplify(0.3)
    lv=h=None
    try: lv=float(re.findall(r'[\d.]+',t.get('building:levels',''))[0])
    except: pass
    try: h=float(re.findall(r'[\d.]+',t.get('height',''))[0])
    except: pass
    if lv is not None and lv<=0: lv=None
    blds.append(dict(id=e['id'],poly=pl,t=t,lv=lv,h=h,ts=e.get('timestamp')))
print('buildings',len(blds))
cent=np.array([[b['poly'].centroid.x,b['poly'].centroid.y] for b in blds])
known=[i for i,b in enumerate(blds) if b['lv'] or b['h']]
kl=np.array([blds[i]['lv'] if blds[i]['lv'] else max(1,round((blds[i]['h']-0.8)/3.0)) for i in known])
kt=cKDTree(cent[known])
for i,b in enumerate(blds):
    if b['lv'] or b['h']:
        b['levels']=int(round(b['lv'])) if b['lv'] else max(1,round((b['h']-0.8)/3.0)); b['est']=0
        b['height']=b['h'] if b['h'] else b['levels']*3.0+0.8; continue
    a=b['poly'].area; typ=b['t'].get('building'); idx=kt.query_ball_point(cent[i],70)
    if typ in ('roof','kiosk','shed','garage','garages','hut','toilets'): lev=1
    elif a<45: lev=2
    elif len(idx)>=3: lev=int(np.median(kl[idx]))
    elif typ=='apartments' or a>120: lev=5
    else: lev=3
    if a<45: lev=min(lev,2)
    b['levels']=max(1,lev); b['est']=1; b['height']=b['levels']*3.0+0.8
    if typ=='roof': b['height']=4.0
print('kat etiketi oranı %.0f%%'%(100*(1-np.mean([b['est'] for b in blds]))))
import os
MODEL=None
if os.path.exists(f'lv_pred_{key}.json'):
    MODEL=json.load(open(f'lv_pred_{key}.json'))
    for b in blds:
        if b['est']==1 and b['t'].get('building') not in ('roof',):
            p_=MODEL['pred'].get(str(b['id']))
            if p_: b['levels']=p_; b['height']=p_*3.0+0.8
# leave-one-out accuracy of the kNN estimate on known buildings
loo=[]
for j,i in enumerate(known):
    idx=[k for k in kt.query_ball_point(cent[i],70) if k!=j]
    loo.append((int(np.median(kl[idx])) if len(idx)>=3 else 5)-kl[j])
loo=np.array(loo); acc=MODEL['acc'] if MODEL else dict(note='Kat sayısı kayıtlı olmayan binalarda 70 m içindeki komşu binaların ortancası kullanıldı.', n=len(loo), exact=round(float(np.mean(loo==0))*100), pm1=round(float(np.mean(np.abs(loo)<=1))*100), mae=round(float(np.abs(loo).mean()),2))
print('kNN doğruluk',acc)
# OSM count per mahalle (coverage vs MAKS)
for b in blds:
    if b['t'].get('building') in SKIP: continue
    lon,lat=INV(*cent[blds.index(b)]) if False else INV(b['poly'].centroid.x,b['poly'].centroid.y)
    for j in mtree.query(Point(lon,lat)):
        if mpolys[j][1].contains(Point(lon,lat)):
            n=mpolys[j][0]
            if n in mstats: mstats[n]['osm']=mstats[n].get('osm',0)+1
            break

# ---------- roads & walk graph ----------
Rd=json.load(open(R+"roads.json"))['elements']
G=nx.Graph(); roads_out=[]; named=[]
skip={'motorway','motorway_link','trunk_link','construction','proposed','raceway','bus_guideway'}
for e in Rd:
    t=e['tags']; hw=t.get('highway')
    if 'geometry' not in e: continue
    pts=[P(p['lon'],p['lat']) for p in e['geometry']]; nodes=e['nodes']
    cls='major' if hw in ('primary','secondary','tertiary','trunk','motorway','primary_link','secondary_link','tertiary_link','trunk_link','motorway_link') else ('minor' if hw in ('residential','unclassified','living_street','service') else 'path')
    if not (hw=='service' and t.get('service') in ('parking_aisle','driveway')) and hw not in ('construction','proposed'):
        ls=LineString([(p['lon'],p['lat']) for p in e['geometry']]).simplify(0.00001)
        roads_out.append(dict(c=cls, g=[(round(a,6),round(b2,6)) for a,b2 in ls.coords]))
    if t.get('name') and hw not in ('footway','steps','path','service','cycleway'): named.append((LineString(pts),t['name']))
    if hw in skip or t.get('access') in ('private','no') or t.get('foot')=='no': continue
    for a,b2,pa,pb in zip(nodes[:-1],nodes[1:],pts[:-1],pts[1:]):
        G.add_edge(a,b2,w=math.dist(pa,pb)*(1.15 if hw=='steps' else 1.0)); G.nodes[a]['xy']=pa; G.nodes[b2]['xy']=pb
G=G.subgraph(max(nx.connected_components(G),key=len)).copy()
nid=list(G.nodes); nxy=np.array([G.nodes[n]['xy'] for n in nid]); ntree=cKDTree(nxy)
nameTree=STRtree([l for l,_ in named]); print('graph nodes',len(nid))

# ---------- POIs ----------
Pz=json.load(open(R+"pois.json"))['elements']
def ll(e): return (e['lon'],e['lat']) if 'lon' in e else (e['center']['lon'],e['center']['lat'])
cats={k:[] for k in ['rail','ferry','tram','market','pharmacy','school','hospital','park']}
for e in Pz:
    t=e['tags']; n=t.get('name'); xy=P(*ll(e))
    is_rail = t.get('railway')=='station' or t.get('station')=='subway' or (t.get('public_transport')=='station' and t.get('subway')=='yes')
    if is_rail and n and 'Haydarpaşa' not in n:
        if C['rail']:
            if n in C['rail']: cats['rail'].append((xy,C['rail'][n]))
        else: cats['rail'].append((xy, n if any(w in n for w in ('Metro','İstasyon','Garı')) else n + ' istasyonu'))
    elif t.get('amenity')=='ferry_terminal':
        nm=(n or 'İskele').split(' - ')[0].strip()
        cats['ferry'].append((xy, nm if 'skele' in nm or 'Terminal' in nm else nm+' İskelesi'))
    elif t.get('railway')=='tram_stop':
        cats['tram'].append((xy,'T3 '+(n or 'tramvay durağı') if key=='kadikoy' else (n or 'Tramvay durağı')+' tramvay durağı'))
    elif t.get('shop') in ('supermarket','bakery'): cats['market'].append((xy,n or ('Market' if t['shop']=='supermarket' else 'Fırın')))
    elif t.get('amenity')=='pharmacy': cats['pharmacy'].append((xy,n or 'Eczane'))
    elif t.get('amenity') in ('school','kindergarten'): cats['school'].append((xy,n or 'Okul'))
    elif t.get('amenity')=='hospital': cats['hospital'].append((xy,n or 'Hastane'))
Gr=json.load(open(R+"green.json"))['elements']; green_out=[]
for e in Gr:
    t=e['tags']; kind=t.get('leisure') or t.get('landuse') or t.get('natural'); geoms=[]
    if e['type']=='way' and e.get('geometry'): geoms=[[(p['lon'],p['lat']) for p in e['geometry']]]
    elif e['type']=='relation': geoms=[[(p['lon'],p['lat']) for p in m['geometry']] for m in e['members'] if m.get('role')=='outer' and m.get('geometry')]
    for gm in geoms:
        if len(gm)<4: continue
        ls=LineString(gm).simplify(0.00001)
        green_out.append(dict(k=kind,g=[(round(a,6),round(b2,6)) for a,b2 in ls.coords]))
        if kind in ('park','garden','recreation_ground'):
            pl=Polygon([P(*c) for c in gm])
            if pl.is_valid and pl.area>1500:
                nm=t.get('name')
                for c in list(pl.exterior.coords)[::3]: cats['park'].append((c, nm if nm and 'Belediye' not in nm else 'Park'))
print({k:len(v) for k,v in cats.items()})
walk={}
for k,items in cats.items():
    if not items: continue
    src={}
    for xy,nm in items:
        d,j=ntree.query(xy)
        if d>250: continue
        n=nid[j]
        if n not in src or d<src[n][0]: src[n]=(d,nm)
    if not src: continue
    H=G.copy(); H.add_node('S')
    for n,(d,nm) in src.items(): H.add_edge('S',n,w=d)
    dist,paths=nx.single_source_dijkstra(H,'S',weight='w', cutoff=4000)
    walk[k]=(dist,paths,src)

# ---------- assemble ----------
out=[]
for b in blds:
    pl=b['poly']; c=pl.centroid; lon,lat=INV(c.x,c.y); t=b['t']
    addr=None
    if t.get('addr:street') and t.get('addr:housenumber'): addr=f"{t['addr:street']} No: {t['addr:housenumber']}"
    elif t.get('addr:street'): addr=t['addr:street']
    near=None
    if not addr and named: near=named[nameTree.nearest(c)][1]
    mah=None
    for j in mtree.query(Point(lon,lat)):
        if mpolys[j][1].contains(Point(lon,lat)): mah=mpolys[j][0]; break
    d,j=ntree.query((c.x,c.y)); n=nid[j]; w={}
    for k,(dist,paths,src) in walk.items():
        if n in dist: w[k]=[round((dist[n]+d)/80.0,1), src[paths[n][1]][1]]
    ring=[[round(a,6),round(bb2,6)] for a,bb2 in (INV(x,y) for x,y in pl.exterior.coords)]
    out.append(dict(id=b['id'], r=ring, lv=b['levels'], h=round(b['height'],1), e=b['est'], g=round(ground(lon,lat),1),
        a=addr, nr=near, nm=t.get('name'), m=mah, w=w, y=int(b['ts'][:4]) if b['ts'] else None))
if False:  # (eski) Kadıköy ham binaları meta içermiyordu: önceki meta analizinden al
    old=json.load(open('data.json')); oy={x['id']:x.get('y') for x in old['b']}
    for o in out: o['y']=oy.get(o['id'])
    for n,s_ in mstats.items():
        if n in old['mah'] and 'osm' in old['mah'][n]: s_['osm']=old['mah'][n]['osm']
gx=dict(lon0=dlon0, lat0=dlat0, step=dstep, w=g.shape[1], h=g.shape[0], v=[int(round(v*10)) for v in g.ravel()], s=[int(round(v*10)) for v in dsm.ravel()])
seaj=[[[round(a,5),round(bb2,5)] for a,bb2 in p.exterior.coords] for p in seaGeoms]
# landmarks
lm=C['landmarks']
if lm=='city':
    lm=[l for l in CITY_LM if math.dist(P(l['lon'],l['lat']),(0,0))<15000]
if lm is None:
    lm=[]; Z={'Çamlıca Kulesi':600,'Çamlıca Camii':330,'15 Temmuz Şehitler Köprüsü':165,'Fatih Sultan Mehmet Köprüsü':105,'Kız Kulesi':30,'Galata Kulesi':100}
    seen=set()
    import os
    for e in (json.load(open(R+'landmarks.json'))['elements'] if os.path.exists(R+'landmarks.json') else []):
        n=e['tags'].get('name'); key2=next((k for k in Z if n and k in n),None)
        if not key2 or key2 in seen: continue
        seen.add(key2); lo,la=ll(e); lm.append(dict(name=key2.replace('Büyük ',''),lon=round(lo,5),lat=round(la,5),z=Z[key2]))
# places: biggest mahalles, spread out
pl_=C['places']
if pl_ is None:
    cnts={n:s.get('osm',0) for n,s in mstats.items()}; pl_=[]
    for n,p in sorted(mpolys,key=lambda x:-cnts.get(x[0],0)):
        c=p.representative_point()
        if all(math.dist(P(c.x,c.y),P(q[1],q[2]))>1300 for q in pl_): pl_.append([n,round(c.x,5),round(c.y,5)])
        if len(pl_)>=9: break
border=[]
if ilce_poly is not None:
    for pg in (ilce_poly.geoms if hasattr(ilce_poly,'geoms') else [ilce_poly]):
        border.append([[round(x,5),round(y,5)] for x,y in pg.simplify(0.00008).exterior.coords])
data=dict(border=border, key=key, name=C['name'], center=[LON0,LAT0], bounds=C['bounds'], view=C.get('view'), seaRange=C['seaRange'],
   b=out, roads=roads_out, green=green_out, sea=seaj, dem=gx, mah=mstats, ist_median=round(float(np.median(ratios)*100),2),
   stations=[dict(xy=[round(v,6) for v in INV(*xy)],n=nm,k=k) for k in ('rail','ferry') for xy,nm in cats[k]],
   landmarks=lm, places=pl_, acc=acc, sampleAddr=C['sample'])
s=json.dumps(data,ensure_ascii=False,separators=(',',':'))
open(f'data_{key}.json','w').write(s); print('size MB %.2f'%(len(s)/1e6), 'landmarks',[l['name'] for l in lm])
