# data_<key>.json -> dist/data/<key>.json (yürüme adları tabloya, DEM gerekirse 2x seyreltme)
import json, sys, numpy as np, os
key=sys.argv[1]; d=json.load(open(f'data_{key}.json'))
WK=['rail','ferry','tram','market','pharmacy','school','park','hospital']
names=[]; ni={}
for b in d['b']:
    arr=[]
    for k in WK:
        v=b['w'].get(k)
        if v is None: arr+= [-1,-1]; continue
        n=v[1]
        if n not in ni: ni[n]=len(names); names.append(n)
        arr+=[int(round(v[0]*10)), ni[n]]
    b['w']=arr
    for f in ('nm','nr','a','m','y'):
        if b.get(f) is None: b.pop(f,None)
d['wk']=WK; d['names']=names
dm=d['dem']
if dm['w']*dm['h']>300000:
    a=np.array(dm['v'],dtype=float).reshape(dm['h'],dm['w']); h2,w2=dm['h']//2,dm['w']//2
    a=a[:h2*2,:w2*2].reshape(h2,2,w2,2).mean(axis=(1,3))
    upd=dict(w=w2,h=h2,step=dm['step']*2,v=[int(round(x)) for x in a.ravel()])
    if 's' in dm:
        sm=np.array(dm['s'],dtype=float).reshape(dm['h'],dm['w'])[:h2*2,:w2*2].reshape(h2,2,w2,2).max(axis=(1,3)); upd['s']=[int(round(x)) for x in sm.ravel()]
    dm.update(upd)
os.makedirs('dist/data',exist_ok=True)
s=json.dumps(d,ensure_ascii=False,separators=(',',':')); open(f'dist/data/{key}.json','w').write(s); print(key,'%.2f MB'%(len(s)/1e6))
