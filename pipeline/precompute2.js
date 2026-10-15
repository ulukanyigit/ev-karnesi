// node precompute2.js <key> : kış güneşi (orta kat) + deniz açısı (en üst kat), örnek bina seçimi
const fs = require('fs'), E = require('./engine.js');
const key = process.argv[2], f = `data_${key}.json`, d = JSON.parse(fs.readFileSync(f));
const e = new E(d), pre = []; const t0 = Date.now();
for (let id = 0; id < e.B.length; id++) {
  const b = d.b[id];
  const w = e.floorSun(id, e.dayProfile(id, 2026, 12, 21, 20), Math.floor((b.lv - 1) / 2));
  const s = e.floorSea(id, e.seaProfile(id), b.lv - 1);
  pre.push([Math.round(w.any * 4) / 4, s.deg]);
  if (id % 2000 === 0) console.log(id, ((Date.now() - t0) / 1000).toFixed(0) + 's');
}
d.pre = pre;
if (d.sampleAddr) d.sampleId = (d.b.find(b => b.a === d.sampleAddr) || d.b[0]).id;
else {
  const [cx, cy] = d.center;
  const cand = d.b.map((b, i) => ({ b, i, p: pre[i] })).filter(o => o.b.a && o.b.lv >= 4 && o.b.lv <= 14 && o.p[0] >= 3 && o.p[1] > 0);
  const pool = cand.length ? cand : d.b.map((b, i) => ({ b, i, p: pre[i] })).filter(o => o.b.a);
  pool.sort((a, b) => (a.b.e - b.b.e) || (Math.hypot(a.b.r[0][0] - cx, a.b.r[0][1] - cy) - Math.hypot(b.b.r[0][0] - cx, b.b.r[0][1] - cy)));
  d.sampleId = pool[0].b.id; console.log('sample', pool[0].b.a, pool[0].b.lv, pool[0].p, 'cands', cand.length);
}
fs.writeFileSync(f, JSON.stringify(d));
const ws = pre.map(p => p[0]).sort((a, b) => a - b);
console.log('done', ((Date.now() - t0) / 1000).toFixed(0) + 's', 'winter median', ws[ws.length >> 1], 'sea share', (pre.filter(p => p[1] > 0).length / pre.length).toFixed(2));
