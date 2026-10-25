// ---------- Térkép ----------
// A tarkov.dev interaktív térképeit használjuk ugyanazzal a koordináta-átszámítással, mint az oldaluk,
// így a quest-zónák és -tárgyak pontosan a helyükre kerülnek.
const TKMap = (() => {
  const NS = 'http://www.w3.org/2000/svg';
  let lmap = null, cfg = null, svgEl = null, floorLayer = null, markerGroup = null, extractGroup = null;
  let curFloor = null, buildSeq = 0, focusObj = null, raidOpen = false;
  const markersByObj = {};
  const svgMem = {};

  const pos = p => [p.z, p.x];
  const llb = b => L.latLngBounds([b[0][1], b[0][0]], [b[1][1], b[1][0]]);
  const inB = (p, b) => {
    const xs = [b[0][0], b[1][0]], zs = [b[0][1], b[1][1]];
    return p.x >= Math.min(...xs) && p.x <= Math.max(...xs) && p.z >= Math.min(...zs) && p.z <= Math.max(...zs);
  };

  function rotate(ll, rot) {
    if (!ll.lng && !ll.lat) return L.latLng(0, 0);
    if (!rot) return ll;
    const a = rot * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
    return L.latLng(ll.lng * s + ll.lat * c, ll.lng * c - ll.lat * s);
  }
  function makeCRS(m) {
    const [sx, mx, sy, my] = m.transform || [1, 0, 1, 0];
    const rot = m.coordinateRotation || 0;
    return L.extend({}, L.CRS.Simple, {
      transformation: new L.Transformation(sx, mx, -sy, my),
      projection: L.extend({}, L.Projection.LonLat, {
        project: ll => L.Projection.LonLat.project(rotate(ll, rot)),
        unproject: p => rotate(L.Projection.LonLat.unproject(p), -rot),
      }),
    });
  }
  // A tarkov.dev getScaledBounds függvénye (a kihúzható terület a pálya 1,5-szerese).
  function scaledBounds(b, f) {
    const cx = (b[0][0] + b[1][0]) / 2, cy = (b[0][1] + b[1][1]) / 2;
    const w = (b[1][0] - b[0][0]) * f, h = (b[1][1] - b[0][1]) * f;
    return [[cy - h / 2, cx - w / 2], [cy + h / 2, cx + w / 2]];
  }
  function floorOf(m, p) {
    if (!p || p.y == null) return null;
    for (const l of m.layers || []) {
      for (const e of l.extents || []) {
        if (!e.height || p.y < e.height[0] || p.y >= e.height[1]) continue;
        if (e.bounds && !e.bounds.some(b => inB(p, b))) continue;
        return l;
      }
    }
    return null;
  }

  // Az SVG-t a GitHubról töltjük (ott engedélyezett a CORS), végső esetben a tarkov.dev-ről,
  // és eltesszük, hogy net nélkül is megjelenjen.
  async function fetchSvg(url) {
    if (svgMem[url]) return svgMem[url];
    let store = null;
    try { store = await caches.open('tarkov-maps'); } catch (e) {}
    const urls = [url.replace('https://assets.tarkov.dev/maps/svg', 'https://raw.githubusercontent.com/the-hideout/tarkov-dev-svg-maps/main'), url];
    for (const u of urls) {
      try {
        const r = await fetch(u);
        if (!r.ok) continue;
        let t = await r.text();
        // Az app natív hálózatkezelése a képeket base64-ben adhatja vissza.
        if (!t.includes('<svg')) { try { t = decodeURIComponent(escape(atob(t.trim()))); } catch (e) {} }
        if (!t.includes('<svg')) continue;
        if (store) store.put(url, new Response(t, { headers: { 'Content-Type': 'image/svg+xml' } })).catch(() => {});
        return (svgMem[url] = t);
      } catch (e) {}
    }
    if (store) {
      try { const r = await store.match(url); if (r) return (svgMem[url] = await r.text()); } catch (e) {}
    }
    return null;
  }

  function tileOpts(m, bounds) {
    return { tileSize: m.tileSize || 256, bounds, minZoom: -5, maxZoom: Math.max(7, m.maxZoom || 6), minNativeZoom: m.minZoom || 0, maxNativeZoom: m.maxZoom || 6 };
  }

  function apiIds(m, apiMaps) {
    return new Set(apiMaps.filter(a => a.normalizedName === m.key || (m.altMaps || []).includes(a.normalizedName)).map(a => a.id));
  }
  function mapName(m, apiMaps) {
    const a = apiMaps.find(a => a.normalizedName === m.key);
    return a ? a.name : m.key;
  }

  // ---- Emeletek ----
  function setFloor(layer) {
    curFloor = layer || null;
    if (floorLayer) { floorLayer.remove(); floorLayer = null; }
    if (svgEl) {
      svgEl.querySelectorAll('.overlay-layer').forEach(g => g.classList.add('hidden-layer'));
      svgEl.classList.toggle('off-level', !!curFloor);
    }
    if (curFloor) {
      const groups = (svgEl && curFloor.svgLayer)
        ? [...svgEl.querySelectorAll('.overlay-layer')].filter(g => g.id === curFloor.svgLayer || g.dataset.keepWithGroup === curFloor.svgLayer)
        : [];
      if (groups.length) groups.forEach(g => g.classList.remove('hidden-layer'));
      else if (curFloor.tilePath) floorLayer = L.tileLayer(curFloor.tilePath, tileOpts(cfg, llb(cfg.bounds))).addTo(lmap);
    }
    renderFloorChips();
  }
  function renderFloorChips() {
    const box = document.getElementById('floorChips');
    const layers = (cfg && cfg.layers) || [];
    box.hidden = !layers.length;
    box.innerHTML = layers.length ? `<button class="chip ${!curFloor ? 'on' : ''}" data-floor="-1">🏠 Alap</button>` +
      layers.map((l, i) => `<button class="chip ${curFloor === l ? 'on' : ''}" data-floor="${i}">${esc(l.name)}</button>`).join('') : '';
  }

  // ---- Jelölők ----
  const OBJ_ICON = { plantItem: '📥', plantQuestItem: '📥', mark: '📡', visit: '👣', findQuestItem: '📦', giveQuestItem: '📦', useItem: '🔧', extract: '🚪' };
  function markerIcon(emoji, cls) {
    return L.divIcon({ className: '', html: `<div class="mk ${cls}">${emoji}</div>`, iconSize: [30, 30], iconAnchor: [15, 15], popupAnchor: [0, -14] });
  }
  function wantTask(t, st) {
    if (focusObj && focusObj.taskId === t.id) return true;
    if (st === 'done' || st === 'other') return false;
    if (S.mapFilter === 'tracked') return !!S.tracked[t.id];
    if (S.mapFilter === 'avail') return st === 'available';
    return true;
  }
  function popupHtml(t, o, what, p) {
    const fl = floorOf(cfg, p);
    const done = objIsDone(t, o);
    return `<div class="pop">
      <b>${esc(t.name)}</b> <span class="small">${esc(t.trader.name)}</span>
      <div style="margin-top:4px">${esc(o.description)}</div>
      ${what ? `<div class="small" style="margin-top:4px">${what}</div>` : ''}
      ${fl ? `<div class="small">🏢 Szint: ${esc(fl.name)}</div>` : ''}
      <div class="row" style="margin-top:8px;gap:6px">
        <button class="btn" data-mobj="${o.id}" data-mtask="${t.id}">${done ? '↩️ Mégsem kész' : '✅ Cél kész'}</button>
        <button class="btn" data-mq="${t.id}">📋 Quest</button>
      </div></div>`;
  }
  function addObjMarker(group, t, o, p, emoji, cls, what, ids) {
    const m = L.marker(pos(p), { icon: markerIcon(emoji, cls), riseOnHover: true });
    m.bindPopup(() => popupHtml(t, o, what, p), { maxWidth: 260 });
    m.on('click', () => { const fl = floorOf(cfg, p); if (fl !== curFloor && fl) setFloor(fl); });
    m.addTo(group);
    (markersByObj[o.id] = markersByObj[o.id] || []).push(m);
  }

  function renderMarkers(data) {
    const { tasks, states, geo, apiMaps } = data;
    Object.keys(markersByObj).forEach(k => delete markersByObj[k]);
    if (markerGroup) markerGroup.remove();
    markerGroup = L.layerGroup().addTo(lmap);
    const ids = apiIds(cfg, apiMaps);
    let count = 0, tasksShown = new Set();
    for (const t of tasks) {
      const st = states[t.id].state;
      if (!wantTask(t, st)) continue;
      for (const o of t.objectives) {
        const g = geo[o.id];
        if (!g) continue;
        if (objIsDone(t, o) && !(focusObj && focusObj.objId === o.id)) continue;
        const cls = 'mk-' + st + (S.tracked[t.id] ? ' mk-tracked' : '');
        const items = (g.markerItem ? [g.markerItem] : []).concat(g.questItem ? [g.questItem] : [], g.useAny || [], o.items || []);
        const itemTxt = items.length ? items.slice(0, 4).map(i => esc(i.shortName || i.name)).join(', ') + (items.length > 4 ? '…' : '') : '';
        for (const z of g.zones || []) {
          if (!z.position || !ids.has(z.map && z.map.id) || !inB(z.position, cfg.bounds)) continue;
          if (z.outline && z.outline.length > 2) {
            L.polygon(z.outline.map(pos), { color: S.tracked[t.id] ? '#ffd24a' : '#e5e200', weight: 1.5, fillOpacity: .18, interactive: false }).addTo(markerGroup);
          }
          const label = o.type === 'mark' ? '📡 Marker: ' : (o.type.startsWith('plant') ? '📥 Ide rakd le: ' : '🔧 Tárgy: ');
          addObjMarker(markerGroup, t, o, z.position, OBJ_ICON[o.type] || '🎯', cls, itemTxt ? label + itemTxt : '🎯 Célzóna', ids);
          count++; tasksShown.add(t.id);
        }
        for (const loc of g.possibleLocations || []) {
          if (!ids.has(loc.map && loc.map.id)) continue;
          for (const p of loc.positions || []) {
            if (!inB(p, cfg.bounds)) continue;
            addObjMarker(markerGroup, t, o, p, '📦', cls, '📦 Itt lehet a questtárgy: ' + esc(g.questItem ? g.questItem.name : ''), ids);
            count++; tasksShown.add(t.id);
          }
        }
      }
    }
    const info = document.getElementById('mapInfo');
    const filt = { tracked: 'követett', avail: 'elérhető', all: 'nem kész' }[S.mapFilter];
    info.innerHTML = count
      ? `${count} jelölő · ${tasksShown.size} ${filt} quest · koppints egy jelölőre a részletekért`
      : (S.mapFilter === 'tracked' && !Object.keys(S.tracked).length
        ? 'Még nem követsz questet. A Questek fülön a ☆ gombbal jelöld ki, amelyiket csinálod.'
        : `Ezen a pályán nincs térképes cél a(z) ${filt} questjeidhez.`);
  }

  function renderExtracts(apiMaps) {
    if (extractGroup) { extractGroup.remove(); extractGroup = null; }
    if (!S.showExtracts) return;
    extractGroup = L.layerGroup().addTo(lmap);
    const ids = apiIds(cfg, apiMaps);
    const am = apiMaps.find(a => ids.has(a.id) && a.normalizedName === cfg.key) || apiMaps.find(a => ids.has(a.id));
    if (!am) return;
    const COL = { pmc: '#7cc36a', scav: '#5fb3e8', shared: '#e8b24a' };
    const FN = { pmc: 'PMC', scav: 'Scav', shared: 'közös' };
    for (const e of am.extracts || []) {
      if (!e.position) continue;
      L.circleMarker(pos(e.position), { radius: 8, color: '#111', weight: 2, fillColor: COL[e.faction] || '#ccc', fillOpacity: .95 })
        .bindPopup(`🚪 <b>${esc(e.name)}</b><div class="small">${FN[e.faction] || esc(e.faction || '')} kijárat</div>`).addTo(extractGroup);
    }
    for (const tr of am.transits || []) {
      if (!tr.position) continue;
      L.circleMarker(pos(tr.position), { radius: 8, color: '#111', weight: 2, fillColor: '#b58cf0', fillOpacity: .95 })
        .bindPopup(`🔁 <b>${esc(tr.description || 'Átjáró')}</b><div class="small">transit</div>`).addTo(extractGroup);
    }
  }

  // ---- Raid terv ----
  function renderRaid(data) {
    const out = document.getElementById('raidOut');
    if (!raidOpen) { out.innerHTML = ''; return; }
    const { tasks, states, geo, apiMaps } = data;
    const ids = apiIds(cfg, apiMaps);
    const onMap = (t, o) => (o.maps || []).some(m => ids.has(m.id)) ||
      ((geo[o.id] || {}).zones || []).some(z => z.map && ids.has(z.map.id)) ||
      ((geo[o.id] || {}).possibleLocations || []).some(l => l.map && ids.has(l.map.id));
    const list = [], keys = {}, bring = {};
    for (const t of tasks) {
      if (states[t.id].state !== 'available') continue;
      const objs = t.objectives.filter(o => !objIsDone(t, o) && (onMap(t, o) || (t.map && ids.has(t.map.id) && !(o.maps || []).length)));
      if (!objs.length) continue;
      list.push({ t, objs });
      for (const k of t.neededKeys || []) {
        if (!k.map || !ids.has(k.map.id)) continue;
        for (const it of k.keys || []) (keys[it.id] = keys[it.id] || { it, tasks: new Set() }).tasks.add(t.name);
      }
      for (const o of objs) {
        const g = geo[o.id] || {};
        const add = (it, n) => { const b = bring[it.id] = bring[it.id] || { it, n: 0, tasks: new Set() }; b.n += n; b.tasks.add(t.name); };
        if (o.type === 'plantItem' && o.items && o.items.length) add(o.items[0], o.count || 1);
        if (o.type === 'mark' && g.markerItem) add(g.markerItem, 1);
        if (o.type === 'plantQuestItem' && g.questItem) add(g.questItem, 1);
        if (o.type === 'useItem' && g.useAny && g.useAny.length) add(g.useAny[0], o.count || 1);
      }
    }
    list.sort((a, b) => (S.tracked[b.t.id] ? 1 : 0) - (S.tracked[a.t.id] ? 1 : 0) || a.t.name.localeCompare(b.t.name));
    const keyList = Object.values(keys), bringList = Object.values(bring);
    out.innerHTML = `
      <div class="card"><b>🎒 Raid terv – ${esc(mapName(cfg, apiMaps))}</b>
        <div class="small">${list.length} elérhető quest csinálható itt${S.level ? ` (${S.level}. szinttel)` : ''}.</div></div>
      ${bringList.length ? `<div class="card"><div class="small" style="margin-bottom:4px">🧳 Vidd magaddal (lerakás / marker)</div>
        ${bringList.map(b => `<div class="need-list"><div class="r"><span>${esc(b.it.name)}<br><span class="small">${esc([...b.tasks].join(', '))}</span></span><b>×${b.n}</b></div></div>`).join('')}</div>` : ''}
      ${keyList.length ? `<div class="card"><div class="small" style="margin-bottom:4px">🔑 Kellhet ez a kulcs</div>
        ${keyList.map(k => `<div class="need-list"><div class="r"><span>${esc(k.it.name)}</span><span class="small">${esc([...k.tasks].join(', '))}</span></div></div>`).join('')}</div>` : ''}
      <div class="card">${list.length ? list.map(({ t, objs }) => `
        <div class="task">
          <b>${S.tracked[t.id] ? '⭐ ' : ''}${esc(t.name)}</b> <span class="small">${esc(t.trader.name)}</span>
          <ul>${objs.map(o => `<li>${esc(o.description)}${o.count > 1 ? ` <b>${Math.min(S.objCount[o.id] || 0, o.count)}/${o.count}</b>` : ''}${markersByObj[o.id] ? ` <button class="pin" data-rfocus="${o.id}">📍</button>` : ''}</li>`).join('')}</ul>
        </div>`).join('') : '<p class="small">Ezen a pályán most nincs elérhető questcélod.</p>'}</div>`;
  }

  // ---- Felépítés ----
  async function load() {
    const [tasks, geo, apiMaps] = await Promise.all([loadTasks(), loadTaskGeo().catch(() => ({})), loadMaps()]);
    return { tasks, geo, apiMaps, states: computeStates(tasks) };
  }

  async function render() {
    const status = document.getElementById('mapInfo');
    let data;
    try { data = await load(); } catch (e) { status.innerHTML = errHtml(e); return; }
    const sel = document.getElementById('mapSel');
    const opts = MAP_CONFIGS.map(m => ({ key: m.key, name: mapName(m, data.apiMaps) })).sort((a, b) => a.name.localeCompare(b.name));
    if (!MAP_CONFIGS.some(m => m.key === S.mapKey)) S.mapKey = 'customs';
    sel.innerHTML = opts.map(o => `<option value="${esc(o.key)}" ${o.key === S.mapKey ? 'selected' : ''}>${esc(o.name)}</option>`).join('');
    document.querySelectorAll('[data-mf]').forEach(c => c.classList.toggle('on', c.dataset.mf === S.mapFilter));
    document.getElementById('extractChip').classList.toggle('on', !!S.showExtracts);
    document.getElementById('raidChip').classList.toggle('on', raidOpen);

    if (!lmap || !cfg || cfg.key !== S.mapKey) await build(S.mapKey);
    else lmap.invalidateSize();
    if (!lmap) return;
    renderMarkers(data);
    renderExtracts(data.apiMaps);
    renderRaid(data);
    if (focusObj) {
      const ms = markersByObj[focusObj.objId] || [];
      if (ms.length) {
        const b = L.latLngBounds(ms.map(m => m.getLatLng()));
        lmap.fitBounds(b.pad(0.6), { maxZoom: Math.min(lmap.getMaxZoom(), (cfg.maxZoom || 6) - 1) });
        const fl = floorOf(cfg, focusObj.p);
        if (fl) setFloor(fl);
        setTimeout(() => ms[0].openPopup(), 350);
      }
      focusObj = null;
    }
  }

  async function build(key) {
    const seq = ++buildSeq;
    cfg = MAP_CONFIGS.find(m => m.key === key);
    if (lmap) { lmap.remove(); lmap = null; }
    svgEl = null; floorLayer = null; curFloor = null; markerGroup = null; extractGroup = null;
    const box = document.getElementById('mapBox');
    const bounds = llb(cfg.bounds);
    lmap = L.map(box, {
      crs: makeCRS(cfg), zoomSnap: 0.25, zoomDelta: 0.5, minZoom: -5, maxZoom: Math.max(7, cfg.maxZoom || 6),
      maxBounds: scaledBounds(cfg.bounds, 1.5), maxBoundsViscosity: 0.7, attributionControl: true,
    });
    lmap.attributionControl.setPrefix(false).addAttribution('Térkép: <a href="https://tarkov.dev" target="_blank" rel="noopener">tarkov.dev</a>');
    lmap.fitBounds(bounds);
    lmap.setMinZoom(Math.min(cfg.minZoom || 1, lmap.getZoom() - 0.5));
    lmap.on('popupopen', e => {
      const el = e.popup.getElement();
      if (el) el.addEventListener('click', onPopupClick);
    });
    renderFloorChips();

    if (cfg.svgPath) {
      document.getElementById('mapInfo').textContent = 'Térkép betöltése…';
      const txt = await fetchSvg(cfg.svgPath);
      if (seq !== buildSeq) return;
      const sb = cfg.svgBounds ? llb(cfg.svgBounds) : bounds;
      if (txt) {
        svgEl = document.createElementNS(NS, 'svg');
        svgEl.setAttribute('xmlns', NS);
        svgEl.innerHTML = txt;
        const inner = svgEl.querySelector('svg');
        if (inner) {
          svgEl.setAttribute('viewBox', inner.getAttribute('viewBox'));
          for (const g of inner.children) {
            if (g.nodeName !== 'g' || !g.id) continue;
            if (g.id === cfg.svgLayer || g.dataset.keepWithGroup === cfg.svgLayer) g.classList.add('base-layer');
            else g.classList.add('hidden-layer', 'overlay-layer');
          }
        }
        L.svgOverlay(svgEl, sb, { className: 'tk-svg', interactive: false }).addTo(lmap);
      } else {
        L.imageOverlay(cfg.svgPath, sb, { className: 'tk-img' }).addTo(lmap);
      }
    } else if (cfg.tilePath) {
      L.tileLayer(cfg.tilePath, tileOpts(cfg, bounds)).addTo(lmap);
    }
  }

  function onPopupClick(e) {
    const ob = e.target.closest('[data-mobj]');
    if (ob) {
      toggleObjective(ob.dataset.mtask, ob.dataset.mobj);
      lmap.closePopup();
      render();
      return;
    }
    const q = e.target.closest('[data-mq]');
    if (q) openQuest(q.dataset.mq);
  }

  // Egy quest céljára ugrik: kikeresi, melyik pályán van, és odanagyít.
  async function focus(taskId, objId) {
    let data;
    try { data = await load(); } catch (e) { alert(e.message); return; }
    const g = data.geo[objId] || {};
    const pts = [];
    for (const z of g.zones || []) if (z.position && z.map) pts.push({ id: z.map.id, p: z.position });
    for (const l of g.possibleLocations || []) for (const p of l.positions || []) if (l.map) pts.push({ id: l.map.id, p });
    for (const pt of pts) {
      const m = MAP_CONFIGS.find(c => apiIds(c, data.apiMaps).has(pt.id) && inB(pt.p, c.bounds));
      if (m) {
        S.mapKey = m.key; save();
        focusObj = { taskId, objId, p: pt.p };
        showView('v-map');
        return;
      }
    }
    alert('Ehhez a célhoz nincs pontos hely a térképen.');
  }

  function init() {
    document.getElementById('mapSel').addEventListener('change', e => { S.mapKey = e.target.value; save(); render(); });
    document.querySelectorAll('[data-mf]').forEach(c => c.onclick = () => { S.mapFilter = c.dataset.mf; save(); render(); });
    document.getElementById('extractChip').onclick = () => { S.showExtracts = !S.showExtracts; save(); render(); };
    document.getElementById('raidChip').onclick = () => {
      raidOpen = !raidOpen; render();
      if (raidOpen) setTimeout(() => document.getElementById('raidOut').scrollIntoView({ behavior: 'smooth' }), 300);
    };
    document.getElementById('floorChips').addEventListener('click', e => {
      const c = e.target.closest('[data-floor]');
      if (c) setFloor(+c.dataset.floor < 0 ? null : cfg.layers[+c.dataset.floor]);
    });
    document.getElementById('raidOut').addEventListener('click', e => {
      const c = e.target.closest('[data-rfocus]');
      if (!c) return;
      const ms = markersByObj[c.dataset.rfocus] || [];
      if (!ms.length) return;
      window.scrollTo({ top: 0, behavior: 'smooth' });
      lmap.fitBounds(L.latLngBounds(ms.map(m => m.getLatLng())).pad(0.6), { maxZoom: (cfg.maxZoom || 6) - 1 });
      setTimeout(() => ms[0].openPopup(), 400);
    });
  }

  return { init, render, focus, invalidate: () => lmap && lmap.invalidateSize() };
})();
