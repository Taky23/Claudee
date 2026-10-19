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
