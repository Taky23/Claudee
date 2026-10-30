# 🧌🎒 Loot Goblinok – saját DayZ szerver (Chernarus, max. 5 fő)

A saját gépedről futó, modolt DayZ szerver telepítője és beállítója.

## Mit tud

| | |
|---|---|
| 🏪 **Green Mountain kereskedőzóna** | Az Expansion kész kereskedőhelye (fegyver, ruha, kaja, alkatrész, építőanyag, ATM-ek), kivilágítva, biztonsági zónával és térképjelölővel. Az autókereskedőnél: **Ada 4x4, Olga 24, Gunter 2, Sarka 120, M3S, M1025**. |
| 🕵️ **Titkos Black Market** | Északon, a Tisy–Sinystok közti erdőben. **Nem látszik a térképen**, csak készpénzzel lehet fizetni. Kínálat: **Gyrocopter, MH-6, UH-1H, Merlin**, a **Helicopter pack** helijei, valamint a különleges autók (Nissan GTR, Skyline R34, Audi RSQ8, m3gtr). |
| 🔑 **Járműkulcsok** | A megvett jármű zárva kerül ki a lerakóhelyre, és a vevő kulcsot kap hozzá. Csak a saját kulcsa nyitja, zárja és indítja, feltörni nem lehet. Egy **üres (párosítatlan) kulcs** hozzápárosítható egy gazdátlan, még kulcs nélküli járműhöz. |
| 🏧 **ATM** | Pénz feltöltése és levétele. A bankszámla újraindítás után is megmarad. Vásárolni csak a nálad lévő készpénzzel lehet. |
| 🤖 **AI katonák** | **Csak katonai helyeken** és **reptereken**. Délen kevesebb (1–2), északon több (2–4), a reptereken +2. Jól látható piros ruhát és láthatósági mellényt viselnek. Közepes célzás, kicsit gyengített sebzés. |
| 🎯 **Modok** | Fegyverek: SNAFU Weapons (plusz opcionálisan a .50-es Barrett a Mortys Weaponsből). Tarkovos ruhák, mellények, táskák, gyűjthető tárgyak (Escape From Tarkov mod). Expansion járművek. |
| 🛠️ **Admin** | VPP Admin Tools: teleport, tárgy- és jármű-lehívás, pozíció kiolvasása. |

