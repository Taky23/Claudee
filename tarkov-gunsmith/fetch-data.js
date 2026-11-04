#!/usr/bin/env node
// Build időben fut (GitHub Actions, tiszta internet). A fegyver-/mod-adatokat az
// EFT JÁTÉK saját adatbázisából (SPT projekt, GitHub) építi fel, NEM a tarkov.dev
// élő API-jából – így az app offline, azonnal betölt, és független a tarkov.dev
// elérhetőségétől. Kimenet: www/data.json a tarkov.dev-hez hasonló alakban, hogy
// az app normalize()-a és az élő frissítés változatlan maradjon.
//
// Források:
//   items.json  – LFS, jsDelivr oldja fel a tartalmat (CI-ben elérhető)
//   en.json     – nyers raw.githubusercontent (nem LFS), megjelenítési nevek

const fs = require('fs');
const path = require('path');
const OUT = path.join(__dirname, 'www', 'data.json');

// items.json LFS-ben van; a tartalmat csak olyan forrás adja vissza, ami feloldja
// az LFS-t. A GitHub mirror és a jsDelivr csak a pointert adja, ezért az SPT saját
// Gitea-ját próbáljuk (a CI-nek nyílt internete van, feloldja az LFS media-t).
const ITEMS_PATH = 'project/assets/database/templates/items.json';
const ITEMS_URLS = [
  `https://dev.sp-tarkov.com/SPT/Server/media/branch/master/${ITEMS_PATH}`,
  `https://dev.sp-tarkov.com/SPT/Server/raw/branch/master/${ITEMS_PATH}`,
  `https://dev.sp-tarkov.com/SPT-AKI/Server/media/branch/master/${ITEMS_PATH}`,
  `https://dev.sp-tarkov.com/SPT-AKI/Server/raw/branch/master/${ITEMS_PATH}`,
  `https://cdn.jsdelivr.net/gh/sp-tarkov/server@master/${ITEMS_PATH}`,
  `https://media.githubusercontent.com/media/sp-tarkov/server/master/${ITEMS_PATH}`,
];
const LOCALE_URLS = [
  'https://raw.githubusercontent.com/sp-tarkov/server/master/project/assets/database/locales/global/en.json',
  'https://cdn.jsdelivr.net/gh/sp-tarkov/server@master/project/assets/database/locales/global/en.json',
];

async function getJson(urls, label) {
  let lastErr = '';
  for (const url of urls) {
    for (let i = 0; i < 3; i++) {
      try {
        const r = await fetch(url, { headers: { 'User-Agent': 'TarkovGunsmith-build/1.0' } });
        if (!r.ok) { lastErr = `HTTP ${r.status} @ ${url}`; console.error(`[${label}] ${lastErr}`); await sleep(1500 * (i + 1)); continue; }
        const text = await r.text();
        if (text.startsWith('version https://git-lfs')) { lastErr = `LFS pointer (nem feloldott) @ ${url}`; console.error(`[${label}] ${lastErr}`); break; }
        const json = JSON.parse(text);
        console.log(`[${label}] OK: ${Math.round(text.length / 1024)} kB, ${Object.keys(json).length} kulcs (${url.split('/')[2]})`);
        return json;
      } catch (e) { lastErr = (e.message || String(e)) + ` @ ${url}`; console.error(`[${label}] próba ${i + 1}: ${lastErr}`); await sleep(1500 * (i + 1)); }
    }
  }
  throw new Error(`[${label}] nem sikerült: ${lastErr}`);
}
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// Ammó-slotok, amiket NEM járunk be (nem modok): töltény/kamra.
const AMMO_SLOT = /patron|cartridge|camora/i;

function slotFilterIds(slot) {
  const f = slot && slot._props && slot._props.filters;
  if (!Array.isArray(f)) return [];
  const ids = [];
  for (const g of f) if (g && Array.isArray(g.Filter)) ids.push(...g.Filter);
  return ids;
}

