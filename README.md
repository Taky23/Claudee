# 🔪 Rejtély bot

Discord bot két játékkal:

- **Gyilkossági rejtély** – egy titkos gyilkos, nyomozás, nyomok és szavazás, napokig is tartó szerverjátékként.
- **Időkapszula** – üzenet a jövőnek, amit a bot a megadott időben kiposztol.

## 🔪 Gyilkossági rejtély

Valaki közületek gyilkos. Éjjel lecsap, nappal köztetek mosolyog.

**Szerepek**

| Szerep | Mit csinál éjjel |
|---|---|
| 🔪 Gyilkos | Kiválaszt egy áldozatot. Éjjelente egyszer névtelenül suttoghat a csatornába. |
| 🕵️ Detektív | Kihallgat valakit, és megtudja, ő-e a gyilkos. |
| 🩺 Orvos | Megvéd valakit (akár magát). 5 játékostól van a játékban. |
| 🙂 Civil | Semmit – de nappal az ő szavazata is dönt. |

**A csavar: nyomok.** Mindenkinek van három ismertetőjegye (🍷 ital, 👃 illat, 🧤 tárgy), ezeket mindenki látja.
Minden gyilkosság után a tetthelyen előkerül a gyilkos egyik ismertetőjegye. Egy nyom sosem elég, mert
mindegyik legalább még egy ártatlanra is illik – a nyomokat együtt kell összerakni.

**Menet:** 🌙 éjszaka (titkos akciók) → ☀️ nappal (halott + új nyom, vita, szavazás) → ismétlés.
A **város** nyer, ha kivégzi a gyilkost. A **gyilkos** nyer, ha már csak egy ártatlan él.

A játék végén a bot magától lezár egy **időkapszulát**, ami pontosan egy év múlva emlékeztet a játékra. 📜

### Parancsok

| Parancs | Leírás |
|---|---|
| `/rejtely uj` | Jelentkezés indítása (állítható az éjszaka és nappal hossza; lassú játékhoz pl. `nappal_perc: 1440`) |
| `/rejtely akcio` | Éjszakai akció – csak te látod. A civilek is használják, hogy senki ne lógjon ki. |
| `/rejtely suttogas` | Gyilkosként névtelen üzenet a csatornába |
| `/rejtely szavaz` | Nappali szavazás (célpont nélkül = senkit ne végezzünk ki) |
| `/rejtely allas` | Nyomok, élő játékosok, szavazatok |
| `/rejtely szabalyok` | Szabályok |
| `/rejtely tovabb` | (Házigazda) fázis azonnali lezárása |
| `/rejtely leallit` | (Házigazda) játék leállítása |

## 📜 Időkapszula

| Parancs | Leírás |
|---|---|
| `/idokapszula lezar` | Üzenet lezárása. Idő: `30 perc`, `3 nap`, `2 hét`, `6 hónap`, `1 év`, `1év 2hónap`, `2027-01-01 18:00` |
| `/idokapszula listam` | A saját lezárt kapszuláid |
| `/idokapszula torol` | Saját kapszula törlése |
| `/idokapszula sugo` | Súgó |

## 📱 Telefonos webappok (Discord nélkül)

A `web/` mappában nyolc telepíthető webapp (PWA) van. A kezdőképernyőre kitéve appként futnak, offline is működnek, és az állást a telefonon tárolják.

- **🎲 Véletlen kaland** (`web/kaland/`) – egy gombnyomásra apró, fura napi küldetést kapsz. Naponta kétszer kérhetsz helyette másikat, utána jöhetnek a bónuszküldetések. Fotót és jegyzetet is csatolhatsz. Pontokat, szinteket, szériát és 22 jelvényt gyűjthetsz, a teljesítéseid a kalandnaplóba kerülnek.
- **🕵️ Zsebdetektív** (`web/detektiv/`) – minden nap egy új rejtély öt gyanúsítottal és nyomokkal. A napi eset mindenkinek ugyanaz, így a barátaiddal is összemérhetitek. A nyomok együtt mindig pontosan egy tettest adnak ki. Két nyom ingyenes, minden további pontba kerül, és csak egyszer vádolhatsz. Van pont nélküli gyakorló mód és statisztika is.

- **🩸 A Kód** (`web/kod/`) – Dexter-szerű, korlátlanul játszható igazságosztó-játék. Minden játékbeli nap egy akta: a nyomokból kell kiválasztanod a valódi tettest (ha ártatlant választasz, vége), aztán egy olyan időpontot és helyszínt, ahol nincs tanú. Minden extra nyom és felderítés növeli Bakó őrmester gyanúját, és 100%-nál lebuksz. A játék addig tart, amíg le nem buksz, a nehézség napról napra nő. A túlélt napokból top 10-es ranglista készül a telefonon.

