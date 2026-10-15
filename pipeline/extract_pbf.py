"""BBBike İstanbul PBF'den ilçe başına Overpass biçiminde JSON üretir: raw_pbf/<key>/{ilce,mahalle,buildings,roads,green,pois}.json"""
import osmium, json, os, sys, re, math
from shapely.geometry import LineString, Point, box
from shapely.ops import polygonize, unary_union
from shapely import STRtree
import argparse
_ap=argparse.ArgumentParser(); _ap.add_argument("--pbf",default="/mnt/user-data/uploads/EV KARNESİ/data/raw/Istanbul.osm.pbf"); _ap.add_argument("keys",nargs="*")
_args=_ap.parse_args()
PBF=_args.pbf
OUT="/home/claude/evk/raw_pbf/"
def slug(n):
    t=n.lower().translate(str.maketrans('çğıöşüâîû','cgiosuaiu')).replace('i̇','i')
    return re.sub(r'[^a-z0-9]','',t)
GREEN_RE=dict(leisure={'park','garden','playground','pitch'}, landuse={'grass','recreation_ground','cemetery','forest'}, natural={'wood','scrub','beach'})
def is_green(t): return any(t.get(k) in v for k,v in GREEN_RE.items())
def poi_ok(t):
    return (t.get('railway') in ('station','tram_stop') or t.get('station')=='subway' or t.get('public_transport')=='station' or
            t.get('amenity') in ('ferry_terminal','pharmacy','school','kindergarten','hospital','marketplace') or
            t.get('shop') in ('supermarket','bakery') or t.get('leisure')=='park')
# pass 1: relations
class R1(osmium.SimpleHandler):
    def __init__(s): super().__init__(); s.rel={}; s.need=set()
    def relation(s,r):
        t=dict(r.tags); keep=False
        if t.get('boundary')=='administrative' and t.get('admin_level') in ('6','8'): keep=True
        elif 'building' in t and t.get('type')=='multipolygon': keep=True
        elif t.get('type')=='multipolygon' and (t.get('leisure')=='park' or t.get('landuse')=='forest'): keep=True
        if keep:
            mem=[(m.ref,m.role) for m in r.members if m.type=='w']
            s.rel[r.id]=dict(tags=t,mem=mem,ts=r.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),v=r.version)
            s.need.update(m for m,_ in mem)
r1=R1(); r1.apply_file(PBF); print('relations',len(r1.rel),'member ways',len(r1.need))
# pass 2: ways + nodes with locations
class R2(osmium.SimpleHandler):
    def __init__(s,need): super().__init__(); s.need=need; s.W={}; s.B=[]; s.H=[]; s.G=[]; s.P=[]
    def node(s,n):
        if len(n.tags)==0: return
        t=dict(n.tags)
        if poi_ok(t): s.P.append(dict(type='node',id=n.id,lat=n.location.lat,lon=n.location.lon,tags=t))
    def way(s,w):
        t=dict(w.tags); geom=None
        def g():
            try: return [dict(lat=round(nd.lat,7),lon=round(nd.lon,7)) for nd in w.nodes]
            except osmium.InvalidLocationError: return None
        if w.id in s.need:
            geom=g(); 
            if geom: s.W[w.id]=geom
        if not t: return
        ts=w.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
        if 'building' in t:
            geom=geom or g()
            if geom: s.B.append(dict(type='way',id=w.id,tags=t,geometry=geom,timestamp=ts,version=w.version))
        if 'highway' in t:
            geom=geom or g()
            if geom: s.H.append(dict(type='way',id=w.id,tags=t,nodes=[nd.ref for nd in w.nodes],geometry=geom))
        if is_green(t):
            geom=geom or g()
            if geom: s.G.append(dict(type='way',id=w.id,tags=t,geometry=geom))
        if poi_ok(t):
            geom=geom or g()
            if geom:
                la=sum(p['lat'] for p in geom)/len(geom); lo=sum(p['lon'] for p in geom)/len(geom)
                s.P.append(dict(type='way',id=w.id,center=dict(lat=la,lon=lo),tags=t))
