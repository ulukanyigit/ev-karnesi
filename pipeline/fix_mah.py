# yazım farkı yüzünden İBB ile eşleşmeyen mahalleleri harf katlamayla eşleştir, data_<key>.json'a ekle
import json, csv, io, re, sys, collections
import numpy as np
RAW="/mnt/user-data/uploads/EV KARNESİ/data/raw/"
def rd(fn): return list(csv.DictReader(io.StringIO(open(RAW+fn,'rb').read().decode('cp1254')), delimiter=';'))
DEP=rd('ibb_deprem_senaryo.csv'); BIN=rd('ibb_mahalle_bina.csv')
def fold(s): return re.sub(r'[^A-Z0-9]','', s.replace('i','İ').replace('ı','I').upper().translate(str.maketrans('ÇĞİÖŞÜÂÎÛ','CGIOSUAIU')))
fixed=0
for key in json.load(open('prov/districts.json')):
    f=f'data_{key}.json'; d=json.load(open(f))
    il=d['name'].replace('â','a').replace('i','İ').replace('ı','I').upper(); il='EYÜP' if il=='EYÜPSULTAN' else il
    dep={fold(r['mahalle_adi']):r for r in DEP if r['ilce_adi']==il}; bina={fold(r['mahalle_adi']):r for r in BIN if r['ilce_adi']==il}
    cnt=collections.Counter(b.get('m') for b in d['b'])
    ch=False
    for name in [m for m in cnt if m and m not in d['mah']]:
        k=fold(name)
        def fz(D):
            if k in D: return D[k]
            c=[x for x in D if len(x)>=4 and (k.startswith(x) or x.startswith(k))]
            return D[c[0]] if len(c)==1 else None
        dr=fz(dep); br=fz(bina)
        if not dr or not br: print('  hâlâ yok:',key,name); continue
        tot=sum(int(br[x]) for x in ['1980_oncesi','1980-2000_arasi','2000_sonrasi'])
        heavy=int(dr['cok_agir_hasarli_bina_sayisi'])+int(dr['agir_hasarli_bina_sayisi'])
        d['mah'][name]=dict(total=tot, pre80=int(br['1980_oncesi']), y80_00=int(br['1980-2000_arasi']), post00=int(br['2000_sonrasi']), heavy=heavy,
            medium=int(dr['orta_hasarli_bina_sayisi']), ratio=round(heavy/tot*100,2) if tot else 0, pctile=None, shelter=int(dr['gecici_barinma']), osm=cnt[name])
        ch=True; fixed+=1; print('  eşlendi:',key,name,'->',dr['mahalle_adi'])
    if ch: json.dump(d,open(f,'w'))
print('düzeltilen',fixed)