## Mi kell hozzá
- Windows, legalább 16 GB RAM (32 GB-tal kényelmes, ha a gépen játszol is)
- **DayZ** a Steamen (a fiókodnak birtokolnia kell, mert csak így tölthetők le a szerver és a modok)
- **Python 3.10 vagy újabb**: [python.org](https://www.python.org/downloads/). Telepítéskor pipáld be az **Add python.exe to PATH** opciót.

**A DayZ Servert és a modokat a telepítő magától letölti** a Steam hivatalos letöltőjével (SteamCMD). Feliratkozni nem kell, és a DayZ Servert sem kell kézzel telepíteni.

## 1. A modok Workshop-linkjei
A `beallitasok.json` → `modok` listában minden modnál van egy `workshop` mező. Ide kell a mod Workshop-linkje vagy azonosítója (a link végén lévő `?id=` utáni szám). Nyisd meg a mod oldalát a Steamben, jobb klikk → **Oldal URL-jének másolása**, és illeszd be:
```json
{ "nev": "SNAFUWeapons", "minta": "snafu", "loot": true, "workshop": "https://steamcommunity.com/sharedfiles/filedetails/?id=…" },
```
A telepítő ellenőrzi, hogy a link tényleg ahhoz a modhoz tartozik-e. Ha nem, nem tölt le semmit, és szól.

| Mod | Megjegyzés |
|---|---|
| **CF** (Community Framework) | kötelező alap (azonosítója már be van írva) |
| **Dabs Framework** | kötelező alap |
| **VPPAdminTools** | admin eszköz |
| **DayZ-Expansion-Licensed** | Expansion alap |
| **DayZ-Expansion-Bundle** | Expansion: kereskedők, ATM, AI, térkép, … |
| **DayZ-Expansion-Vehicles** | a helikopterek miatt (azonosítója már be van írva) |
| **Escape From Tarkov** | Tarkovos tárgyak |
| **SNAFU Weapons** | fegyverek (modern katonai fegyverek, mesterlövészpuskák) |
| **Mortys Weapons** | nem kötelező: .50-es Barrett M82A1 |
| **Bandits Nissan GTR Limit**, **Nissan Skyline GT-R R34**, **Audi RSQ8 Mansory**, **m3gtr** | nem kötelező: a BM különleges autói |
| **Helicopter pack** (KillSwitch / SIBNIC) | nem kötelező: további helik a BM-be. **Kell hozzá a szerveroldali része is**, lásd lent. |

Amelyik modnál üresen hagyod a `workshop` mezőt, azt a telepítő a DayZ `!Workshop` mappájában keresi, vagyis ott is működik, ha előtte kézzel feliratkoztál rá.

> ⚠️ Az Escape From Tarkov mod utoljára 2022-ben frissült, ezért előfordulhat, hogy a mostani DayZ-vel már nem működik. Ha a szerver miatta nem indul, vedd ki a `beallitasok.json` → `modok` listából.

**A haveroknak nem kell semmit előre letölteniük:** amikor a DayZ launcherben csatlakoznak a szerverhez, a launcher felajánlja a hiányzó modok letöltését.

### A Helicopter pack szerveroldali része
A Helicopter pack leírása szerint a szerverre kell egy **[Server_Side]** mod is, amit a készítő oldaláról ([sibnic.info](https://sibnic.info)) lehet letölteni, a Workshopon nincs fent. Töltsd le, csomagold ki, és a benne lévő `@…` mappát tedd ide: `dayz-szerver/szerver_modok/`. A telepítő megtalálja, és szerveroldali modként (`-serverMod`) tölti be. A játékosoknak ezt nem kell letölteniük. Ha a mappa nevében nincs benne, hogy „sibnic”, nevezd át pl. `@SibnicServer`-re.

## 2. Beállítások
Nyisd meg a `beallitasok.json` fájlt (pl. Jegyzettömbbel):
- `superadminok_steam64`: írd be a saját **Steam64 azonosítódat**, egy 17 jegyű számot, ami 7656-tal kezdődik. Steamben a profilodon: jobb klikk → **Steam URL másolása**, vagy a [steamid.io](https://steamid.io) oldalon.
- `steam_felhasznalo`: a Steam **bejelentkezési neved** (nem a becenév). Ha üresen hagyod, a telepítő megkérdezi.
- `szerver → jelszo`: ezzel tudnak belépni a haverok. Ha üresen hagyod, bárki beléphet.

A telepítő a Steam64 azonosítódat a VPP Admin Tools superadmin listájába írja (`profiles/VPPAdminTools/Permissions/SuperAdmins/SuperAdmins.txt`). Ha belépés után mégsem éred el az admin menüt, szólj, és megnézzük.

## 3. Telepítés
A `dayz-szerver` mappában kattints a címsorba, írd be, hogy `cmd`, és nyomj Entert. A megnyíló ablakba:
```
python goblin.py telepit
```
Ez megcsinálja:
- letölti a SteamCMD-t, azzal a **DayZ Servert** (ha még nincs meg) és a **modokat**. Első alkalommal a SteamCMD **kéri a Steam jelszavadat és a Steam Guard kódot**, ezeket ott, a fekete ablakban kell beírnod (a jelszó gépelés közben nem látszik). A jelszót a program nem menti, a bejelentkezést a SteamCMD maga jegyzi meg;
- a modokat és kulcsaikat átmásolja a szerverhez;
- összerakja a küldetést (mission) az Expansion hivatalos sablonjából;
- megírja a `serverDZ.cfg`-t és az `inditas.bat`-ot a szerver mappájába;
- generál egy admin jelszót, és elmenti a `beallitasok.json`-ba.

Ha a DayZ Server a Steamben már telepítve van, azt használja. Ha nincs, a `dayz-szerver/DayZServer` mappába kerül.

**Ha nem szeretnéd megadni a Steam jelszavad a SteamCMD-nek:** iratkozz fel a modokra a Workshopon, és indítsd el egyszer a DayZ-t, hogy letöltse őket. Telepítsd a DayZ Servert a Steamből (Könyvtár → Eszközök → DayZ Server), majd futtasd: `python goblin.py telepit --steam-nelkul`.

**Frissítés** (ha frissül a DayZ vagy egy mod): `python goblin.py frissit`. Ez mindent újratölt, és újra összerak. Teljesen tiszta küldetéshez: `python goblin.py telepit --ujra`.

## 4. Router: port nyitás (hogy a haverok is be tudjanak lépni)
A router beállításaiban (általában `192.168.0.1` vagy `192.168.1.1`) a **Port Forwarding / Porttovábbítás** menüben irányítsd a gépedre:
- **UDP 2302–2305**
- **UDP 27016**

Az első indításkor a Windows tűzfal rákérdez: **Engedélyezés**. A haverok a **nyilvános IP-címeddel** csatlakoznak (pl. a [whatismyip.com](https://www.whatismyip.com) mutatja), te magad pedig a `127.0.0.1:2302` címmel.

## 5. Első indítás
1. A DayZ Server mappájában (a telepítő a végén kiírja, hol van) indítsd el az `inditas.bat`-ot. Az első betöltés pár percig tart.
2. Amikor a szerver betöltött (a DayZ launcherben megjelenik), állítsd le: zárd be az ablakot, vagy Ctrl+C, majd I.
3. Ekkor az Expansion legenerálta a saját beállításait. Futtasd:
```
python goblin.py testreszab
```
4. Indítsd újra az `inditas.bat`-ot.

A `testreszab` bármikor újrafuttatható, de **csak leállított szervernél**. Ugyanazt nem írja be kétszer.

## 6. A Black Market helyének beállítása (közösen)
1. Lépj be a szerverre, nyisd meg a **VPP admin menüt**, és teleportálj a Tisy és Sinystok közti erdőbe.
2. Keresd meg a helyet. A VPP Teleport menüje mutatja az aktuális pozíciódat, onnan kimásolhatod. A `beallitasok.json` → `black_market` részbe ezek kellenek:
   - `helyzet`: ahol a kereskedő álljon, pl. `"1520.3 297.4 13912.8"`;
   - `irany`: merre nézzen, 0–360 fokban;
   - `jarmu_lerako`: sík, fáktól mentes hely **100 méteren belül**, ide kerülnek a megvett autók;
   - `heli_lerako`: nagyobb tisztás 100 méteren belül, ide kerülnek a helik.
3. Állítsd le a szervert → `python goblin.py testreszab` → indítás.

Ha nem vagy biztos a koordinátákban, küldd el őket, és megnézem.

## 7. A különleges autók osztálynevei
A BM-be a modolt autókat az osztálynevükkel (classname) lehet felvenni. Ezt így találod meg:
```
python goblin.py keres GTR
python goblin.py keres Skyline
python goblin.py keres RSQ8
python goblin.py keres m3gtr
python goblin.py keres heli
```
A listában általában a legrövidebb, a mod nevével kezdődő név a jármű. Írd be a `beallitasok.json` → `black_market` → `autok` (a helikopter-csomag helijeinél: `helik`) → `osztaly` mezőbe, majd `testreszab`. A helikopter-csomagból annyi helit veszel fel, ahányat akarsz: a listában 3 hely van, de bővíthető vagy törölhető. Ugyanígy működik a VPP tárgy-lehívó keresője is: ha ott lehív egy autót, látszik a neve.

Bármilyen fegyvert vagy tárgyat (pl. SNAFU-s mesterlövészpuskát) a BM-be az `egyeb` listában adhatsz meg: `{ "nev": "Barrett", "osztaly": "…", "ar": [100000, 200000] }`.

## Finomhangolás (`beallitasok.json` → `ai`)
| Mező | Jelentés |
|---|---|
| `del`, `eszak` | AI létszám (min, max) a déli és az északi katonai helyeken |
| `repter_plusz` | ennyivel több AI a reptereken |
| `pontossag` | célzás 0–1 között (alap: 0,25–0,5) |
| `sebzes_szorzo` | mennyit sebeznek (alap 0,8, vagyis kicsit gyengébbek) |
| `ujraeledes_perc` | a kiirtott csapat ennyi perc múlva tér vissza |

## Ha valami nem megy
- A szerver naplói a DayZ Server mappájában, a `profiles` mappában vannak (`*.RPT`, `*.log`, illetve `ExpansionMod/Logs`). Ha hiba van, küldd el az utolsó RPT-fájl végét.
- Az első indítás után a koordináták (pl. a fények vagy a lerakóhelyek) finomhangolást igényelhetnek. Ez normális, ezeket együtt igazítjuk.

## Őszintén a korlátokról
A beállításokat az Expansion aktuális forráskódja és hivatalos sablonjai alapján írtam, és automatikus tesztekkel ellenőriztem. **Játékon belül viszont nem tudtam kipróbálni**, ezért az első indításnál számíts kisebb igazításokra.