r2=R2(r1.need); r2.apply_file(PBF, locations=True); print('buildings',len(r2.B),'highways',len(r2.H),'green',len(r2.G),'pois',len(r2.P))
def relgeom(rid):
    r=r1.rel[rid]; mem=[]
    for wid,role in r['mem']:
        if wid in r2.W: mem.append(dict(type='way',ref=wid,role=role or 'outer',geometry=r2.W[wid]))
    return mem
def relpoly(rid):
    outers=[LineString([(p['lon'],p['lat']) for p in m['geometry']]) for m in relgeom(rid) if m['role']=='outer' and len(m['geometry'])>1]
    if not outers: return None
    ps=list(polygonize(unary_union(outers)))
    return unary_union(ps) if ps else None
# districts
dists={}
for rid,r in r1.rel.items():
    if r['tags'].get('admin_level')=='6' and r['tags'].get('boundary')=='administrative':
        p=relpoly(rid)
        if p is not None and p.area>0: dists[rid]=(r['tags']['name'],p)
print('districts',len(dists))
mah=[(rid,relpoly(rid)) for rid,r in r1.rel.items() if r['tags'].get('admin_level')=='8' and r['tags'].get('boundary')=='administrative']
mah=[(rid,p) for rid,p in mah if p is not None]
want=set(_args.keys)
# spatial index helpers
def cen(geom): return Point(sum(p['lon'] for p in geom)/len(geom), sum(p['lat'] for p in geom)/len(geom))
for rid,(name,poly) in dists.items():
    key=slug(name); 
    if want and key not in want: continue
    d=OUT+key+'/'; os.makedirs(d,exist_ok=True)
    b=poly.bounds; bb=box(b[0]-0.005,b[1]-0.005,b[2]+0.005,b[3]+0.005); pp=poly.buffer(0.0003)
    rel=r1.rel[rid]
    json.dump(dict(elements=[dict(type='relation',id=rid,tags=rel['tags'],members=relgeom(rid))]),open(d+'ilce.json','w'))
    json.dump(dict(elements=[dict(type='relation',id=m,tags=r1.rel[m]['tags'],members=relgeom(m)) for m,p in mah if poly.contains(p.representative_point())]),open(d+'mahalle.json','w'),ensure_ascii=False)
    els=[e for e in r2.B if pp.contains(Point(e['geometry'][0]['lon'],e['geometry'][0]['lat']))]
    for brid,r in r1.rel.items():
        if 'building' in r['tags'] and r['tags'].get('type')=='multipolygon':
            mem=relgeom(brid)
            if mem and pp.contains(Point(mem[0]['geometry'][0]['lon'],mem[0]['geometry'][0]['lat'])):
                els.append(dict(type='relation',id=brid,tags=r['tags'],members=mem,timestamp=r['ts'],version=r['v']))
    json.dump(dict(elements=els),open(d+'buildings.json','w'),ensure_ascii=False)
    json.dump(dict(elements=[e for e in r2.H if any(bb.contains(Point(p['lon'],p['lat'])) for p in e['geometry'][::4]+e['geometry'][-1:])]),open(d+'roads.json','w'),ensure_ascii=False)
    gr=[e for e in r2.G if bb.contains(cen(e['geometry']))]
    for grid,r in r1.rel.items():
        t=r['tags']
        if t.get('type')=='multipolygon' and (t.get('leisure')=='park' or t.get('landuse')=='forest'):
            mem=relgeom(grid)
            if mem and bb.contains(cen(mem[0]['geometry'])): gr.append(dict(type='relation',id=grid,tags=t,members=mem))
    json.dump(dict(elements=gr),open(d+'green.json','w'),ensure_ascii=False)
    def pc(e): return Point(e['lon'],e['lat']) if e['type']=='node' else Point(e['center']['lon'],e['center']['lat'])
    json.dump(dict(elements=[e for e in r2.P if bb.contains(pc(e))]),open(d+'pois.json','w'),ensure_ascii=False)
    print(f'{key:14s} {name:14s} bina {len(els):6d}  mahalle {sum(1 for m,p in mah if poly.contains(p.representative_point()))}')
