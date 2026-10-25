// A json.tarkov.dev adatszerkezetének kiírása (fejlesztéshez). Használat: node json-probe.js
const BASE = 'https://json.tarkov.dev/regular/';
const get = async p => { const r = await fetch(BASE + p); if (!r.ok) throw new Error(p + ' ' + r.status); return r.json(); };
const show = (label, v, n = 2500) => console.log(`\n### ${label}\n` + JSON.stringify(v, null, 1).slice(0, n));
(async () => {
  const tasks = await get('tasks');
  const td = tasks.data;
  show('tasks top keys', Object.keys(td).map(k => [k, Array.isArray(td[k]) ? 'array' : typeof td[k], Object.keys(td[k] || {}).length]));
  show('translations', (tasks.translations || []).slice(0, 40));
  const list = Object.values(td.tasks);
  const withZones = list.find(t => t.objectives.some(o => o.zones && o.zones.length && o.type === 'plantItem'));
  show('task (plantItem zones)', withZones, 6000);
  const qi = list.find(t => t.objectives.some(o => o.possibleLocations && o.possibleLocations.length));
  show('task objective possibleLocations', qi && qi.objectives.find(o => o.possibleLocations), 2500);
  show('task mark objective', list.flatMap(t => t.objectives).find(o => o.type === 'mark'), 2000);
  show('task useItem objective', list.flatMap(t => t.objectives).find(o => o.type === 'useItem'), 1500);
  show('task with neededKeys + rewards', list.find(t => (t.neededKeys || []).length), 4000);
  show('objective types', [...new Set(list.flatMap(t => t.objectives.map(o => o.type)))]);
  show('questItems sample', Object.values(td.questItems || {}).slice(0, 1));
  const hu = await get('tasks_hu');
  show('tasks_hu sample', Object.entries(hu.data).slice(0, 8));
  show('tasks_hu keys for withZones', Object.entries(hu.data).filter(([k]) => k.startsWith(withZones.id)).slice(0, 10));

  const maps = await get('maps');
  show('maps top keys', Object.keys(maps.data));
  const cust = Object.values(maps.data.maps).find(m => m.normalizedName === 'customs');
  show('customs keys', Object.keys(cust));
  show('customs basic', { id: cust.id, name: cust.name, normalizedName: cust.normalizedName, extracts: cust.extracts.slice(0, 2), transits: (cust.transits || []).slice(0, 1) }, 3000);
  show('maps translations', (maps.translations || []).slice(0, 20));

  const items = await get('items');
  show('items top keys', Object.keys(items.data));
  const il = Object.values(items.data.items);
  show('item count', il.length);
  const salewa = il.find(i => i.normalizedName === 'salewa-first-aid-kit');
  show('item salewa', salewa, 5000);
  const ammo = il.find(i => i.normalizedName && i.normalizedName.includes('m855a1'));
  show('item ammo m855a1 properties', ammo && { types: ammo.types, properties: ammo.properties }, 3000);
  show('fleaMarket', items.data.fleaMarket);
  show('items translations', (items.translations || []).slice(0, 20));

  const hideout = await get('hideout');
  const st = Object.values(hideout.data || hideout)[0];
  show('hideout top', Object.keys(hideout));
  show('hideout station', st, 2500);
  const traders = await get('traders');
  show('traders top', Object.keys(traders));
  show('trader', Object.values(traders.data || traders)[0], 2000);
  for (const p of ['items_hu', 'maps_hu', 'traders_hu', 'hideout_hu', 'items_en']) {
    try { const d = await get(p); show(p + ' sample', Object.entries(d.data).slice(0, 4)); } catch (e) { console.log('\n### ' + p + ' HIBA ' + e.message); }
  }
  for (const p of ['pve/tasks', 'pve/items']) {
    const r = await fetch('https://json.tarkov.dev/' + p, { method: 'HEAD' }); console.log(p, r.status);
  }
})().catch(e => { console.error(e); process.exit(1); });
