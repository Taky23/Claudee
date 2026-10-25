// Élő próba a valódi tarkov.dev API-val: megnyitja a webappot headless Chrome-ban, és megnézi,
// hogy betöltenek-e a questek, a térkép jelölői és az árak. Használat: node live-test.js <url>
const { chromium } = require('playwright');

(async () => {
  const url = process.argv[2] || 'http://localhost:8765/index.html';
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 390, height: 844 } });
  const logs = [];
  p.on('console', m => { if (m.type() === 'warning' || m.type() === 'error') logs.push(`[${m.type()}] ${m.text()}`); });
  p.on('pageerror', e => logs.push('[pageerror] ' + e.message));
  p.on('response', r => { if (r.url().includes('tarkov.dev') && r.status() >= 400) logs.push(`[http ${r.status()}] ${r.url().slice(0, 140)}`); });
  p.on('dialog', d => d.accept());
  let ok = true;
  const check = (name, cond, info) => { console.log(`${cond ? 'OK  ' : 'HIBA'} ${name}: ${info}`); if (!cond) ok = false; };

  await p.goto(url + '#tasks');
  await p.waitForSelector('#tasksOut .task, #tasksOut .err', { timeout: 60000 }).catch(() => {});
  await p.click('[data-qv="all"]');
  await p.waitForTimeout(1500);
  const tasks = await p.locator('#tasksOut .task').count();
  check('Questek', tasks > 50, `${tasks} quest látszik; ${(await p.textContent('#tasksOut')).replace(/\s+/g, ' ').slice(0, 120)}`);
  await p.waitForTimeout(8000);
  const pins = await p.locator('#tasksOut [data-pin]').count();
  check('Térképes célok a questeknél', pins > 20, `${pins} 📍 gomb`);

  await p.click('nav [data-view="v-map"]');
  await p.click('[data-mf="all"]');
  await p.waitForTimeout(12000);
  const marks = await p.locator('.mk').count();
  const svg = await p.locator('.tk-svg').count();
  check('Térkép (Customs)', marks > 5 && svg > 0, `${marks} jelölő, SVG: ${svg}, info: ${await p.textContent('#mapInfo')}`);
  const extracts = await p.locator('path.leaflet-interactive').count();
  check('Kijáratok', extracts > 3, `${extracts} kör/zóna`);

  await p.click('nav [data-view="v-price"]');
  await p.fill('#q', 'salewa');
  await p.waitForSelector('#priceOut .card, #priceOut .err', { timeout: 30000 }).catch(() => {});
  const items = await p.locator('#priceOut .card .item').count();
  check('Árkeresés', items > 0, `${items} találat`);

  await p.click('nav [data-view="v-ammo"]');
  await p.waitForSelector('#ammoOut table, #ammoOut .err', { timeout: 30000 }).catch(() => {});
  check('Lőszer', await p.locator('#ammoOut tr').count() > 3, `${await p.locator('#ammoOut tr').count()} sor`);

  console.log('\n--- Konzol figyelmeztetések / hibák ---\n' + (logs.join('\n') || 'nincs'));
  await b.close();
  process.exit(ok ? 0 : 1);
})();
