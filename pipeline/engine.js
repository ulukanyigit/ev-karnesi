// Ev Karnesi hesap motoru — güneş, gölge, deniz manzarası, simge görüş hattı
// Yerel metrik düzlem (eşdikdörtgen, merkez etrafında ~2 km için < 0.1% hata)
(function (root) {
  const D2R = Math.PI / 180, R2D = 180 / Math.PI;
  const FLOOR_H = 3.0, WIN_Z = 1.5, PARTY = 0.7, OFF = 0.6;

  function Engine(data) {
    const [lon0, lat0] = data.center;
    this.lon0 = lon0; this.lat0 = lat0;
    this.kx = 111320 * Math.cos(lat0 * D2R); this.ky = 110574;
    // DEM
    const d = data.dem; this.dem = d; this.demv = Float32Array.from(d.v, v => v / 10); this.dsmv = d.s ? Float32Array.from(d.s, v => v / 10) : null;
    // buildings
    this.B = data.b.map((b, i) => {
      const xs = [], ys = [];
      for (const [lo, la] of b.r) { const p = this.P(lo, la); xs.push(p[0]); ys.push(p[1]); }
      if (xs.length > 1 && xs[0] === xs[xs.length - 1] && ys[0] === ys[ys.length - 1]) { xs.pop(); ys.pop(); }
      let A = 0; for (let k = 0; k < xs.length; k++) { const j = (k + 1) % xs.length; A += xs[k] * ys[j] - xs[j] * ys[k]; }
      let minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
      for (let k = 0; k < xs.length; k++) { minx = Math.min(minx, xs[k]); maxx = Math.max(maxx, xs[k]); miny = Math.min(miny, ys[k]); maxy = Math.max(maxy, ys[k]); }
      return { i, xs, ys, ccw: A > 0, area: Math.abs(A) / 2, minx, miny, maxx, maxy, g: b.g, h: b.h, lv: b.lv, top: b.g + b.h };
    });
    this.maxTop = Math.max(...this.B.map(b => b.top));
    this.cell = 40;
    this.grid = new Map();
    for (const b of this.B) this._ins(this.grid, b.minx, b.miny, b.maxx, b.maxy, b.i);
    this.stamp = new Int32Array(this.B.length); this.sid = 1;
    // sea
    this.SE = []; this.seaGrid = new Map();
    for (const ring of data.sea) {
      const pts = ring.map(([lo, la]) => this.P(lo, la));
      for (let k = 0; k < pts.length - 1; k++) {
        const a = pts[k], c = pts[k + 1], id = this.SE.length;
        this.SE.push([a[0], a[1], c[0], c[1]]);
        this._ins(this.seaGrid, Math.min(a[0], c[0]), Math.min(a[1], c[1]), Math.max(a[0], c[0]), Math.max(a[1], c[1]), id);
      }
    }
    this.seaRings = data.sea.map(r => r.map(([lo, la]) => this.P(lo, la)));
    this.seaRange = data.seaRange || 4000;
  }
  const E = Engine.prototype;
  E.P = function (lon, lat) { return [(lon - this.lon0) * this.kx, (lat - this.lat0) * this.ky]; };
  E.INV = function (x, y) { return [this.lon0 + x / this.kx, this.lat0 + y / this.ky]; };
  E._key = (cx, cy) => cx * 100003 + cy;
  E._ins = function (grid, x0, y0, x1, y1, id) {
    const c = this.cell;
    for (let cx = Math.floor(x0 / c); cx <= Math.floor(x1 / c); cx++)
      for (let cy = Math.floor(y0 / c); cy <= Math.floor(y1 / c); cy++) {
        const k = this._key(cx, cy); let a = grid.get(k); if (!a) grid.set(k, a = []); a.push(id);
      }
  };
  E.ground = function (x, y) {
    const [lon, lat] = this.INV(x, y), d = this.dem;
    let c = (lon - d.lon0) / d.step - 0.5, r = (d.lat0 - lat) / d.step - 0.5;
    if (c < 0 || r < 0 || c > d.w - 1 || r > d.h - 1) return 0;
    const c0 = Math.min(d.w - 2, Math.floor(c)), r0 = Math.min(d.h - 2, Math.floor(r)), fc = c - c0, fr = r - r0, v = this.demv, w = d.w;
    return v[r0 * w + c0] * (1 - fc) * (1 - fr) + v[r0 * w + c0 + 1] * fc * (1 - fr) + v[(r0 + 1) * w + c0] * (1 - fc) * fr + v[(r0 + 1) * w + c0 + 1] * fc * fr;
  };
  // uzak engel yüzeyi: DSM (binalar dahil) + dünya eğriliği/kırılma düzeltmesi; yakında (<80 m) çıplak arazi
  const CURV = 0.87 / 12742000;
  E.farSurf = function (x, y, t) {
    let v = this.ground(x, y);
    if (this.dsmv && t > 80) { const s = this._sample(this.dsmv, x, y); if (s > v) v = s; }
    return v - t * t * CURV;
  };
  E._sample = function (arr, x, y) {
    const [lon, lat] = this.INV(x, y), d = this.dem;
    let c = (lon - d.lon0) / d.step - 0.5, r = (d.lat0 - lat) / d.step - 0.5;
    if (c < 0 || r < 0 || c > d.w - 1 || r > d.h - 1) return 0;
    const c0 = Math.min(d.w - 2, Math.floor(c)), r0 = Math.min(d.h - 2, Math.floor(r)), fc = c - c0, fr = r - r0, w = d.w;
    return arr[r0 * w + c0] * (1 - fc) * (1 - fr) + arr[r0 * w + c0 + 1] * fc * (1 - fr) + arr[(r0 + 1) * w + c0] * (1 - fc) * fr + arr[(r0 + 1) * w + c0 + 1] * fc * fr;
  };
  E.inside = function (b, x, y) {
    if (x < b.minx || x > b.maxx || y < b.miny || y > b.maxy) return false;
    let ins = false; const xs = b.xs, ys = b.ys, n = xs.length;
    for (let i = 0, j = n - 1; i < n; j = i++) {
      if ((ys[i] > y) !== (ys[j] > y) && x < (xs[j] - xs[i]) * (y - ys[i]) / (ys[j] - ys[i]) + xs[i]) ins = !ins;
    }
    return ins;
  };
  E.buildingAt = function (x, y, except) {
    const a = this.grid.get(this._key(Math.floor(x / this.cell), Math.floor(y / this.cell)));
    if (!a) return -1;
    for (const id of a) if (id !== except && this.inside(this.B[id], x, y)) return id;
    return -1;
  };
  // DDA over grid cells along ray; calls fn(cellArray, tEnter, tExit) in order; fn returns true to stop
  E._walk = function (grid, ox, oy, ux, uy, L, fn) {
    const c = this.cell;
    let cx = Math.floor(ox / c), cy = Math.floor(oy / c);
    const sx = ux > 0 ? 1 : -1, sy = uy > 0 ? 1 : -1;
    const tdx = ux !== 0 ? Math.abs(c / ux) : Infinity, tdy = uy !== 0 ? Math.abs(c / uy) : Infinity;
    let tmx = ux !== 0 ? (((ux > 0 ? cx + 1 : cx) * c - ox) / ux) : Infinity;
    let tmy = uy !== 0 ? (((uy > 0 ? cy + 1 : cy) * c - oy) / uy) : Infinity;
    let t0 = 0;
    while (t0 <= L) {
      const t1 = Math.min(tmx, tmy);
      const a = grid.get(this._key(cx, cy));
      if (a && fn(a, t0, Math.min(t1, L))) return;
      if (tmx < tmy) { cx += sx; t0 = tmx; tmx += tdx; } else { cy += sy; t0 = tmy; tmy += tdy; }
    }
  };
  function segHit(ox, oy, ux, uy, ax, ay, bx, by) {
    const ex = bx - ax, ey = by - ay, den = ux * ey - uy * ex;
    if (Math.abs(den) < 1e-12) return Infinity;
    const wx = ax - ox, wy = ay - oy;
    const t = (wx * ey - wy * ex) / den, s = (wx * uy - wy * ux) / den;
    return (s >= 0 && s <= 1 && t > 0.05) ? t : Infinity;
  }
  E.entry = function (b, ox, oy, ux, uy) {
    let tm = Infinity; const xs = b.xs, ys = b.ys, n = xs.length;
    for (let k = 0; k < n; k++) { const j = (k + 1) % n; const t = segHit(ox, oy, ux, uy, xs[k], ys[k], xs[j], ys[j]); if (t < tm) tm = t; }
    return tm;
  };
  // obstacles along ray: calls cb(t, top) for each building entered (unordered across a cell), up to L
  E._obstacles = function (ox, oy, ux, uy, L, cb) {
    const st = ++this.sid;
    this._walk(this.grid, ox, oy, ux, uy, L, (a) => {
      let stop = false;
      for (const id of a) {
        if (this.stamp[id] === st) continue; this.stamp[id] = st;
        const b = this.B[id], t = this.entry(b, ox, oy, ux, uy);
        if (t <= L && cb(t, b.top) === true) stop = true;
      }
      return stop;
    });
  };
  E.firstSea = function (ox, oy, ux, uy, L) {
    let best = Infinity;
    this._walk(this.seaGrid, ox, oy, ux, uy, L, (a, t0, t1) => {
      for (const id of a) { const s = this.SE[id]; const t = segHit(ox, oy, ux, uy, s[0], s[1], s[2], s[3]); if (t < best) best = t; }
      return best <= t1 + 1e-6;
    });
    return best;
  };
  E.inSea = function (x, y) {
    let ins = false;
    for (const r of this.seaRings) {
      for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
        if ((r[i][1] > y) !== (r[j][1] > y) && x < (r[j][0] - r[i][0]) * (y - r[i][1]) / (r[j][1] - r[i][1]) + r[i][0]) ins = !ins;
      }
    }
    return ins;
  };

  // --- sun position (UTC ms) ---
  function sunPos(ms, lat, lon) {
    const d = ms / 86400000 - 10957.5;
    const g = (357.529 + 0.98560028 * d) * D2R;
    const q = 280.459 + 0.98564736 * d;
    const L = (q + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g)) * D2R;
    const e = (23.439 - 0.00000036 * d) * D2R;
    const RA = Math.atan2(Math.cos(e) * Math.sin(L), Math.cos(L));
    const dec = Math.asin(Math.sin(e) * Math.sin(L));
    let gmst = (18.697374558 + 24.06570982441908 * d) % 24; if (gmst < 0) gmst += 24;
    const H = (gmst * 15 + lon) * D2R - RA;
    const la = lat * D2R;
    const alt = Math.asin(Math.sin(la) * Math.sin(dec) + Math.cos(la) * Math.cos(dec) * Math.cos(H));
    let az = Math.atan2(Math.sin(H), Math.cos(H) * Math.sin(la) - Math.tan(dec) * Math.cos(la)) * R2D + 180;
    az = ((az % 360) + 360) % 360;
    return { alt: alt * R2D, az };
  }
  Engine.sunPos = sunPos;
  E.sun = function (ms) { return sunPos(ms, this.lat0, this.lon0); };
  // Türkiye UTC+3 sabit
  Engine.localMs = (y, m, d, hh, mm) => Date.UTC(y, m - 1, d, hh - 3, mm || 0);

  // --- facades ---
  E.facades = function (id) {
    const b = this.B[id], xs = b.xs, ys = b.ys, n = xs.length, out = [];
    for (let k = 0; k < n; k++) {
      const j = (k + 1) % n, dx = xs[j] - xs[k], dy = ys[j] - ys[k], len = Math.hypot(dx, dy);
      if (len < 2.5) continue;
      let nx = dy / len, ny = -dx / len; if (!b.ccw) { nx = -nx; ny = -ny; }
      const mx = (xs[k] + xs[j]) / 2, my = (ys[k] + ys[j]) / 2;
      // party wall: outward point inside another building
      const party = this.buildingAt(mx + nx * PARTY, my + ny * PARTY, id) >= 0;
      if (party) continue;
      const az = ((Math.atan2(nx, ny) * R2D) + 360) % 360;
      out.push({ x: mx + nx * OFF, y: my + ny * OFF, nx, ny, len, az });
    }
    return out;
  };
  E.floorZ = function (id, k) { return this.B[id].g + WIN_Z + k * FLOOR_H; };

  // shadow line: absolute height above which point (x,y) gets direct sun
  E.shadowLine = function (x, y, sun) {
    const a = sun.az * D2R, ux = Math.sin(a), uy = Math.cos(a), ta = Math.tan(sun.alt * D2R);
    const L = Math.min(900, (this.maxTop + 5) / Math.max(ta, 0.02));
    let S = -Infinity;
    this._obstacles(x, y, ux, uy, L, (t, top) => { const v = top - t * ta; if (v > S) S = v; });
    for (let t = 10; t <= L; t += 15) { const v = this.ground(x + ux * t, y + uy * t) - t * ta; if (v > S) S = v; }
    return S;
  };

  // per-facade, per-time shadow lines for a day; step minutes
  E.dayProfile = function (id, y, m, d, step = 15) {
    const F = this.facades(id), times = [];
    for (let mins = 4 * 60; mins <= 21 * 60; mins += step) {
      const ms = Engine.localMs(y, m, d, Math.floor(mins / 60), mins % 60), s = this.sun(ms);
      if (s.alt > 2) times.push({ mins, s });
    }
    const S = F.map(f => times.map(({ s }) => {
      const a = s.az * D2R, dot = f.nx * Math.sin(a) + f.ny * Math.cos(a);
      if (dot < 0.08) return Infinity; // cephe güneşe dönük değil
      return this.shadowLine(f.x, f.y, s);
    }));
    return { F, times, S, step, sunrise: times.length ? times[0].mins : null, sunset: times.length ? times[times.length - 1].mins : null };
  };
  // hours of sun for floor k on each facade + best
  E.floorSun = function (id, prof, k) {
    const z = this.floorZ(id, k), h = prof.step / 60;
    const per = prof.F.map((f, i) => {
      let c = 0, first = null, last = null;
      prof.S[i].forEach((S, j) => { if (z > S) { c++; if (first === null) first = prof.times[j].mins; last = prof.times[j].mins; } });
      return { az: f.az, len: f.len, hours: c * h, first, last };
    });
    let best = per.reduce((a, b) => (b.hours > (a ? a.hours : -1) ? b : a), null);
    // any facade lit: union over time
    let anyC = 0;
    prof.times.forEach((_, j) => { if (prof.S.some((col, i) => z > col[j])) anyC++; });
    return { per, best, any: anyC * h };
  };

  // sea view rays: for each facade, rays in ±78° every 2°; returns per-ray required eye height
  // cap: bu yüksekliği aşan engel bulununca ışın kesilir (hiçbir kat göremez)
  E.seaProfile = function (id) {
    const F = this.facades(id), rays = [], range = this.seaRange, cap = this.B[id].top + 1;
    for (const f of F) {
      for (let da = -78; da <= 78; da += 2) {
        const az = (f.az + da + 360) % 360, a = az * D2R, ux = Math.sin(a), uy = Math.cos(a);
        const ts = this.firstSea(f.x, f.y, ux, uy, range);
        if (!isFinite(ts)) continue;
        let M = 0, step = ts > 3000 ? 30 : 15;
        for (let t = 10; t < ts; t += step) { const g = this.farSurf(f.x + ux * t, f.y + uy * t, t); if (g > M) { M = g; if (M > cap) break; } }
        if (M > cap) continue;
        this._obstacles(f.x, f.y, ux, uy, ts, (t, top) => { top -= t * t * CURV; if (top > M) M = top; return M > cap; });
        if (M > cap) continue;
        rays.push({ az: Math.round(az / 2) * 2, need: M, dist: ts });
      }
    }
    return rays;
  };
  E.floorSea = function (id, rays, k) {
    const z = this.floorZ(id, k), bins = new Set();
    let near = Infinity;
    for (const r of rays) if (z > r.need + 0.3) { bins.add(r.az); if (r.dist < near) near = r.dist; }
    const arr = [...bins].sort((a, b) => a - b);
    // main direction: circular mean
    let sx = 0, sy = 0; for (const a of arr) { sx += Math.sin(a * D2R); sy += Math.cos(a * D2R); }
    const dir = arr.length ? ((Math.atan2(sx, sy) * R2D) + 360) % 360 : null;
    return { deg: arr.length * 2, bins: arr, dir, near: isFinite(near) ? near : null };
  };
  // landmark line-of-sight
  E.landmarks = function (id, k, list) {
    const F = this.facades(id), z = this.floorZ(id, k), out = [];
    for (const L of list) {
      const [lx, ly] = this.P(L.lon, L.lat);
      let ok = false, dist = null;
      for (const f of F) {
        const dx = lx - f.x, dy = ly - f.y, D = Math.hypot(dx, dy), ux = dx / D, uy = dy / D;
        if (f.nx * ux + f.ny * uy < 0.2) continue;
        const slope = (L.z - z) / D; let blocked = false;
        for (let t = 10; t < D - 30; t += (D > 3000 ? 30 : 15)) { if (this.farSurf(f.x + ux * t, f.y + uy * t, t) > z + slope * t) { blocked = true; break; } }
        if (!blocked) this._obstacles(f.x, f.y, ux, uy, D - 30, (t, top) => { if (top - t * t * CURV > z + slope * t) blocked = true; return blocked; });
        if (!blocked) { ok = true; dist = D; break; }
      }
      if (ok) out.push({ name: L.name, dist });
    }
    return out;
  };

  // ground shadow hull for map (lon/lat ring)
  E.shadowHull = function (id, sun) {
    const b = this.B[id];
    if (sun.alt <= 0.5) return null;
    const len = Math.min(400, b.h / Math.tan(sun.alt * D2R)), a = sun.az * D2R;
    const vx = -Math.sin(a) * len, vy = -Math.cos(a) * len;
    const pts = [];
    for (let k = 0; k < b.xs.length; k++) { pts.push([b.xs[k], b.ys[k]]); pts.push([b.xs[k] + vx, b.ys[k] + vy]); }
    pts.sort((p, q) => p[0] - q[0] || p[1] - q[1]);
    const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const lo = [], up = [];
    for (const p of pts) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], p) <= 0) lo.pop(); lo.push(p); }
    for (let i = pts.length - 1; i >= 0; i--) { const p = pts[i]; while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], p) <= 0) up.pop(); up.push(p); }
    const hull = lo.slice(0, -1).concat(up.slice(0, -1)); hull.push(hull[0]);
    return hull.map(([x, y]) => this.INV(x, y));
  };

  root.EvEngine = Engine;
  if (typeof module !== 'undefined') module.exports = Engine;
})(typeof window !== 'undefined' ? window : globalThis);
