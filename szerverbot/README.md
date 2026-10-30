# 🤖 Szerverbot

Saját bot a baráti Tarkov / DayZ / anime szerverhez.

## Mit tud

| Parancs / funkció | Mit csinál |
|---|---|
| `/raid` | Közös játék vagy watch party szervezése: 🎯 Tarkov, 🧟 DayZ, 🌸 Anime vagy 🎲 egyéb. Pingeli a játék rangját, a többiek a **Jövök / Talán / Nem jövök** gombokkal jelentkeznek. Tarkovnál alapból 5 fő a létszámkorlát. Indulás előtt 15 perccel és induláskor pingeli a jelentkezőket. A szervező a 🗑️ gombbal lemondhatja. Időpont: `20:00`, `holnap 20:00`, `szombat 19:00`, `11.02 20:00`, `30 perc`, `most` |
| 🔊 Ideiglenes hangszobák | Aki belép az indító hangszobába (pl. `➕ Új szoba`), saját hangszobát kap (`🎮 Név szobája`), amit átnevezhet és létszámot állíthat be rá. Ha mindenki kilépett, a szoba eltűnik. |
| 💀 Kilépők | Ha valaki kilép: `💀 **Név** — Missing in Action [MIA]` a kiválasztott szobába. Ingyen, külön szobába. |
| `/rangvalaszto` | Gombos rangválasztó (🎯 Tarkov, 🧟 DayZ, 🌸 Anime, 🎲 Egyéb játékok): mindenki maga veheti fel vagy le. |
| `/szulinap beallit` · `torol` · `lista` | Mindenki megadhatja a szülinapját, és reggel 9-kor a bot felköszönti. |
| `/sorsol` | Kisorsol valakit a hangszobádból („ki megy előre?”, „ki a csali?”). |
| `/csapatok` | Véletlen csapatokra osztja a hangszobádban lévőket. |
| `/fejvagyiras` | Pénzfeldobás. |
| `/beallit` | (Admin) Melyik szoba legyen a kilépőké, a szülinapoké és az ideiglenes hangszobák indítója. |

## Beállítás

### 1. Bot létrehozása
1. [Discord Developer Portal](https://discord.com/developers/applications) → **New Application** (pl. `Szerverbot`).
2. **Bot** fül:
   - **Reset Token** → másold ki a tokent.
   - Kapcsold be a **Server Members Intent** kapcsolót (enélkül nem látja a kilépőket) → **Save Changes**.
3. Meghívás (az `APP_ID` helyére az Application ID kerül, a General Information oldalról):
   `https://discord.com/oauth2/authorize?client_id=APP_ID&permissions=8&integration_type=0&scope=bot+applications.commands`

### 2. Futtatás
Kell hozzá Python 3.10 vagy újabb.

```bash
pip install -r requirements.txt
cp .env.example .env    # írd be: SZERVERBOT_TOKEN=... és GUILD_ID=... (a szervered azonosítója)
python -m szerverbot
```

A bot csak addig működik, amíg fut, ezért egy mindig bekapcsolt gépen vagy szerveren érdemes futtatni.
Linux szerveren (pl. Oracle Cloud ingyenes gép) systemd szolgáltatásként magától újraindul:

```ini
# /etc/systemd/system/szerverbot.service
[Unit]
Description=Szerverbot
After=network-online.target

[Service]
WorkingDirectory=/home/ubuntu/Claudee
ExecStart=/usr/bin/python3 -m szerverbot
Restart=always

[Install]
WantedBy=multi-user.target
```
`sudo systemctl enable --now szerverbot`

### 3. A szerveren
1. A **bot rangját** húzd a játék-rangok fölé (Szerverbeállítások → Szerepkörök), hogy ki tudja osztani őket.
2. Hozz létre egy `➕ Új szoba` hangszobát (pl. a 🔊 HANGCSATORNÁK alá).
3. `/beallit kilepok:#🚪・kilépők szulinap:#💬・általános hangszoba:➕ Új szoba`
4. A `#🎭・rangok` szobában: `/rangvalaszto`
5. A Carl-botban kapcsold ki a búcsúüzenetet, különben dupla lesz.

Az adatok SQLite-ban vannak (`data/szerverbot.db`), így újraindítás után is megmaradnak.
