// Futtatás: node test/gen.test.js
const G = require('../www/gen.js');
const assert = require('assert');
let n = 0;
const ok = (c, msg) => { assert.ok(c, msg); n++; };

// Determinisztikus: ugyanaz a seed ugyanazt adja
ok(JSON.stringify(G.generate({ diff: 2, seed: 42 })) === JSON.stringify(G.generate({ diff: 2, seed: 42 })), 'seed');
ok(JSON.stringify(G.daily('2026-10-25')) === JSON.stringify(G.daily('2026-10-25')), 'napi azonos');
ok(G.daily('2026-10-25').seed !== G.daily('2026-10-26').seed, 'napi különbözik');

const gunRules = new Set(G.RULES.filter(r => r.gun).map(r => r.t));
for (let i = 0; i < 20000; i++) {
  const d = 1 + (i % 3), players = 1 + (i % 5);
  const m = G.generate({ diff: d, players, seed: i * 7919 });
  ok(m.map && m.objective.t && m.extract.t && m.time.t, 'mezők');
  ok(m.players.length === players, 'játékosszám');
  ok(m.rules.length === G.DIFFS[d].rules, 'szabályszám ' + d + ' ' + m.rules.length);
  ok(new Set(m.rules).size === m.rules.length, 'nincs dupla szabály');
  ok(m.points > 0 && Number.isFinite(m.points), 'pont');
  ok(m.rerollsLeft === G.DIFFS[d].rerolls, 'reroll');
  const melee = m.players.some(p => p.melee);
  if (melee) {
    ok(!m.rules.some(t => gunRules.has(t)), 'késsel nincs lőfegyveres szabály: ' + m.rules);
    ok(m.objective.tag !== 'head', 'késsel nincs fejlövés');
  }
  m.players.forEach(p => { if (p.melee) ok(!p.ammo, 'késhez nincs lőszer'); else ok(p.ammo, 'lőszer van'); });
  const bad = G.RULES.filter(r => r.bad && r.bad.includes(m.objective.tag)).map(r => r.t);
  ok(!m.rules.some(t => bad.includes(t)), 'szabály nem ütközik a céllal: ' + m.objective.tag + ' ' + m.rules);
  if (m.players.some(p => p.pickup)) ok(!m.rules.some(t => t.startsWith('Csak a küldetéshez')), 'felvett fegyverrel lehet lootolni');
  if (players === 1) ok(!m.rules.some(t => t.includes('csapat')), 'egyedül nincs csapatszabály');
  if (d === 1) ok(m.timeLimit === null, 'kemény: nincs időlimit');
  if (d === 3) ok(m.timeLimit >= 18 && m.timeLimit <= 25, 'őrület időlimit');
  if (!G.MAPS.find(x => x.id === m.mapId).night) ok(!m.time.night, 'beltéren nincs éjszaka');
  if (m.objective.tag === 'boss') ok(G.MAPS.find(x => x.id === m.mapId).boss, 'boss csak bossos pályán');
  ok(!/undefined|NaN|null/.test(JSON.stringify([m.objective.t, m.extract.t, m.rules, m.punish, m.players])), 'nincs undefined a szövegben');
}

// Újrasorsolás
for (let i = 0; i < 3000; i++) {
  const m = G.generate({ diff: 1 + (i % 3), players: 1 + (i % 4), seed: i });
  const keys = ['map', 'objective', 'extract', 'time', 'rule:0', 'p:0:weapon', 'p:0:armor', 'p:0:meds', 'p:0:gear', 'p:0:ammo'];
  const oldMap = m.mapId;
  G.reroll(m, 'map'); ok(m.mapId !== oldMap, 'új pálya');
  keys.forEach(k => G.reroll(m, k));
  const melee = m.players.some(p => p.melee);
  if (melee) ok(!m.rules.some(t => gunRules.has(t)), 'reroll után sincs lőfegyveres szabály késsel');
  ok(new Set(m.rules).size === m.rules.length, 'reroll: nincs dupla');
  const bad2 = G.RULES.filter(r => r.bad && r.bad.includes(m.objective.tag)).map(r => r.t);
  ok(!m.rules.some(t => bad2.includes(t)), 'reroll: nincs ütközés');
  ok(m.rules.length === G.DIFFS[m.diff].rules, 'reroll: szabályszám');
  ok(m.points > 0, 'reroll pont');
}

ok(G.rank(0).name === 'Timmy' && G.rank(150).name === 'Patkány' && G.rank(999999).next === null, 'rang');

// Eloszlás: minden pálya és cél előfordul
const maps = new Set(), objs = new Set();
for (let i = 0; i < 5000; i++) { const m = G.generate({ diff: 3, seed: i }); maps.add(m.mapId); objs.add(m.objective.tag); }
ok(maps.size === G.MAPS.length, 'minden pálya');
ok(objs.size === G.OBJECTIVES.length, 'minden cél: ' + [...objs]);
console.log('OK,', n, 'ellenőrzés');

for (let i = 0; i < 20000; i++) { const m = G.generate({ diff: 3, players: 3, seed: i }); m.players.forEach(p => { if (p.weapon.startsWith('🎒')) assert.ok(p.armor.startsWith('Csak a raidben talált'), 'meztelen páncél'); }); }
console.log('meztelen OK');