- **🎯 Tarkov Segéd** (`web/tarkov/`) – Escape from Tarkov segédapp a [tarkov.dev](https://tarkov.dev) nyilvános API-jával:
  - **Árak:** élő flea ár (legolcsóbb és 24 órás átlag, 48 órás változás), legjobb trader ár, rekeszenkénti érték, és hogy flea-n vagy traderen érdemes-e eladni (a flea díjjal számolva). Szól, ha a tárgy még kell a questjeidhez vagy a hideoutodhoz. Kedvencekkel.
  - **Lőszer:** kaliberenkénti táblázat sebzéssel, átütéssel, páncélsebzéssel, fragmentációval és árral.
  - **Questek:** traderenként, Kappa-szűrővel, keresővel és pipálható haladással.
  - **Hideout:** az állomások szintjeinek követése, és az összes hiányzó tárgy listája becsült költséggel.
  - **Idő:** Tarkov idő (bal/jobb), trader restock visszaszámláló, PvP/PvE mód, angol vagy magyar tárgynevek.

- **🎮 Gamer Zseb** (`web/gamer/`) – két dolog egy appban:
  - **Játékár-figyelő** a [CheapShark](https://www.cheapshark.com) ingyenes API-jával: akciók boltok szerint (Steam, Epic, GOG, Humble…), ingyen játékok, keresés, egy játék összes boltban elérhető ára és a valaha volt legalacsonyabb ára, figyelőlista célárral, valamint opcionális email-riasztás a CheapShark-on keresztül. Az utoljára letöltött adatokat megjegyzi, így a szolgáltatás kiesésekor is mutat valamit.
  - **Tarkov kihívás-generátor** (net nélkül): sorsol pályát, helyszínt, fegyvert, páncélszabályt és extra szabályokat, 3 nehézségi szinten, akár 5 fős csapatra. Az egyes elemek újrasorsolhatók, és pontokat meg előzményeket is vezet.

- **🗄️ Gamer Tár** (`web/tar/`) – minden adat **kizárólag a telefonon** (IndexedDB) él. Az oldal Content-Security-Policy szabálya megtiltja, hogy bármilyen külső szerverhez forduljon.
  - **Érzékenység-átváltó:** CS2, Apex, Valorant, Overwatch 2, CoD, Destiny 2 és mások között, cm/360° és eDPI számítással, DPI-váltással és mentett beállításokkal.
  - **Játéknapló:** stopper (bezárt appnál is megy), napi, heti és havi statisztika, 7 napos grafikon, állapotok (játszom / backlog / kijátszva / félretéve), értékelés, jegyzetek és elért eredmények.
  - **Unalom:** a „Nincs kedvem semmihez” gomb ajánl valamit a megadott energiaszinthez: régen játszott vagy backlogos játékot a naplóból, rég elmentett dolgot a Tárból, vagy egy beépített ötletet. Egyre szemtelenebb kommentekkel dob újat, és számolja, hányszor vágtál bele valamibe.
  - **Tár:** linkek, képek, videók, bármilyen fájl és jegyzet, mappákkal és keresővel. Más appokból a **Megosztás** menüvel is ide küldhetők a dolgok (Web Share Target).
  - **Mentés:** biztonsági mentés JSON-fájlba és visszaállítás, tárhely-kijelzés, védett (persistent) tárhely kérése.

- **🌴 Sötét Utas** (`web/sotet/`) – Dexter-szerű kettős élet szimulátor, nyomozás nélkül, ezért más, mint A Kód. Minden nap 4 napszakból áll, és mindegyikre választasz egy akciót: munka, futás, megfigyelés, idő Lilivel, előkészítés, lecsapás, takarítás, pihenés. Négy mérőt kell egyensúlyban tartani: a Sötét Utas éhségét, a gyanút, a kapcsolatot és az energiát. Közben véletlen helyzetek jönnek két választással, minden lecsapás után pedig egy takarítós reflexjáték. A játék végtelen, napszámlálóval és top 10-es helyi ranglistával.

- **🌸 Anime Hub** (`web/anime/`) – saját anime-központ az [AniList](https://anilist.co) nyilvános API-jával. A lista, a pontozás és a jegyzetek **csak a telefonon** vannak. Az AniList felé csak keresések és azonosítók mennek, a fordítóhoz csak az anime-leírás, a képkeresőhöz csak a feltöltött kép; a CSP mást nem enged.
  - **Felfedezés:** felkapott, idei szezon, jövő szezon (sorozatok, filmek és OVA-k; premierlista dátummal és visszaszámlálással, 📌 gombbal a Tervezem listára), minden idők legjobbjai, kereső; részletes adatlap bannerrel, szereplőkkel, kapcsolódó részekkel és ajánlásokkal.
  - **📸 Melyik anime ez?** Képernyőképből vagy videórészletből megmondja az anime címét, a részt és a percet ([trace.moe](https://trace.moe), csak a feltöltött kép megy ki; 18+ találatok kiszűrve).
  - **🧭 Nézési sorrend:** a teljes franchise (évadok, filmek, OVA-k, mellékszálak) megjelenési sorrendben, „fő történet” vagy „minden” nézettel, a már látottak bejelölve.
  - **🎵 Openingek és endingek:** az [AnimeThemes](https://animethemes.moe) adatbázisából, az appban lejátszható videóval, YouTube (videó) és YouTube Music (dal) kereséssel.
  - **🇭🇺 Magyar leírás:** az adatlapon egy gomb (vagy a „mindig magyarul” kapcsoló) lefordítja a leírást. Ha a Chrome beépített, telefonon futó fordítója már elérhető, azt használja; különben a MyMemory ingyenes fordítót (csak a leírás szövege megy ki). A fordítást megjegyzi, és ha elfogy a napi keret, Google Fordító linket ad.
  - **Vissza gomb:** a telefon vissza gombja az appon belül lép vissza (fülek, adatlapok, ablakok), fent „‹ Vissza” gomb is van, a kezdőképernyőn pedig dupla nyomás kell a kilépéshez.
  - **Listám:** +1 rész egy koppintással, 5 állapot, saját 1–10-es pontszám, újranézések, jegyzet; „🔔 X új rész vár rád” és visszaszámlálás a következő részig.
  - **Műsor:** heti vetítési naptár, a listádon lévők kiemelésével.
  - **Mit nézzek?** Hangulat (8 féle) és rendelkezésre álló idő szerinti ajánló a „Tervezem” listából vagy újdonságokból, plusz egy „még egy rész” alvás-kalkulátor.
  - **MyAnimeList import:** a nyilvános MAL-lista `load.json` oldalát kimásolod és beilleszted (MAL-fiókos engedély és export nélkül), vagy beolvasod a MAL export fájlt (`.xml` / `.xml.gz`). Átjön az állapot, a haladás, a pontszám, az újranézések és a megjegyzések; az AniList felé csak a MAL-azonosítók mennek.
  - **Én:**
    - **⏱️ Idő:** az összes megnézett rész órákban (újranézésekkel együtt), hétköznapi összevetésekkel (alvás, munkanap, film, Budapest–Tokió repülés), és lebontva animénként, műfajonként, formátum, lista és stúdió szerint.
    - **🧬 DNS:** statisztika (részek, órák, műfajok, stúdiók) és anime-személyiség megosztható képként.
    - **📆 Évkönyv:** havi vagy éves összefoglaló (részek, órák, befejezések, top 3, a hónap kedvence, fő műfajok, legaktívabb nap) megosztható képként.
    - **🎯 Kihívások:** havonta 4 új kihívás pontokkal és rangokkal.
    - **⚔️ Csata:** két animéből választasz, és Elo-alapú saját kedvenc-rangsor alakul ki.
    - **⚙️ Import & mentés:** MAL import, mentés és visszaállítás.
  - **⏭️ Mit nézzek utána?** Egy anime befejezésekor felugrik a folytatás (ha van) és a hasonló ajánlások.
  - Az évkönyvhöz és a kihívásokhoz az app nézési naplót vezet (csak a telefonon), a bevezetése előtti nézések nem számítanak bele.

### Kitenni a telefonra

1. A GitHubon: **Settings → Pages → Source: GitHub Actions**.
2. Amikor a `web/` mappa változása bekerül a `main` ágba, a `.github/workflows/pages.yml` magától közzéteszi az oldalt itt:
   `https://<felhasználónév>.github.io/<repó>/` (az appok a `kaland/`, `detektiv/`, `kod/`, `tarkov/`, `gamer/`, `tar/`, `sotet/` és `anime/` alatt).
3. Nyisd meg a telefonon, majd:
   - **Android (Chrome):** ⋮ menü → *Hozzáadás a kezdőképernyőhöz* / *Alkalmazás telepítése*
   - **iPhone (Safari):** Megosztás (□↑) → *Főképernyőhöz adás*

Helyben is kipróbálhatod: `cd web && python -m http.server`, majd nyisd meg a `http://localhost:8000` címet.

## ⚙️ Telepítés

### 1. Bot létrehozása a Discordon

1. Nyisd meg a [Discord Developer Portalt](https://discord.com/developers/applications), és hozz létre egy új **Application**-t.
2. A **Bot** fülön nyomd meg a **Reset Token** gombot, és másold ki a tokent. *Senkinek ne add oda!*
3. Az **OAuth2 → URL Generator** részen pipáld be: `bot` és `applications.commands`,
   jogosultságok: **Send Messages**, **Embed Links**, **Read Message History**.
4. A generált linkkel hívd meg a botot a szerveredre.

Különleges (privileged) intentre nincs szükség.

### 2. Futtatás

Kell hozzá Python 3.10 vagy újabb.

```bash
git clone https://github.com/Taky23/Claudee.git
cd Claudee
pip install -r requirements.txt
cp .env.example .env      # Windows-on: copy .env.example .env
# írd be a tokent a .env fájlba
python bot.py
```

Tipp: ha a `.env`-ben megadod a szervered azonosítóját (`GUILD_ID`), a parancsok azonnal megjelennek.
(Azonosító másolása: Discord beállítások → Speciális → Fejlesztői mód, majd jobb klikk a szerverre → Azonosító másolása.)

A futó játékok és a kapszulák SQLite-ban (`data/bot.db`) tárolódnak, így a bot újraindítása után is megmaradnak.
A bot csak akkor tud fázist váltani és kapszulát kinyitni, ha fut – hosszú távra érdemes egy mindig bekapcsolt gépen vagy szerveren futtatni.

## 🧪 Tesztek

```bash
pip install pytest
python -m pytest
```
