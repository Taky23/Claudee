# Vanilla DayZ szerver (Chernarus, max. 5 fő)

Két fájl, telepítő nélkül. A cél: előbb a tiszta vanilla szerver fusson, utána egyesével jönnek a modok.

1. Telepítsd a **DayZ Servert** a Steamből (Könyvtár → pipáld be a **Kellékek**/Eszközök opciót → DayZ Server → Telepítés).
2. Nyisd meg a mappáját: Steam → jobb klikk a DayZ Serveren → **Kezelés** → **Helyi fájlok tallózása**.
3. Másold be ide a `serverDZ.cfg` és az `inditas.bat` fájlt. A gyári `serverDZ.cfg`-t cseréld le.
4. Indítás: dupla kattintás az `inditas.bat`-ra. Ha a Windows tűzfal rákérdez: **Engedélyezés**.
5. Belépés: DayZ → Szerverek → Közvetlen csatlakozás → `127.0.0.1`, port `2302`, jelszó `goblin`.

Admin: játékban a chatbe `#login <passwordAdmin>` (a `serverDZ.cfg`-ben állítsd át a saját jelszavadra).
A haverokhoz a routeren az UDP 2302–2305 és 27016 portokat kell a gépedre irányítani.

**Modok később:** a mod mappáját (`@Valami`) a szerver mappájába másolod, a `keys` mappájából a `.bikey` fájlt a szerver `keys` mappájába, és az `inditas.bat` elején bővíted a sort: `set MODOK=@CF;@Valami`.
