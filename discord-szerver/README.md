# Discord szerver automata beállító

Ez a szkript egyszer lefuttatva felépíti a teljes Discord szervert: rangokat,
kategóriákat, csatornákat a helyes jogosultságokkal, és kiírja a szabályzatot
meg az üdvözlő üzenetet.

## Mit hoz létre?

**Rangok:** 👑 Admin · 🛡️ Moderátor · 🤖 Bot · ⭐ Tag

**Csatornák:**
- 📋 **INFORMÁCIÓ** – bejelentések, szabályzat, üdvözlés, rang-választó (mindenki olvassa, csak a stáb ír)
- 💬 **KÖZÖSSÉG** – általános, játék, képek-média, bot-parancsok
- 🔊 **HANGCSATORNÁK** – Általános, Gaming, Zene, AFK
- 🛠️ **STÁB** – mod-chat, napló (csak a Moderátor és az Admin látja)

A csatornák és rangok a `setup_szerver.py` tetején bármikor átírhatók.

## Lépésről lépésre

### 1. Készíts egy botot
1. Nyisd meg: https://discord.com/developers/applications
2. **New Application** → adj neki nevet → **Create**.
3. Bal oldalt **Bot** fül → **Reset Token** → másold ki a tokent (ezt senkinek ne add ki!).
4. Görgess le a **Privileged Gateway Intents** résznél – ehhez a szkripthez **nem** kell bekapcsolni egyiket sem.

### 2. Hívd meg a botot a szerveredre
1. Bal oldalt **OAuth2** → **URL Generator**.
2. **Scopes**-nál pipáld: `bot`.
3. **Bot Permissions**-nál pipáld: **Administrator** (így biztosan mindent létre tud hozni).
4. Másold ki a lap alján lévő linket, nyisd meg böngészőben, és válaszd ki a szervered → **Authorize**.

> A szervert előbb hozd létre a Discordban (bal oldalt a **+** gomb), ha még nincs.

### 3. Állítsd be a tokent
1. Másold a `.env.example` fájlt `.env` néven ugyanebbe a mappába.
2. Írd bele a bot tokenjét a `DISCORD_TOKEN=` után.
3. (Opcionális) Ha a bot több szerveren is van, add meg a `GUILD_ID`-t is.
   A szerverazonosítót így kapod meg: Discord → **Beállítások → Haladó →
   Fejlesztői mód** BE, majd jobb klikk a szerver nevére → **Szerverazonosító
   másolása**.

### 4. Futtasd
Telepített Python 3.9+ kell hozzá. A mappában:

```bash
pip install -r requirements.txt
python setup_szerver.py
```

Ennyi. A szkript kiírja a terminálba, mit hozott létre, és a végén:
`✅ Kész! A szerver fel van építve.`

## Jó tudni

- **Újra lefuttatható.** Amit már létrehozott (azonos néven), azt nem csinálja
  meg újra, úgyhogy nyugodtan futtathatod mégegyszer, ha módosítottál valamit a
  listában.
- **A bot rangja legyen felül.** Ha a bot nem tud rangot létrehozni, a Discord
  **Szerverbeállítások → Rangok** résznél húzd a bot rangját minél feljebb.
- **Biztonság.** A `.env` fájl (benne a token) a `.gitignore` miatt nem kerül
  fel a GitHubra. Ha mégis kiszivárgott a token, a Developer Portalon a **Reset
  Token** gombbal azonnal érvénytelenítsd.

## Testreszabás

Nyisd meg a `setup_szerver.py` fájlt. A `ROLES`, `STRUCTURE`, `RULES` és
`WELCOME_MESSAGE` részeket könnyű átírni:

- Új csatorna: vedd fel egy sorral a megfelelő kategória `channels` listájába.
- Új rang: egy sor a `ROLES` listába (`perms` lehet `admin`, `moderator`,
  `bot` vagy `member`).
- `visibility`: `all` = mindenki, `read_only` = mindenki olvassa de csak a
  stáb ír, `staff` = csak a Moderátor és az Admin látja.
