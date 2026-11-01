/* Tarkov Kihívás adatbázis. Minden elemnek van egy `d` szintje:
   1 = Könnyű, 2 = Nehéz, 3 = HC, 4 = Insane.
   A generátor a kiválasztott szinten és alatta lévő elemekből válogat (a felsőbb szint a nehezebbeket is hozza). */
window.TARKOV = {
  szintek: [
    { id: 1, nev: 'Könnyű', emoji: '🟢', szin: '#8bc34a', extra: [1, 1], leiras: 'Laza menet, egy-két szabály.' },
    { id: 2, nev: 'Nehéz', emoji: '🟡', szin: '#ffb300', extra: [2, 3], leiras: 'Komolyabb megkötések, több szabály.' },
    { id: 3, nev: 'HC', emoji: '🟠', szin: '#ff6d00', extra: [3, 4], leiras: 'Hardcore: kevés felszerelés, kemény feltételek.' },
    { id: 4, nev: 'Insane', emoji: '🔴', szin: '#e53935', extra: [4, 5], leiras: 'Őrület. Csak a legbátrabbaknak.' },
  ],

  // Pályák
  palyak: [
    { nev: 'Customs', d: 1 }, { nev: 'Factory', d: 1 }, { nev: 'Woods', d: 1 },
    { nev: 'Interchange', d: 1 }, { nev: 'Shoreline', d: 1 }, { nev: 'Reserve', d: 2 },
    { nev: 'Lighthouse', d: 2 }, { nev: 'Streets of Tarkov', d: 2 }, { nev: 'Ground Zero', d: 1 },
    { nev: 'The Lab', d: 3 }, { nev: 'Night Factory (éjjel)', d: 3 },
  ],

  // Fő feladat – ez a menet célja
  celok: [
    { t: 'Hozz ki legalább 1 értékes lootot (>50k) és extractolj élve.', d: 1 },
    { t: 'Ölj meg 2 Scavot, aztán extractolj.', d: 1 },
    { t: 'Látogass meg egy loot-helyet (Marked Room, Dorms, stb.), és gyere ki.', d: 1 },
    { t: 'Teljesíts egy aktív kill-questedet ezen a pályán.', d: 1 },
    { t: 'Ölj meg 1 PMC-t, és vedd fel a dogtagját.', d: 2 },
    { t: 'Nyiss ki egy zárt ajtót kulccsal, és lootold ki a szobát.', d: 2 },
    { t: 'Teljesíts egy place-item (jelzőrakás) questet, vagy tégy úgy, mintha.', d: 2 },
    { t: 'Ölj meg 3 PMC-t egy raid alatt.', d: 3 },
    { t: 'Öld meg a pálya bosszát (vagy a goonst, ha ott vannak).', d: 3 },
    { t: 'Fejezd be a raidet úgy, hogy a táskád tele van loottal (minden slot foglalt).', d: 3 },
    { t: 'Ölj meg egy PMC-t közelharcban (kés vagy ököl).', d: 4 },
    { t: 'Juss ki élve úgy, hogy a raid elején ELADTAD a fegyvered (üres kézzel kezdesz).', d: 4 },
    { t: 'Öld meg a bosszt CSAK pisztollyal.', d: 4 },
  ],

  // Fegyver / felszerelés megkötés
  fegyverek: [
    { t: 'Bármilyen fegyver mehet.', d: 1 },
    { t: 'Csak shotgun (sörétes).', d: 1 },
    { t: 'Csak pisztoly (másodlagos nincs).', d: 2 },
    { t: 'Csak 7.62x39 kaliber (pl. AKM).', d: 1 },
    { t: 'Csak 5.45x39 kaliber (pl. AK-74).', d: 1 },
    { t: 'Csak SMG (géppisztoly).', d: 2 },
    { t: 'Csak bolt-action mesterlövészpuska.', d: 2 },
    { t: 'Csak marksman puska (féautomata DMR).', d: 2 },
    { t: 'Egyetlen tár! Újratöltés csak a raidben felszedett lőszerrel.', d: 3 },
    { t: 'Csak kés / közelharci fegyver.', d: 3 },
    { t: 'Csak olyan fegyver, amit a raidben szedsz fel (üres kézzel kezdesz).', d: 4 },
    { t: 'Csak flea-ről vett legolcsóbb fegyver, mod nélkül.', d: 3 },
    { t: 'Csak a traderek szintje 1 fegyvere és lőszere.', d: 3 },
    { t: 'Makarov PM és semmi más fegyver.', d: 4 },
  ],

  // Páncél / mellény / felszerelés
  pancelok: [
    { t: 'Bármilyen páncél mehet.', d: 1 },
    { t: 'Maximum 4-es szintű páncél.', d: 1 },
    { t: 'Maximum 3-as szintű páncél.', d: 2 },
    { t: 'Nincs páncél (csak rig).', d: 3 },
    { t: 'Nincs sisak.', d: 2 },
    { t: 'Nincs sem páncél, sem sisak (pizsama run).', d: 4 },
    { t: 'Csak Scav-szintű cucc: semmi vásárolt páncél.', d: 3 },
  ],

  // Extra szabályok – ezekből a nehézség szerint több jön
  extrak: [
    { t: 'Nem használhatsz gyógyszert, amíg nincs 1 kill.', d: 1 },
    { t: 'Tilos a sprint (futás) az első 5 percben.', d: 1 },
    { t: 'Nem vehetsz fel másik fegyvert a földről.', d: 1 },
    { t: 'Minden Scavot meg kell ölnöd, akit látsz.', d: 2 },
    { t: 'Csak guggolva vagy fekve közlekedhetsz épületben.', d: 2 },
    { t: 'Nem használhatsz headsetet (fülhallgatót).', d: 2 },
    { t: 'Tilos a flea market: csak traderről vett cuccal mehetsz be.', d: 2 },
    { t: 'Nincs térkép-appozás raid közben (fejből navigálj).', d: 2 },
    { t: 'Ha megsebesülsz, azonnal a legközelebbi extract felé indulsz.', d: 3 },
    { t: 'Nem ihatsz/ehetsz a raid alatt.', d: 3 },
    { t: 'Egy stim sem (nincs injekció).', d: 3 },
    { t: 'Csak akkor lőhetsz, ha rád lőttek előbb.', d: 3 },
    { t: 'Nem gyógyíthatod a végtagjaidat (blacked limbekkel kell kijönni).', d: 4 },
    { t: 'Nincs mini-térkép, nincs offline guide, semmi segítség.', d: 4 },
    { t: 'Egyetlen életed van: ha meghalsz, aznap nincs több Tarkov.', d: 4 },
    { t: 'Végig night vision NÉLKÜL, ha éjszakai raid.', d: 3 },
    { t: 'Nem használhatsz gránátot.', d: 1 },
  ],

  // Secure container / stash megkötés
  secure: [
    { t: 'Secure container bármire használható.', d: 1 },
    { t: 'A secure containerbe CSAK quest-itemet tehetsz.', d: 2 },
    { t: 'Üres secure container: semmit nem tehetsz bele a raid alatt.', d: 3 },
    { t: 'Kis secure (Alpha/Beta méret) szabály: képzeld el, hogy csak 4 slotod van.', d: 3 },
    { t: 'Amit kihozol, annak a táskában kell lennie – a secure nem számít.', d: 4 },
  ],

  // Transit (átjárós) kihívás-láncok – külön kapcsolóval. Scav-free, új mechanika.
  transit: [
    { t: 'Indulj Customsról, menj át transittal Streetsre, és ott extractolj.', d: 2 },
    { t: 'Ground Zero → transit Streetsre → ölj meg 1 PMC-t → extract.', d: 2 },
    { t: 'Interchange-en transitolj át Customsra, és old meg a Goonst ott.', d: 3 },
    { t: 'Streets → transit Groud Zero-ra loottal a táskádban, utána extract.', d: 2 },
    { t: 'Lighthouse → transit Shoreline-ra, látogasd meg a Resortot, extract.', d: 3 },
    { t: 'Két transit egy „életben”: A → B → C pályán át, mindháromban legyen 1 kill.', d: 4 },
    { t: 'Transittal érkezz egy pályára üres kézzel, ott szedj fel mindent, és menj ki élve.', d: 4 },
    { t: 'Customs → transit Streetsre → teljesíts egy aktív questet Streetsen → extract.', d: 3 },
  ],

  // Opcionális hangulat / plusz cél, random ízesítőnek
  izek: [
    'Ha túléled, jutalom: 1 kedvenc skin/matrica a következő vásárláskor. 🎁',
    'Vedd fel, ha tudod (klip a #🏆 szobába)! 🎥',
    'Mondd el a haveroknak a raid végén, mi történt. 🎙️',
    'Ha elbuksz, a következő raidet ugyanígy próbáld újra. 🔁',
    'Bónusz pont, ha közben valakit megmentesz (co-op). 🤝',
  ],
};
