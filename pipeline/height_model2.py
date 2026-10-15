"""Şehir geneli kat sayısı modeli. python height_model2.py key1 key2 ...
Her ilçe için ham bina + GBA okur, tüm etiketli binalarla tek rastgele orman eğitir.
İlçe bazında komşu-ortanca (kNN) ile karşılaştırıp daha iyi olanı seçer -> lv_pred_<key>.json"""
import json, numpy as np, re, math, sys, os
from scipy.spatial import cKDTree
from shapely.geometry import Polygon
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold
RAW='/home/claude/evk/raw_pbf/'
GBA={int(k):v for k,v in json.load(open('/mnt/user-data/uploads/EV KARNESİ/data/raw/gba_city.json')).items()}
KEYS=sys.argv[1:]
TY=['apartments','house','residential','industrial','commercial','retail','detached','office','school','yes']
allX=[]; ally=[]; meta=[]
per={}
for key in KEYS:
    R=RAW+key+'/'
    g=GBA
    B=json.load(open(R+'buildings.json'))['elements']
    rows=[]
    for e in B:
        if 'geometry' not in e: continue
        t=e.get('tags',{}); lv=None
        try: lv=float(re.findall(r'[\d.]+',t.get('building:levels',''))[0])
        except: pass
        if lv is not None and (lv<=0 or lv>60): lv=None
        lat0=e['geometry'][0]['lat']; KX=111320*math.cos(math.radians(lat0)); KY=110574
        xy=np.array([[p['lon']*KX,p['lat']*KY] for p in e['geometry']])
        if len(xy)<4: continue
        pl=Polygon(xy)
        if not pl.is_valid: pl=pl.buffer(0)
        if pl.is_empty: continue
        rows.append(dict(id=e['id'],lv=lv,gba=g.get(e['id'],np.nan),area=pl.area,per=pl.length,c=xy.mean(0),typ=t.get('building','yes'),nv=len(xy)))
    C=np.array([r['c'] for r in rows]); T=cKDTree(C)
    gba=np.array([r['gba'] for r in rows]); area=np.array([r['area'] for r in rows])
    lvs=np.array([r['lv'] if r['lv'] else np.nan for r in rows])
    X=[]
    for i,r in enumerate(rows):
        idx=T.query_ball_point(r['c'],100); gg=gba[idx]; gg=gg[np.isfinite(gg)]
        idx70=[j for j in T.query_ball_point(r['c'],70) if j!=i]; kv=lvs[idx70]; kv=kv[np.isfinite(kv)]
        X.append([r['gba'], math.log1p(r['area']), r['per']/math.sqrt(max(r['area'],1)),
                  np.nanmean(gg) if len(gg) else np.nan, np.nanmax(gg) if len(gg) else np.nan, len(idx), float(np.mean(area[idx])),
                  r['nv'], np.median(kv) if len(kv) else np.nan, len(kv), *[1.0 if r['typ']==t else 0.0 for t in TY]])
    X=np.nan_to_num(np.array(X),nan=-1)
    lab=np.where(np.isfinite(lvs))[0]
    per[key]=dict(rows=rows,X=X,lab=lab,y=lvs[lab])
    print(f'{key:12s} bina {len(rows):6d}  etiketli {len(lab):5d} (%{len(lab)/len(rows)*100:.1f})  GBA %{np.isfinite(gba).mean()*100:.0f}')
# stacked training set
Xall=np.vstack([per[k]['X'][per[k]['lab']] for k in KEYS]); yall=np.concatenate([per[k]['y'] for k in KEYS])
dist=np.concatenate([[k]*len(per[k]['lab']) for k in KEYS])
pr=np.zeros(len(yall))
for tr,te in KFold(5,shuffle=True,random_state=0).split(Xall):
    pr[te]=RandomForestRegressor(300,min_samples_leaf=2,n_jobs=-1,random_state=0).fit(Xall[tr],yall[tr]).predict(Xall[te])
model=RandomForestRegressor(300,min_samples_leaf=2,n_jobs=-1,random_state=0).fit(Xall,yall)
def stats(e): return dict(exact=round(float(np.mean(e==0))*100), pm1=round(float(np.mean(np.abs(e)<=1))*100), mae=round(float(np.abs(e).mean()),2))
print('\nilçe        n     RF(MAE ±1)     kNN(MAE ±1)   seçilen')
for k in KEYS:
    m=dist==k; y=yall[m]
    if m.sum()<20:
        method='rf'; s_rf=stats(np.clip(np.round(pr[m]),1,None)-y) if m.sum() else dict(exact=0,pm1=0,mae=0); s_kn=None
    else:
        s_rf=stats(np.clip(np.round(pr[m]),1,None)-y)
        knf=Xall[m][:,8]; kn=np.where(knf>0, knf, np.median(yall))
        s_kn=stats(np.clip(np.round(kn),1,None)-y)
        method='knn' if s_kn['mae']<s_rf['mae'] else 'rf'
    print(f"{k:10s} {m.sum():5d}   {s_rf['mae']:5.2f} %{s_rf['pm1']:3d}     " + (f"{s_kn['mae']:5.2f} %{s_kn['pm1']:3d}" if s_kn else '   -      ') + f"     {method}")
    P=per[k]
    if method=='rf':
        pred=np.clip(np.round(model.predict(P['X'])),1,60).astype(int)
        acc=dict(note='Kat sayısı kayıtlı olmayan binalarda; uydu yüksekliği (GlobalBuildingAtlas), taban alanı, bina tipi, çevre dokusu ve komşu kayıtlardan eğitilen bir rastgele orman modeli kullanıldı.', n=int(m.sum()), **s_rf)
    else:
        f=P['X'][:,8]; pred=np.clip(np.round(np.where(f>0,f,np.round(model.predict(P['X'])))),1,60).astype(int)
        acc=dict(note='Kat sayısı kayıtlı olmayan binalarda 70 m içindeki komşu kayıtların ortancası, komşu kaydı yoksa rastgele orman modeli kullanıldı.', n=int(m.sum()), **s_kn)
    json.dump(dict(pred={str(r['id']):int(pred[i]) for i,r in enumerate(P['rows'])}, acc=acc, method=method), open(f'lv_pred_{k}.json','w'))
