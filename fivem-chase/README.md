# 🏎️🚓 Goblin Chase – FiveM üldözős szerver

Egy menekülő, a többiek rendőrök. **Ha a menekülő kocsijának motorja füstölni kezd, vége az üldözésnek: a rendőrök nyertek.**
Ha a menekülő kibírja az időt (alapból 10 perc), ő nyer.

## A szabályok
- **Kezdés:** mindenki kocsit kap, 5 mp visszaszámlálás. A menekülő indul, a rendőrök **10 mp-cel később**.
- **🚓 A rendőrök nyernek, ha a menekülő**
  - kocsijának motorja **füstölni kezd** (a motor „egészsége” 400 alá esik),
  - kocsija tönkremegy, vagy ő meghal,
  - **10 mp-nél tovább kint van** a kocsijából,
  - kilép a szerverről.
- **🏁 A menekülő nyer**, ha kibírja az időt.
- A képernyőn látszik a szerep, a hátralévő idő, a menekülőnek pedig a **motor állapota** (100% → 0% = füst).
- A rendőrök 20 mp-enként egy piros kört kapnak a térképen arról, merre jár nagyjából a menekülő.
- Az NPC-rendőrök nem szólnak bele, és a forgalom ritkább.

## Parancsok (a chatbe, T billentyű)
| Parancs | Mit csinál |
|---|---|
| `/chase` | Üldözés indítása: véletlen menekülő, véletlen helyszín |
| `/chase 3` | A 3-as számú játékos lesz a menekülő |
| `/chase 0 sivatag` | Véletlen menekülő, a „sivatag” helyszínen |
| `/chasestop` | A futó üldözés leállítása |
| `/chasepos` | Kiírja, hol állsz (saját helyszín felvételéhez) |

