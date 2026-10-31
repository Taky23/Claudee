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
| `RunnerCars`, `CopCars` | a kocsik listája (GTA V jármű-nevek, pl. `sultan`, `police3`) |
| `Scenarios` | helyszínek: a menekülő és a rendőrök kezdőpontja |

**Saját helyszín:** állj oda kocsival, írd be: `/chasepos`, és a kiírt `{ x = …, y = …, z = …, h = … }` sort másold a `Scenarios` listába, egy új bejegyzésbe.
A beépített két helyszín (belváros, Sandy Shores) koordinátái közelítőek. Ha valamelyiknél rossz helyre spawnol a kocsi, a `/chasepos` paranccsal pontosítsd.

## Saját autók (modok)
Bármilyen add-on autó-resource mehet a `resources` mappába (`ensure` sorral a `server.cfg`-ben). Utána a kocsi nevét írd be a `RunnerCars` vagy a `CopCars` listába. A handlingjét a kocsi saját `handling.meta` fájljában lehet állítani. Ebben is segítek, ha kell.

## Tesztelés
A játéklogikát (füst, kiszállás, időlimit, kilépés, rendőr-jelzések) kamu FiveM-környezetben szimulálja a `teszt/szimulacio.py`:
`pip install lupa pytest`, majd `python -m pytest fivem-chase/teszt/szimulacio.py`.
