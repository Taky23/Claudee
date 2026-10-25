// Tarkov Hardcore – küldetés-generátor (adatok + sorsolás). Böngészőben és Node-ban is fut.
(function (root) {
  'use strict';

  // ---------- Véletlen (seedelhető, hogy a napi kihívás mindenkinek ugyanaz legyen) ----------
  function rng(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function hashStr(s) {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  const pick = (r, arr) => arr[Math.floor(r() * arr.length)];
  const int = (r, lo, hi) => lo + Math.floor(r() * (hi - lo + 1));
  function pickN(r, arr, n) {
    const pool = arr.slice(), out = [];
    while (out.length < n && pool.length) out.push(pool.splice(Math.floor(r() * pool.length), 1)[0]);
    return out;
  }

  // ---------- Nehézségek ----------
  const DIFFS = {
    1: { name: 'Kemény', icon: '😬', rules: 2, rerolls: 3, mult: 1 },
    2: { name: 'Hardcore', icon: '💀', rules: 3, rerolls: 1, mult: 2 },
    3: { name: 'Őrület', icon: '☢️', rules: 4, rerolls: 0, mult: 4 },
  };

  // ---------- Pályák ----------
  // boss: null, ha nincs saját bossa. night: lehet-e éjszakai raid. hot: veszélyes pontok.
  const MAPS = [
    { id: 'customs', name: 'Customs', boss: 'Reshala', night: true,
      hot: ['a Dorms (kollégium) 3. emelete', 'a New Gas benzinkút', 'a Big Red raktár', 'a Fortress (erőd)', 'a Crack House'],
      ex: ['ZB-1011', 'Crossroads', 'RUAF Roadblock', 'Smuggler\'s Boat', 'Old Gas Station', 'Dorms V-Ex', 'ZB-1012', 'Trailer Park'] },
    { id: 'woods', name: 'Woods', boss: 'Shturman', night: true,
      hot: ['a fűrésztelep (Sawmill)', 'az USEC tábor', 'a lezuhant repülőgép', 'a Scav-bunker (ZB-014)', 'a hegyi bázis (Mountain Stash)'],
      ex: ['Outskirts', 'UN Roadblock', 'ZB-016', 'Bridge V-Ex', 'South V-Ex', 'RUAF Gate'] },
    { id: 'shoreline', name: 'Shoreline', boss: 'Sanitar', night: true,
      hot: ['az üdülő (Health Resort) keleti szárnya', 'az üdülő nyugati szárnya', 'a vízerőmű', 'a meteorológiai állomás', 'a kikötő'],
      ex: ['Tunnel', 'Road to Customs', 'Pier Boat', 'Rock Passage', 'Path to Lighthouse', 'CCP Temporary'] },
    { id: 'interchange', name: 'Interchange', boss: 'Killa', night: true,
      hot: ['a Kiba Arms fegyverbolt', 'a Techlight', 'az OLI áruház', 'a Goshan', 'a parkolóház'],
      ex: ['Emercom Checkpoint', 'Railway Exfil', 'Hole in the Fence', 'Power Station V-Ex', 'Saferoom Exfil'] },
    { id: 'reserve', name: 'Reserve', boss: 'Glukhar', night: true,
      hot: ['a fehér király (White Knight) épülete', 'a fekete gyalog (Black Pawn)', 'a bunkerek', 'a kórház (Fehér futó)', 'a vasúti depó'],
      ex: ['D-2', 'Cliff Descent', 'Armored Train', 'Bunker Hermetic Door', 'Sewer Manhole', 'Scav Lands'] },
    { id: 'lighthouse', name: 'Lighthouse', boss: 'Rogue-ok (víztisztító)', night: true,
      hot: ['a víztisztító (Rogue-bázis)', 'a világítótorony', 'a hegyi villák', 'a vonatállomás', 'a Chalet'],
      ex: ['Southern Road', 'Path to Shoreline', 'Side Tunnel', 'Armored Train', 'Mountain Pass'] },
    { id: 'streets', name: 'Streets of Tarkov', boss: 'Kaban', night: true,
      hot: ['a Lexos autószalon', 'a Concordia lakópark', 'a Pinewood hotel', 'a Chek 13 bolt', 'a mozi (Cinema)'],
      ex: ['Evacuation Zone', 'Crash Site', 'Sewer River', 'Klimov Street', 'Collapsed Crane', 'Damaged House'] },
    { id: 'factory', name: 'Factory', boss: 'Tagilla', night: true,
      hot: ['az irodák (3. emelet)', 'a Pumping Station', 'a Forklift-terem', 'a Gate 3 környéke', 'az alagsor'],
      ex: ['Gate 3', 'Cellars', 'Gate 0', 'Med Tent Gates'] },
    { id: 'gz', name: 'Ground Zero', boss: null, night: true,
      hot: ['a Terragroup torony környéke', 'a Nakatani bevásárlóközpont', 'az Emercom bázis', 'a parkolóház', 'a Mira sugárút'],
      ex: ['Emercom Checkpoint', 'Nakatani Basement', 'Mira Ave', 'Police Cordon V-Ex'] },
    { id: 'lab', name: 'The Lab', boss: 'Raiderek', night: false,
      hot: ['a szerverterem', 'a menedzser irodája', 'a BEAR-labor', 'az orvosi blokk', 'az aréna'],
      ex: ['Main Elevator', 'Medical Block Elevator', 'Parking Gate', 'Sewage Conduit', 'Hangar Gate', 'Ventilation Shaft'] },
    { id: 'labyrinth', name: 'The Labyrinth', boss: 'Shadow of Tagilla', night: false,
      hot: ['a labirintus közepe', 'a csapdás folyosók', 'a kiindulási terem'],
      ex: [] },
  ];

  // ---------- Fegyverek ----------
  const WEAPONS = {
    'Pisztoly': ['PM', 'TT', 'Glock 17', 'M1911A1', 'M9A3', 'USP .45', 'Desert Eagle', 'SR-1MP', 'APS', 'MP-443 Grach', 'Five-seveN'],
    'Géppisztoly': ['MP5', 'MP7A1', 'MP9', 'Vector 9x19', 'UMP 45', 'PP-19-01 Vityaz', 'P90', 'PPSh-41', 'MPX', 'Kedr', 'Saiga-9'],
    'Gépkarabély': ['M4A1', 'HK 416A5', 'AK-74M', 'AKM', 'AK-105', 'AK-12', 'MDR', 'SCAR-L', 'AUG A3', 'ASh-12', 'SA-58', 'MCX', 'RD-704', 'Mk47'],
    'DMR': ['SVDS', 'RSASS', 'M1A', 'SR-25', 'SKS', 'VSS Vintorez', 'G28', 'OP-SKS', 'Vepr Hunter'],
    'Ismétlő puska': ['Mosin', 'SV-98', 'M700', 'T-5000', 'DVL-10', 'AXMC', 'VPO-215'],
    'Sörétes': ['MP-133', 'MP-153', 'Saiga-12', 'KS-23M', 'M590A1', 'M870', 'MP-43 (kétcsövű)', 'TOZ-106'],
  };
  // A „rossz” fegyverek, amiket Őrületen gyakrabban kapsz.
  const CURSED_WEAPONS = ['TOZ-106', 'MP-43 (kétcsövű)', 'PM', 'TT', 'PPSh-41', 'Kedr', 'VPO-215', 'Mosin', 'APS'];
  const SPECIAL_WEAPONS = [
    { t: '🔪 Csak kés. Semmi lőfegyver.', melee: true, min: 2 },
    { t: '🎒 Meztelenül indulsz: csak azzal harcolhatsz, amit a raidben találsz.', melee: false, min: 1, pickup: true, naked: true },
    { t: '🎲 Az első lőfegyver, amit a raidben felveszel. Előtte csak kés.', melee: false, min: 1, pickup: true },
    { t: '🧨 Csak gránátok és kés. Lőfegyver nem jöhet.', melee: true, min: 3 },
  ];

  // ---------- Felszerelés-szabályok ----------
  // lvl = legalább ennyi nehézségtől kerülhet elő.
  const AMMO = [
    { t: 'Csak a kaliber leggyengébb lőszere (pl. PS, FMJ, HP).', lvl: 2 },
    { t: 'Legfeljebb 2 tár lőszer, semmi tartalék a hátizsákban.', lvl: 2 },
    { t: 'Csak 1 tár. Ha kiürül, kés.', lvl: 3 },
    { t: 'Legfeljebb 30-as átütésű lőszer.', lvl: 1 },
    { t: 'Csak traderről vett lőszer, flea-ről nem.', lvl: 1 },
    { t: 'Bármilyen lőszer jöhet.', lvl: 1, max: 1 },
  ];
  const ARMOR = [
    { t: 'Nincs páncél és nincs sisak.', lvl: 2 },
    { t: 'Nincs páncél, csak sisak.', lvl: 1 },
    { t: 'Legfeljebb 3-as osztályú mellény, sisak nélkül.', lvl: 1 },
    { t: 'Legfeljebb 2-es osztályú mellény.', lvl: 2 },
    { t: 'Páncél jöhet, sisak nem.', lvl: 1 },
    { t: 'Csak a raidben talált páncél (meztelenül indulsz).', lvl: 3 },
    { t: 'Bármilyen páncél jöhet, de fejhallgató nem.', lvl: 1, max: 1 },
  ];
  const NAKED_ARMOR = 'Csak a raidben talált páncél (meztelenül indulsz).';
  const MEDS = [
    { t: 'Csak 2 kötszer és 1 érszorító.', lvl: 2 },
    { t: 'Csak egy AI-2 medkit. Semmi más.', lvl: 2 },
    { t: 'Semmilyen gyógyszer. Ami van, az van.', lvl: 3 },
    { t: 'Nincs sebészkészlet (CMS/Surv12).', lvl: 1 },
    { t: 'Nincs stimulátor.', lvl: 1 },
    { t: 'Nincs fájdalomcsillapító.', lvl: 2 },
    { t: 'Csak a raidben talált gyógyszer.', lvl: 3 },
  ];
  const GEAR = [
    { t: 'Nincs hátizsák.', lvl: 1 },
    { t: 'Nincs mellény/rig: minden a zsebben.', lvl: 2 },
    { t: 'Nincs fejhallgató.', lvl: 2 },
    { t: 'Csak vaslátó, semmi optika vagy kollimátor.', lvl: 1, gun: true },
    { t: 'Gyári fegyver: egyetlen alkatrészt sem cserélhetsz.', lvl: 2, gun: true },
    { t: 'A secure containert nem használhatod a raidben.', lvl: 3 },
    { t: 'Nincs biztosítás a felszerelésre.', lvl: 1 },
  ];

  // ---------- Csapatszabályok (mindenkire vonatkoznak) ----------
  const RULES = [
    { t: 'Nem futhatsz, csak akkor, ha lőnek rád.', lvl: 1 },
    { t: 'Ne lőj elsőként: csak visszalőhetsz.', lvl: 2, gun: true, bad: ['ghost'] },
    { t: 'Csak egyes lövés, semmi sorozat.', lvl: 1, gun: true },
    { t: 'Csak csípőből lőhetsz, célzás nélkül.', lvl: 3, gun: true },
    { t: 'Az első 5 percben nem lőhetsz.', lvl: 1, gun: true, bad: ['ghost'] },
    { t: 'Nem nézhetsz térképet és extract-listát a raid alatt.', lvl: 2 },
    { t: 'Nem gyógyíthatsz, amíg nem voltál 1 percig biztonságban.', lvl: 2 },
    { t: 'Minden ölés után el kell dobnod egy tárat.', lvl: 3, gun: true, bad: ['ghost'] },
    { t: 'Csak a küldetéshez kellő tárgyat veheted fel. Más loot nincs.', lvl: 2, bad: ['loot'], noPickup: true },
    { t: 'Ha a fegyveredre rakható hangtompító, kötelező rajta lennie.', lvl: 1, gun: true },
    { t: 'Az első 10 percet a spawnodban kell töltened (késői spawn).', lvl: 2 },
    { t: 'Nem ugorhatsz és nem hajolhatsz ki (lean).', lvl: 2 },
    { t: 'Ha megsebesülsz, 30 másodpercig guggolva kell maradnod.', lvl: 3 },
    { t: 'Nincs hang-csalás: a csapat csak a játékbeli VOIP-on beszélhet.', lvl: 1, squad: true },
    { t: 'Ha egy csapattárs meghal, a többieknek is azonnal ki kell jutniuk.', lvl: 2, squad: true },
    { t: 'Scavet nem ölhetsz, csak PMC-t és bosst.', lvl: 3, gun: true, bad: ['scav'] },
    { t: 'Minden ajtót becsukva kell hagynod magad mögött.', lvl: 1 },
  ];

  // ---------- Büntetések (ha elbuksz) ----------
  const PUNISH = [
    { t: 'A következő raidben csak pisztolyt vihetsz.', lvl: 1 },
    { t: 'A következő raid meztelenül (csak kés).', lvl: 1 },
    { t: 'Add el traderen a legdrágább fegyveredet.', lvl: 2 },
    { t: '24 óráig nem használhatod a flea marketet.', lvl: 2 },
    { t: 'Ürítsd ki a secure containered: mindent ki kell dobnod belőle.', lvl: 3 },
    { t: 'Adj el traderen 500 000 ₽ értékű tárgyat a stash-edből.', lvl: 3 },
    { t: 'A következő 3 raid csak a legolcsóbb fegyverrel, amid van.', lvl: 2 },
    { t: 'Dobd el a legjobb páncélodat (csak traderen eladni sem szabad).', lvl: 3 },
  ];

  const ITEMS = ['Physical Bitcoin', 'LEDX', 'Graphics card (GPU)', 'Tetriz', 'Ophthalmoscope', 'Military flash drive',
    'Golden rooster', 'Roler Submariner', 'Intelligence folder', 'Virtex processor', 'Military battery', 'Moonshine'];

  // ---------- Fő célok ----------
  // Minden cél egy függvény: (r, map, diff, melee) -> {t, pts} vagy null, ha nem illik ide.
  const OBJECTIVES = [
    function boss(r, m, d, melee) {
      if (!m.boss || (melee && d < 3)) return null;
      return { t: `Bossvadászat: ${m.boss}. Öld meg, és hozz ki tőle legalább egy tárgyat.`, pts: 40, tag: 'boss' };
    },
    function pmc(r, m, d) {
      const n = [0, int(r, 1, 2), int(r, 2, 3), int(r, 3, 5)][d];
      return { t: `Ölj meg ${n} PMC-t.`, pts: 12 * n, tag: 'pmc' };
    },
    function scav(r, m, d) {
      const n = [0, int(r, 4, 6), int(r, 6, 9), int(r, 10, 14)][d];
      return { t: `Ölj meg ${n} scavet.`, pts: 2 * n, tag: 'scav' };
    },
    function head(r, m, d, melee) {
      if (melee) return null;
      const n = [0, 3, 5, 8][d];
      return { t: `Legalább ${n} ölés, mind fejlövéssel. Egy nem-fejlövéses ölés és elbuktál.`, pts: 6 * n, tag: 'head' };
    },
    function spot(r, m, d) {
      const mins = [0, 2, 3, 5][d];
      return { t: `Juss el ide: ${pick(r, m.hot)}, és tölts ott ${mins} percet.`, pts: 15 + mins * 3, tag: 'spot' };
    },
    function loot(r, m, d) {
      const v = [0, 300, 600, 1000][d];
      return { t: `Hozz ki legalább ${v} 000 ₽ értékű lootot.`, pts: Math.round(v / 20), tag: 'loot' };
    },
    function item(r, m, d) {
      return { t: `Találd meg a raidben és hozd ki: ${pick(r, ITEMS)}.`, pts: 30, tag: 'item' };
    },
    function ghost(r, m, d) {
      return { t: 'Szellem-raid: egyetlen lövést sem adhatsz le, és senki nem találhat el.', pts: 25, tag: 'ghost' };
    },
    function survive(r, m, d) {
      const mins = [0, 25, 35, 45][d];
      return { t: `Maradj életben a raidben legalább ${mins} percig, csak utána indulhatsz az extracthoz.`, pts: mins, tag: 'survive' };
    },
  ];

  // ---------- Sorsolás ----------
  function filt(arr, d, melee, squad) {
    return arr.filter(x => d >= (x.lvl || 1) && (x.max == null || d <= x.max) && !(melee && x.gun) && !(x.squad && !squad));
  }

  function rollWeapon(r, d) {
    const specialChance = [0, 0.06, 0.14, 0.3][d];
    const specials = SPECIAL_WEAPONS.filter(s => d >= s.min);
    if (r() < specialChance && specials.length) {
      const s = pick(r, specials);
      return { t: s.t, melee: s.melee, pickup: !!s.pickup, naked: !!s.naked };
    }
    if (d === 3 && r() < 0.45) {
      const w = pick(r, CURSED_WEAPONS);
      const cat = Object.keys(WEAPONS).find(c => WEAPONS[c].includes(w));
      return { t: `${cat}: ${w}`, melee: false };
    }
    const cats = Object.keys(WEAPONS);
    const cat = pick(r, cats);
    return { t: `${cat}: ${pick(r, WEAPONS[cat])}`, melee: false };
  }

  function rollPlayer(r, d) {
    const w = rollWeapon(r, d);
    const p = { weapon: w.t, melee: w.melee };
    if (w.pickup) p.pickup = true;
    if (!w.melee) p.ammo = pick(r, filt(AMMO, d, false)).t;
    p.armor = w.naked ? NAKED_ARMOR : pick(r, filt(ARMOR, d, w.melee)).t;
    p.meds = pick(r, filt(MEDS, d, w.melee)).t;
    p.gear = pick(r, filt(GEAR, d, w.melee)).t;
    return p;
  }

  function rollObjective(r, map, d, anyMelee) {
    for (let i = 0; i < 50; i++) {
      const o = pick(r, OBJECTIVES)(r, map, d, anyMelee);
      if (o) return o;
    }
    return OBJECTIVES[4](r, map, d, anyMelee);
  }

  function rollExtract(r, map, d) {
    if (!map.ex.length) return { t: 'Bármelyik kijárat, amit a labirintusban találsz.', pts: 0 };
    const exactChance = [0, 0.4, 0.8, 1][d];
    if (r() < exactChance) return { t: `Csak ezen juthatsz ki: ${pick(r, map.ex)}.`, pts: 10 };
    return { t: 'Bármelyik extract jó.', pts: 0 };
  }

  function rollTime(r, map, d) {
    if (!map.night) return { t: '🏢 Beltéri pálya, nincs napszak', night: false };
    const nightChance = [0, 0.2, 0.35, 0.55][d];
    return r() < nightChance ? { t: '🌙 Éjszakai raid', night: true } : { t: '☀️ Nappali raid', night: false };
  }

  function rollTimeLimit(r, d) {
    if (d === 1) return null;
    if (d === 2 && r() < 0.5) return null;
    return [0, 0, int(r, 25, 35), int(r, 18, 25)][d];
  }

  // A küldetéshez illő szabályok (kés, csapat, cél, felvett fegyver szerint).
  function rulePool(m) {
    const melee = m.players.some(p => p.melee), pickup = m.players.some(p => p.pickup);
    return filt(RULES, m.diff, melee, m.players.length > 1)
      .filter(x => !(x.bad && x.bad.includes(m.objective.tag)) && !(x.noPickup && pickup))
      .map(x => x.t);
  }
  // Kicseréli a küldetéssel ütköző szabályokat, és pótolja a hiányzókat.
  function fixRules(r, m) {
    const pool = rulePool(m);
    const kept = [];
    m.rules.forEach(t => { if (pool.includes(t) && !kept.includes(t)) kept.push(t); });
    const want = DIFFS[m.diff].rules;
    while (kept.length < want) {
      const free = pool.filter(t => !kept.includes(t));
      if (!free.length) break;
      kept.push(pick(r, free));
    }
    m.rules = kept;
  }

  function rollPunish(r, d) {
    return pick(r, PUNISH.filter(p => p.lvl <= d && p.lvl >= Math.max(1, d - 1))).t;
  }

  // A teljes küldetés. opts: {diff, players, seed, mapId}
  function generate(opts) {
    const d = opts.diff || 2;
    const nPlayers = Math.max(1, Math.min(5, opts.players || 1));
    const seed = opts.seed != null ? opts.seed >>> 0 : (Math.random() * 4294967296) >>> 0;
    const r = rng(seed);
    const map = opts.mapId ? MAPS.find(m => m.id === opts.mapId) || pick(r, MAPS) : pick(r, MAPS);
    const players = Array.from({ length: nPlayers }, () => rollPlayer(r, d));
    const anyMelee = players.some(p => p.melee);
    const m = {
      v: 1, seed, diff: d, mapId: map.id, map: map.name,
      time: rollTime(r, map, d),
      objective: rollObjective(r, map, d, anyMelee),
      extract: rollExtract(r, map, d),
      timeLimit: rollTimeLimit(r, d),
      players,
      rules: [],
      punish: rollPunish(r, d),
      rerollsLeft: DIFFS[d].rerolls,
    };
    fixRules(r, m);
    m.points = score(m);
    return m;
  }

  function score(m) {
    let p = 20 + m.objective.pts + m.extract.pts + m.rules.length * 8;
    if (m.time.night) p += 15;
    if (m.timeLimit) p += 15;
    m.players.forEach(pl => { if (pl.melee) p += 30; });
    return Math.round(p * DIFFS[m.diff].mult * (1 + (m.players.length - 1) * 0.15));
  }

  // Egy elem újrasorsolása. key: 'map' | 'objective' | 'extract' | 'time' | 'rule:i' | 'p:i:field'
  function reroll(m, key) {
    const r = rng((Math.random() * 4294967296) >>> 0);
    const d = m.diff;
    const anyMelee = () => m.players.some(p => p.melee);
    if (key === 'map') {
      const others = MAPS.filter(x => x.id !== m.mapId);
      const map = pick(r, others);
      m.mapId = map.id; m.map = map.name;
      m.time = rollTime(r, map, d);
      m.objective = rollObjective(r, map, d, anyMelee());
      m.extract = rollExtract(r, map, d);
    } else {
      const map = MAPS.find(x => x.id === m.mapId);
      if (key === 'objective') {
        const old = m.objective.t;
        for (let i = 0; i < 20 && m.objective.t === old; i++) m.objective = rollObjective(r, map, d, anyMelee());
      } else if (key === 'extract') m.extract = rollExtract(r, map, d);
      else if (key === 'time') m.time = rollTime(r, map, d);
      else if (key.startsWith('rule:')) {
        const i = +key.split(':')[1];
        const pool = rulePool(m).filter(t => !m.rules.includes(t));
        if (pool.length) m.rules[i] = pick(r, pool);
      } else if (key.startsWith('p:')) {
        const [, si, field] = key.split(':');
        const pl = m.players[+si];
        if (field === 'weapon') {
          const w = rollWeapon(r, d);
          pl.weapon = w.t; pl.melee = w.melee;
          if (w.pickup) pl.pickup = true; else delete pl.pickup;
          if (w.naked) pl.armor = NAKED_ARMOR; else if (pl.armor === NAKED_ARMOR) pl.armor = pick(r, filt(ARMOR, d, w.melee).filter(x => x.t !== NAKED_ARMOR)).t;
          if (w.melee) delete pl.ammo; else if (!pl.ammo) pl.ammo = pick(r, filt(AMMO, d, false)).t;
          if (w.melee) {
            const okGear = filt(GEAR, d, true).map(x => x.t);
            m.players.forEach(p2 => { if (p2.melee && !okGear.includes(p2.gear)) p2.gear = pick(r, okGear); });
            if (m.objective.tag === 'head') m.objective = rollObjective(r, map, d, true);
          }
        } else if (field === 'ammo' && !pl.melee) pl.ammo = pick(r, filt(AMMO, d, false)).t;
        else if (field === 'armor') pl.armor = pl.weapon.startsWith('🎒') ? NAKED_ARMOR : pick(r, filt(ARMOR, d, pl.melee)).t;
        else if (field === 'meds') pl.meds = pick(r, filt(MEDS, d, pl.melee)).t;
        else if (field === 'gear') pl.gear = pick(r, filt(GEAR, d, pl.melee)).t;
      }
    }
    fixRules(r, m);
    m.points = score(m);
    return m;
  }

  // Napi kihívás: a dátumból jön a seed, így mindenkinek ugyanaz.
  function daily(dateStr) {
    const m = generate({ diff: 2, players: 1, seed: hashStr('tarkov-hc-' + dateStr) });
    m.daily = dateStr;
    m.rerollsLeft = 0;
    return m;
  }

  const RANKS = [
    [0, 'Timmy', '🐣'], [150, 'Patkány', '🐀'], [500, 'Túlélő', '🩹'], [1200, 'Raider', '🎯'],
    [2500, 'Veterán', '🎖️'], [5000, 'Gigachad', '🗿'], [10000, 'Kappa', '🏆'], [20000, 'Tarkov isten', '☠️'],
  ];
  function rank(points) {
    let cur = RANKS[0], next = null;
    for (let i = 0; i < RANKS.length; i++) { if (points >= RANKS[i][0]) { cur = RANKS[i]; next = RANKS[i + 1] || null; } }
    return { name: cur[1], icon: cur[2], min: cur[0], next: next ? { name: next[1], at: next[0] } : null };
  }

  const API = { DIFFS, MAPS, WEAPONS, RULES, PUNISH, OBJECTIVES, generate, reroll, daily, score, rank, rng, hashStr, _filt: filt };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.TGen = API;
})(typeof window !== 'undefined' ? window : globalThis);