## Telepítés (Windows)
Mindenkinek kell **saját, legális GTA V** és a **FiveM** kliens ([fivem.net](https://fivem.net)).

1. **Szerverprogram:** töltsd le a legfrissebb ajánlott (Recommended) Windows-szervert:
   https://runtime.fivem.net/artifacts/fivem/build_server_windows/master/
   Csomagold ki egy új mappába, pl. `C:\FiveM\server`.
2. Indítsd el a mappában a **`FXServer.exe`**-t. Megnyílik a böngészőben a **txAdmin** (`http://localhost:40120`).
3. A txAdminban:
   - jelentkezz be a **Cfx.re** fiókoddal (ha nincs, ott regisztrálhatsz);
   - válaszd a **„Popular Recipes” → „CFX Default”** szervert;
   - kérni fog egy **licenckulcsot**: a [portal.cfx.re](https://portal.cfx.re) oldalon → **Server Registration Keys** → új kulcs (ingyenes) → másold be.
4. Ha a txAdmin felrakta az alap szervert, másold a **`goblin_chase`** mappát a szerver **`resources`** mappájába (a txAdmin kiírja, hol van, általában `txData\…\resources`).
5. A txAdminban: **CFG Editor** → a `server.cfg` végére írd be: `ensure goblin_chase` → **Save** → **Restart Server**.
6. **Belépés:** FiveM → F8 → írd be: `connect localhost:30120`

**A haveroknak:** a routeren a **30120-as portot (TCP és UDP)** kell a gépedre irányítani. Ők a nyilvános IP-címeddel csatlakoznak: `connect <IP>:30120`.

## Beállítás (`goblin_chase/config.lua`)
| Mező | Jelentés |
|---|---|
| `SmokeThreshold` | ez alatt a motor-érték alatt füstöl (alap 400; nagyobb szám = hamarabb vége) |
| `RoundTime` | ennyi másodpercig kell kibírnia a menekülőnek |
| `HeadStart` | ennyi másodperc előnyt kap a menekülő |
| `OutOfCarSeconds` | ennyi ideig lehet kint a kocsiból |
| `PingInterval` | ilyen gyakran látják a rendőrök a menekülő környékét (0 = soha) |
| `Traffic` | forgalom sűrűsége (0 = üres utak) |
| `Cars` | a kocsik listája (ugyanaz a menekülőknek és a rendőröknek) |
| `RunnerColor`, `CopColor` | a színek (RGB): fekete és sötétkék |
| `MaxSpeedKmh` | fix végsebesség minden kocsinak (km/h) |
| `Scenarios` | helyszínek: a menekülő és a rendőrök kezdőpontja |

**Saját helyszín:** állj oda kocsival, írd be: `/chasepos`, és a kiírt `{ x = …, y = …, z = …, h = … }` sort másold a `Scenarios` listába, egy új bejegyzésbe.
A beépített két helyszín (belváros, Sandy Shores) koordinátái közelítőek. Ha valamelyiknél rossz helyre spawnol a kocsi, a `/chasepos` paranccsal pontosítsd.

## 🏎️ Handling: más-más kocsik, fix végsebesség
A játékmód minden üldözős kocsira **indításkor ráteszi a saját handlingjét**, így nem kell a kocsik fájljaihoz nyúlni.
- **Fix végsebesség:** `Config.MaxSpeedKmh` (alap: **180 km/h**). Ennél egyik kocsi sem megy gyorsabban, és mindegyik el is éri.
- **Közös alap** (`Config.HandlingBase`): tömeg, gyorsulás, tapadás, fék, kormány. Ettől lesznek a kocsik hasonlóak.
- **Profilok** (`Config.HandlingProfiles`): kis eltérések az alaphoz képest (legfeljebb kb. ±15%, a „nehéz” tömege +35%):

| Profil | Milyen |
|---|---|
| Kiegyensúlyozott | az alap |
| Gyorsuló | jobban gyorsul, kicsit csúszósabb |
| Tapadós | jobban fog a kanyarban, kicsit lassabban gyorsul |
| Nehéz | nehezebb, jobban tol ütközésnél, kicsit lomhább |
| Fordulékony | élesebben fordul, jobban fékez, könnyebb |

- **Melyik kocsi melyik profil:** `Config.CarProfiles`, pl. `sultan = 'tapados'`. Ami nincs a listában, az a kiegyensúlyozottat kapja.
- **A motor sérülése mindenkinél egyforma** (`fEngineDamageMult`), így a „füst” szabály igazságos: egyik kocsi sem bírja jobban az ütést.

## 🚗 Az autók: ugyanazok mindenkinek, más színben
Nincs külön rendőrautó: **mindenki ugyanabból a listából kap kocsit**. A menekülőé **fekete** (rendszám: GOBLIN), a rendőröké **sötétkék** (rendszám: RENDOR).

| Autó | Modellnév (ellenőrizendő) | Miben jó | Mivel fizet érte |
|---|---|---|---|
| 2020 Bugatti Bolide | `bolide` | tapadás, fék | könnyű: ütközésnél könnyen ellökik |
| Koenigsegg Jesko | `jesko` | ő gyorsul a legjobban | kanyarban hamarabb megcsúszik |
| BMW M3 Competition | `m3comp` | fordulékony, jól irányítható | kicsit „driftes”, gyorsulásban átlagos |
| 2021 Audi RS Q3 (Prior Design) | `rsq3` | nehéz: ütközésben ő tol a legjobban | lomhább, hosszabb fékút |

A fix 180 km/h végsebesség mindegyikre vonatkozik, így egyik sem húz el a többi elől, csak máshogy viselkedik.

**Telepítés kocsinként:**
1. Töltsd le a GTA V-s **FiveM / Add-On** változatát, és a mappáját másold a szerver `resources` mappájába (pl. `resources\[autok]\jesko`).
2. A `server.cfg`-be (txAdmin → CFG Editor): `ensure jesko` (a mappa nevével).
3. A kocsi mappájában lévő `vehicles.meta`-ban nézd meg a `<modelName>` sort. Ha más, mint a táblázatban, írd át a `config.lua`-ban a `Config.Cars` és a `Config.CarProfiles` sorban (vagy küldd el, és átírom).

Ha egy kocsi nincs telepítve, vagy más a neve, a játékos helyette egy **Sultant** kap a szerepének megfelelő színben, és a képernyőn szól erről. Az üldözés így nem akad el.

## Saját autók (modok) berakása
1. **Tölts le egy FiveM-hez készült autót** (pl. a [gta5-mods.com](https://www.gta5-mods.com)-ról, „FiveM ready” / „Add-On”). Csak olyat használj, amit a készítője engedélyez szerveren. A fizetős autók „leakelt” változata tilos.
2. Az autó általában egy kész mappa: benne egy `fxmanifest.lua`, egy `stream` mappa (a modell) és `.meta` fájlok. Másold a szerver **`resources`** mappájába, pl. `resources\[autok]\skyline`.
   Ha nincs benne `fxmanifest.lua`, szólj, és megírom hozzá.
3. A txAdmin **CFG Editor**-ában adj hozzá egy sort: `ensure skyline` (a mappa nevével) → Save → Restart.
4. Keresd meg a **modell nevét**: a `vehicles.meta` fájlban a `<modelName>` sorban (pl. `<modelName>r34</modelName>`).
5. A `goblin_chase/config.lua`-ban:
   - írd be a nevét a `RunnerCars` (vagy `CopCars`) listába: `Config.RunnerCars = { 'sultan', 'r34', ... }`
   - és adj neki profilt: `r34 = 'gyorsulo',` a `Config.CarProfiles` listában.
6. Restart, és jöhet a `/chase`.

## Tesztelés
A játéklogikát (füst, kiszállás, időlimit, kilépés, rendőr-jelzések) kamu FiveM-környezetben szimulálja a `teszt/szimulacio.py`:
`pip install lupa pytest`, majd `python -m pytest fivem-chase/teszt/szimulacio.py`.
