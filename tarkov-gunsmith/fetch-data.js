#!/usr/bin/env node
// Build időben fut (GitHub Actions, tiszta internet). Letölti a tarkov.dev
// fegyver- és mod-adatait, és www/data.json-be menti, hogy az APK OFFLINE,
// azonnal betöltsön – ne függjön a telefonon a tarkov.dev élő elérhetőségétől.
// Ha a letöltés nem sikerül, üres data.json-t ír (hibajelzéssel) és 0-val lép ki,
// így a build akkor is lefut; az app ilyenkor élőben próbálkozik.

const fs = require('fs');
const path = require('path');

const API = 'https://api.tarkov.dev/graphql';
const OUT = path.join(__dirname, 'www', 'data.json');

const SLOT_FRAG = 'slots { id name required filters { allowedItems { id } } }';
const gunQ = `{ items(type: gun) { id name shortName properties { __typename ... on ItemPropertiesWeapon { ergonomics recoilVertical recoilHorizontal caliber ${SLOT_FRAG} } } } }`;
const modQ = `{ items(type: mods) { id name shortName properties { __typename ... on ItemPropertiesWeaponMod { ergonomics recoilModifier ${SLOT_FRAG} } } } }`;

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function gql(query, label) {
  let lastErr = '';
  for (let i = 0; i < 5; i++) {
    try {
      const r = await fetch(API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'User-Agent': 'TarkovGunsmith-build/1.0' },
        body: JSON.stringify({ query }),
      });
      const text = await r.text();
      let d = null;
      try { d = JSON.parse(text); } catch {}
      if (d && d.errors && d.errors.length) {
        lastErr = d.errors.map(e => (typeof e === 'string' ? e : (e && e.message)) || '').join(' | ');
        console.error(`[${label}] próba ${i + 1}: GraphQL hiba [${r.status}]: ${lastErr}`);
      } else if (d && d.data && d.data.items) {
        console.log(`[${label}] OK: ${d.data.items.length} elem (HTTP ${r.status}, ${i + 1}. próba)`);
        return d.data.items;
      } else {
        lastErr = `váratlan válasz [${r.status}]: ${text.slice(0, 160)}`;
        console.error(`[${label}] próba ${i + 1}: ${lastErr}`);
      }
    } catch (e) {
      lastErr = e.message || String(e);
      console.error(`[${label}] próba ${i + 1}: hálózati hiba: ${lastErr}`);
    }
    await sleep(2000 * (i + 1));
  }
  throw new Error(`[${label}] nem sikerült 5 próbából: ${lastErr}`);
}

(async () => {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  try {
    const guns = await gql(gunQ, 'guns');
    const mods = await gql(modQ, 'mods');
    const payload = { at: Date.now(), guns, mods };
    fs.writeFileSync(OUT, JSON.stringify(payload));
    const kb = Math.round(fs.statSync(OUT).size / 1024);
    console.log(`\n✅ data.json kész: ${guns.length} fegyver, ${mods.length} mod, ${kb} kB`);
  } catch (e) {
    console.error('\n⚠️ Nem sikerült beépíteni az adatokat:', e.message);
    console.error('   Üres data.json kerül be; az app élőben próbálkozik majd.');
    fs.writeFileSync(OUT, JSON.stringify({ at: Date.now(), guns: [], mods: [], error: e.message }));
    // Szándékosan 0-val lépünk ki, hogy a build folytatódjon.
  }
})();