(async () => {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  try {
    const items = await getJson(ITEMS_URLS, 'items');
    const en = await getJson(LOCALE_URLS, 'locale');

    const nameOf = id => en[id + ' Name'] || (items[id] && items[id]._name) || id;
    const shortOf = id => en[id + ' ShortName'] || nameOf(id);
    const isItem = it => it && it._type === 'Item' && it._props;

    // 1) Fegyverek: a weapClass mező megbízhatóan jelzi a fegyvert.
    const gunIds = [];
    for (const id in items) {
      const it = items[id];
      if (isItem(it) && it._props.weapClass && Array.isArray(it._props.Slots)) gunIds.push(id);
    }

    // 2) Modok: BFS a fegyverek slotjaiból kiindulva (az ammó-slotokat kihagyva).
    const modIds = new Set();
    const queue = [];
    for (const gid of gunIds) {
      for (const s of items[gid]._props.Slots || []) {
        if (AMMO_SLOT.test(s._name || '')) continue;
        for (const fid of slotFilterIds(s)) queue.push(fid);
      }
    }
    while (queue.length) {
      const id = queue.pop();
      if (modIds.has(id) || !isItem(items[id])) continue;
      // ammót ne vegyünk fel modként
      const p = items[id]._props;
      if (p.Caliber && typeof p.Damage === 'number') continue;
      modIds.add(id);
      for (const s of p.Slots || []) {
        if (AMMO_SLOT.test(s._name || '')) continue;
        for (const fid of slotFilterIds(s)) if (!modIds.has(fid)) queue.push(fid);
      }
    }

    const mapSlots = (it, keepIds) => (it._props.Slots || [])
      .filter(s => !AMMO_SLOT.test(s._name || ''))
      .map(s => ({
        id: s._id, name: s._name, required: !!s._required,
        filters: { allowedItems: slotFilterIds(s).filter(fid => keepIds.has(fid)).map(fid => ({ id: fid })) },
      }))
      .filter(s => s.filters.allowedItems.length); // üres slotokat kihagyjuk

    const allModSet = modIds; // mely id-k engedélyezettek slotokban
    const guns = gunIds.map(id => {
      const p = items[id]._props;
      return {
        id, name: nameOf(id), shortName: shortOf(id),
        properties: {
          __typename: 'ItemPropertiesWeapon',
          ergonomics: p.Ergonomics || 0,
          recoilVertical: p.RecoilForceUp || 0,
          recoilHorizontal: p.RecoilForceBack || 0,
          caliber: p.ammoCaliber || '',
          slots: mapSlots(items[id], allModSet),
        },
      };
    }).filter(g => g.slots || g.properties.slots.length >= 0);

    const mods = [...modIds].map(id => {
      const p = items[id]._props;
      return {
        id, name: nameOf(id), shortName: shortOf(id),
        properties: {
          __typename: 'ItemPropertiesWeaponMod',
          ergonomics: typeof p.Ergonomics === 'number' ? p.Ergonomics : 0,
          recoilModifier: typeof p.Recoil === 'number' ? p.Recoil / 100 : 0,
          slots: mapSlots(items[id], allModSet),
        },
      };
    });

    const payload = { at: Date.now(), source: 'spt-game-db', guns, mods };
    fs.writeFileSync(OUT, JSON.stringify(payload));
    const kb = Math.round(fs.statSync(OUT).size / 1024);

    // Diagnosztika a CI-loghoz
    const sg = guns.find(g => g.shortName === 'M4A1') || guns[0];
    const sampleModId = sg && sg.properties.slots[0] && sg.properties.slots[0].filters.allowedItems[0] && sg.properties.slots[0].filters.allowedItems[0].id;
    const sm = mods.find(m => m.id === sampleModId) || mods[0];
    console.log(`\n✅ data.json kész: ${guns.length} fegyver, ${mods.length} mod, ${kb} kB`);
    if (sg) console.log(`   Minta fegyver: ${sg.name} [${sg.shortName}] ergo=${sg.properties.ergonomics} vert=${sg.properties.recoilVertical} cal=${sg.properties.caliber} slotok=${sg.properties.slots.length}`);
    if (sm) console.log(`   Minta mod: ${sm.name} [${sm.shortName}] ergo=${sm.properties.ergonomics} recoilMod=${sm.properties.recoilModifier} subslot=${sm.properties.slots.length}`);
    if (!guns.length || !mods.length) throw new Error('üres fegyver- vagy mod-lista');
  } catch (e) {
    console.error('\n⚠️ Nem sikerült beépíteni az adatokat:', e.message);
    console.error('   Üres data.json kerül be; az app élőben (tarkov.dev) próbálkozik.');
    fs.writeFileSync(OUT, JSON.stringify({ at: Date.now(), guns: [], mods: [], error: e.message }));
  }
})();
