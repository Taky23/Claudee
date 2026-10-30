"""Loot Goblinok DayZ szerver – telepítő és testreszabó.

Használat (Windowson, a dayz-szerver mappában):
  python goblin.py telepit      – DayZ Server és modok letöltése (SteamCMD), küldetés (mission), serverDZ.cfg, inditas.bat
  python goblin.py frissit      – a DayZ Server és az összes mod frissítése, utána telepít
  python goblin.py testreszab   – az első indítás UTÁN: kereskedők, Black Market, AI, járműkulcsok
  python goblin.py keres GTR    – osztálynevek (classname) keresése a modokban, pl. az autókhoz

Minden beállítás a beallitasok.json fájlban van.
"""
from __future__ import annotations

import copy
import io
import json
import math
import os
import re
import secrets
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ITT = Path(__file__).resolve().parent
EXP_MISSZIOK_ZIP = "https://github.com/ExpansionModTeam/DayZ-Expansion-Missions/archive/refs/heads/master.zip"
STEAMCMD_ZIP = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
STEAM_API_RESZLETEK = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
DAYZ_APP = "221100"
DAYZ_SZERVER_APP = "223350"
VANILLA_KULDETES = "dayzOffline.chernarusplus"
GREEN_MOUNTAIN_FAJLOK = {
    "traders": "GreenMountain_Traders.map",
    "objects": "Green_Mountain_Trader.map",
}
AUTO_KERESKEDO = "GOBLIN_Autok"
BM_KERESKEDO = "GOBLIN_BlackMarket"
HIVIS_LOADOUT = "GoblinHiVisLoadout"
# Jól látható, de nem nevetséges öltözet az AI-nak (az Expansion sablonjaiban is használt osztálynevek).
HIVIS_RUHAK = {
    "Body": ["TrackSuitJacket_Red", "ParamedicJacket_Crimson"],
    "Legs": ["TrackSuitPants_Red", "ParamedicPants_Crimson"],
    "Vest": ["ReflexVest"],
    "Headgear": ["BeanieHat_Red", "RadarCap_Red"],
}
REPTER_MINTA = re.compile(r"ATC|Airfield|ControlTower|Hangar", re.I)


class Hiba(Exception):
    pass


# ---------------------------------------------------------------- általános segédek
def beallitasok() -> dict:
    try:
        with open(ITT / "beallitasok.json", encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError:
        raise Hiba(f"Nincs meg a beallitasok.json itt: {ITT}") from None
    except json.JSONDecodeError as e:
        sorok = e.doc.splitlines()
        sor = sorok[e.lineno - 1] if 0 < e.lineno <= len(sorok) else ""
        raise Hiba(
            f"Hiba a beallitasok.json {e.lineno}. sorában (valószínűleg hiányzik vagy fölösleges egy \" idézőjel vagy egy , vessző):\n"
            f"    {sor.strip()}\n"
            "Javítsd ki, vagy töltsd le újra az eredeti beallitasok.json-t."
        ) from None


def ment_beallitasok(cfg: dict) -> None:
    with open(ITT / "beallitasok.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def vektor(s) -> list[float] | None:
    """„1234.5 200 13800” vagy [x, y, z] → [x, y, z]; üres → None."""
    if not s:
        return None
    if isinstance(s, (list, tuple)):
        v = [float(x) for x in s]
    else:
        v = [float(x) for x in re.split(r"[\s,;]+", str(s).strip()) if x]
    if len(v) != 3:
        raise Hiba(f"Hibás koordináta: {s!r} (három szám kell: x y z)")
    return v


def tav2d(a, b) -> float:
    return math.hypot(a[0] - b[0], a[2] - b[2])


def olvas_json(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def ir_json(p: Path, adat) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(adat, f, indent=4, ensure_ascii=False)


def ir_szoveg(p: Path, szoveg: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(szoveg, encoding="utf-8")


def map_sor(osztaly: str, pos, ori=(0, 0, 0), extra: str | None = None) -> str:
    sor = f"{osztaly}|{pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f}|{ori[0]:.6f} {ori[1]:.6f} {ori[2]:.6f}"
    return sor + (f"|{extra}" if extra else "")


def map_poziciok(szoveg: str) -> list[list[float]]:
    out = []
    for sor in szoveg.splitlines():
        reszek = sor.split("|")
        if len(reszek) >= 2:
            try:
                out.append(vektor(reszek[1]))
            except (Hiba, ValueError):
                pass
    return out


def kozeppont(pontok):
    n = len(pontok)
    return [sum(p[i] for p in pontok) / n for i in range(3)]


# ---------------------------------------------------------------- útvonalak
def steam_konyvtarak() -> list[Path]:
    utak: list[Path] = []
    steam = None
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
                steam = Path(winreg.QueryValueEx(k, "SteamPath")[0])
        except OSError:
            pass
    for jelolt in [steam, Path("C:/Program Files (x86)/Steam"), Path("C:/Program Files/Steam")]:
        if jelolt and (jelolt / "steamapps").is_dir():
            steam = jelolt
            break
    if steam:
        utak.append(steam)
        vdf = steam / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            for m in re.finditer(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="ignore")):
                p = Path(m[1].replace("\\\\", "\\"))
                if p not in utak:
                    utak.append(p)
    return utak


def utvonalak(cfg: dict, kell_szerver: bool = True) -> tuple[Path | None, Path | None]:
    u = cfg.get("utvonalak", {})
    dayz = Path(u["dayz"]) if u.get("dayz") else None
    szerver = Path(u["dayz_szerver"]) if u.get("dayz_szerver") else None
    for lib in steam_konyvtarak():
        common = lib / "steamapps" / "common"
        if not dayz and (common / "DayZ").is_dir():
            dayz = common / "DayZ"
        if not szerver and (common / "DayZServer" / "DayZServer_x64.exe").exists():
            szerver = common / "DayZServer"
    if not szerver and (ITT / "DayZServer" / "DayZServer_x64.exe").exists():
        szerver = ITT / "DayZServer"
    if dayz and not dayz.is_dir():
        dayz = None
    if szerver and not (szerver / "DayZServer_x64.exe").exists():
        if u.get("dayz_szerver"):
            raise Hiba(f"A megadott DayZ szerver mappában nincs DayZServer_x64.exe: {szerver}")
        szerver = None
    if kell_szerver and not szerver:
        raise Hiba("Nem találom a DayZ szervert. Futtasd előbb: python goblin.py telepit")
    return dayz, szerver


def kuldetes_mappa(cfg: dict, szerver: Path) -> Path:
    return szerver / "mpmissions" / cfg["szerver"]["kuldetes"]


# ---------------------------------------------------------------- modok
def mod_keres(workshop: Path, mod: dict) -> Path | None:
    talalat = []
    for d in workshop.iterdir():
        if not d.name.startswith("@") or not d.is_dir():
            continue
        if illik(mod, d.name):
            talalat.append(d)
    if len(talalat) > 1:
        nevek = ", ".join(t.name for t in talalat)
        raise Hiba(f"A(z) {mod['nev']} modra több mappa is illik: {nevek}. Pontosítsd a mintát a beallitasok.json-ban.")
    return talalat[0] if talalat else None


def workshop_id(ertek) -> str:
    """„2291785437” vagy a Workshop-link („…?id=2291785437…”) → „2291785437”."""
    ertek = str(ertek or "").strip()
    m = re.search(r"[?&]id=(\d+)", ertek)
    if m:
        return m[1]
    return ertek if ertek.isdigit() else ""


def steamcmd_mappa() -> Path:
    return ITT / "_steamcmd"


def workshop_tartalom(wid: str) -> Path:
    return steamcmd_mappa() / "steamapps" / "workshop" / "content" / DAYZ_APP / wid


def steamcmd_exe() -> Path:
    exe = steamcmd_mappa() / ("steamcmd.exe" if sys.platform == "win32" else "steamcmd.sh")
    if not exe.exists():
        if sys.platform != "win32":
            raise Hiba("A SteamCMD letöltése csak Windowson automatikus.")
        print("  SteamCMD letöltése…")
        with urllib.request.urlopen(STEAMCMD_ZIP, timeout=120) as r:
            zipfile.ZipFile(io.BytesIO(r.read())).extractall(steamcmd_mappa())
    return exe


def steamcmd_futtat(args: list[str]) -> None:
    """A SteamCMD a konzolban kérdezi a jelszót és a Steam Guard kódot, ezért a kimenetét nem nyeljük el."""
    subprocess.run([str(steamcmd_exe()), *args, "+quit"], check=False)


def workshop_cimek(azonositok: list[str]) -> dict[str, str]:
    """Workshop azonosító → a mod címe (a Steam nyilvános API-ja alapján). Hiba esetén üres."""
    if not azonositok:
        return {}
    adat = {"itemcount": len(azonositok), **{f"publishedfileids[{i}]": a for i, a in enumerate(azonositok)}}
    try:
        with urllib.request.urlopen(STEAM_API_RESZLETEK, data=urllib.parse.urlencode(adat).encode(), timeout=20) as r:
            valasz = json.load(r)
    except (OSError, ValueError):
        return {}
    out = {}
    for d in valasz.get("response", {}).get("publishedfiledetails", []):
        if str(d.get("consumer_app_id")) == DAYZ_APP and d.get("title"):
            out[str(d["publishedfileid"])] = d["title"]
    return out


def mod_nev_metabol(mappa: Path) -> str:
    meta = mappa / "meta.cpp"
    if meta.exists():
        m = re.search(r'name\s*=\s*"([^"]*)"', meta.read_text(encoding="utf-8", errors="ignore"))
        if m:
            return m[1]
    return ""


def illik(mod: dict, nev: str) -> bool:
    n = norm(nev)
    if (n == mod["minta"]) if mod.get("pontos") else (mod["minta"] in n):
        return True
    return any(norm(m) in n for m in mod.get("mas_nevek", []))


def modok_letoltese(cfg: dict, szerver: Path | None, mindet: bool) -> Path:
    """A hiányzó (vagy frissítésnél az összes) modot és a DayZ Servert letölti SteamCMD-vel."""
    kellenek = []
    for mod in cfg["modok"]:
        wid = workshop_id(mod.get("workshop"))
        if wid and (mindet or not workshop_tartalom(wid).is_dir()):
            kellenek.append((mod, wid))
    kell_szerver = szerver is None or mindet
    if not kellenek and not kell_szerver:
        return szerver

    cimek = workshop_cimek([w for _, w in kellenek])
    for mod, wid in kellenek:
        cim = cimek.get(wid)
        if cim is None and cimek:
            raise Hiba(f"A(z) {mod['nev']} Workshop azonosítója ({wid}) nem egy DayZ mod. Ellenőrizd a linket a beallitasok.json-ban.")
        if cim and not illik(mod, cim):
            raise Hiba(f"A(z) {mod['nev']} helyére megadott Workshop link egy másik modra mutat: „{cim}”. Ellenőrizd a beallitasok.json-ban.")

    felh = cfg.get("steam_felhasznalo", "").strip()
    if not felh:
        felh = input("\nSteam felhasználónév (a DayZ-t birtokló fiók; a jelszót a SteamCMD kérdezi): ").strip()
        if not felh:
            raise Hiba("Steam felhasználónév nélkül nem tudok letölteni.")
        cfg["steam_felhasznalo"] = felh
        ment_beallitasok(cfg)
    args = []
    cel_szerver = szerver or ITT / "DayZServer"
    if kell_szerver:
        args += ["+force_install_dir", str(cel_szerver)]
    args += ["+login", felh]
    if kell_szerver:
        args += ["+app_update", DAYZ_SZERVER_APP, "validate"]
    for _, wid in kellenek:
        args += ["+workshop_download_item", DAYZ_APP, wid, "validate"]
    print(f"\nLetöltés SteamCMD-vel: {'DayZ Server + ' if kell_szerver else ''}{len(kellenek)} mod. "
          "Ha kéri, írd be a Steam jelszavad és a Steam Guard kódot (a jelszó gépelés közben nem látszik).")
    steamcmd_futtat(args)
    if kell_szerver and not (cel_szerver / "DayZServer_x64.exe").exists():
        raise Hiba("A DayZ Server letöltése nem sikerült (rossz jelszó vagy Steam Guard kód?). Futtasd újra.")
    rossz = [m["nev"] for m, w in kellenek if not workshop_tartalom(w).is_dir()]
    if rossz:
        raise Hiba("Nem sikerült letölteni: " + ", ".join(rossz) + ". Futtasd újra; nagy modnál a SteamCMD néha többször is nekifut.")
    return cel_szerver


def modok_masolasa(cfg: dict, dayz: Path | None, szerver: Path) -> list[dict]:
    workshop = dayz / "!Workshop" if dayz else None
    (szerver / "keys").mkdir(exist_ok=True)
    meglevo = []
    hianyzo = []
    for mod in cfg["modok"]:
        wid = workshop_id(mod.get("workshop"))
        forras = workshop_tartalom(wid) if wid and workshop_tartalom(wid).is_dir() else None
        if forras:
            meta_nev = mod_nev_metabol(forras)
            if meta_nev and not illik(mod, meta_nev):
                # A Workshop-címet letöltés előtt már ellenőriztük; a mod belső neve ettől eltérhet.
                print(f"  ⚠️ {mod['nev']}: a letöltött mod belső neve „{meta_nev}”. Ha ez nem a várt mod, ellenőrizd a Workshop linkjét.")
        elif mod.get("helyi_mappa"):
            helyi = ITT / mod["helyi_mappa"]
            forras = mod_keres(helyi, mod) if helyi.is_dir() else None
        elif workshop and workshop.is_dir():
            forras = mod_keres(workshop, mod)
        if not forras:
            if not mod.get("opcionalis"):
                hianyzo.append(mod["nev"])
            print(f"  – {mod['nev']}: nincs meg" + (" (nem kötelező)" if mod.get("opcionalis") else " ⚠️"))
            continue
        cel = szerver / f"@{mod['nev']}"
        if cel.exists():
            shutil.rmtree(cel)
        shutil.copytree(forras, cel)
        kulcsok = 0
        for kulcs in cel.rglob("*.bikey"):
            shutil.copy2(kulcs, szerver / "keys" / kulcs.name)
            kulcsok += 1
        print(f"  ✓ {mod['nev']}  ← {mod_nev_metabol(cel) or forras.name}  ({kulcsok} kulcs)")
        meglevo.append({**mod, "mappa": cel})
    if hianyzo:
        raise Hiba("Hiányzó kötelező modok: " + ", ".join(hianyzo) + ". Add meg a Workshop linkjüket a beallitasok.json-ban "
                   "(modok → workshop), vagy iratkozz fel rájuk, és indítsd el egyszer a DayZ launchert.")
    return meglevo


# ---------------------------------------------------------------- küldetés (mission)
def expansion_sablon() -> Path:
    cel = ITT / "_letoltes" / "expansion-sablon"
    if (cel / "cfgeconomycore.xml").exists():
        return cel
    print("  Expansion küldetés-sablon letöltése…")
    with urllib.request.urlopen(EXP_MISSZIOK_ZIP, timeout=120) as r:
        adat = r.read()
    with zipfile.ZipFile(io.BytesIO(adat)) as z:
        elotag = None
        for nev in z.namelist():
            m = re.match(r"([^/]+/Template/Chernarus/)", nev)
            if m:
                elotag = m[1]
                break
        if not elotag:
            raise Hiba("A letöltött Expansion sablonban nincs Chernarus mappa.")
        for nev in z.namelist():
            if nev.startswith(elotag) and not nev.endswith("/"):
                p = cel / nev[len(elotag):]
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(z.read(nev))
    return cel


def ce_blokk(mappa: str, fajlok: list[tuple[str, str]]) -> str:
    sorok = [f'\t<ce folder="{mappa}">'] + [f'\t\t<file name="{n}" type="{t}" />' for n, t in fajlok] + ["\t</ce>"]
    return "\n".join(sorok)


def economycore_beir(szoveg: str, mappa: str, blokk: str | None) -> str:
    """A <ce folder="mappa"> blokkot lecseréli (vagy törli, ha blokk None), különben beszúrja."""
    szoveg = re.sub(rf'\s*<ce folder="{re.escape(mappa)}">.*?</ce>', "", szoveg, flags=re.S)
    if blokk:
        szoveg = szoveg.replace("</economycore>", blokk + "\n</economycore>")
    return szoveg


def eventspawns_osszefuz(cel: str, forras: str) -> tuple[str, int]:
    meglevo = set(re.findall(r'<event name="([^"]+)"', cel))
    uj = [m[0] for m in re.finditer(r'[ \t]*<event name="([^"]+)">.*?</event>', forras, flags=re.S) if m[1] not in meglevo]
    if uj:
        cel = cel.replace("</eventposdef>", "\n".join(uj) + "\n</eventposdef>")
    return cel, len(uj)


def mod_types_fajlok(mod_mappa: Path) -> list[Path]:
    out = []
    for p in mod_mappa.rglob("*.xml"):
        try:
            eleje = p.read_text(encoding="utf-8", errors="ignore")[:2000]
        except OSError:
            continue
        if re.search(r"<types>", eleje) and "<type " in p.read_text(encoding="utf-8", errors="ignore"):
            out.append(p)
    return out


def fenyek_map(gm_poziciok: list[list[float]], sugar: float) -> str:
    """Kivilágítás a Green Mountain kereskedőhely köré (fénykör + piros jelzőfények)."""
    k = kozeppont(gm_poziciok)
    talaj = min(p[1] for p in gm_poziciok)
    sorok = []
    for i in range(10):
        szog = 2 * math.pi * i / 10
        sorok.append(map_sor("ExpansionPointLight", [k[0] + sugar * math.cos(szog), talaj + 3.0, k[2] + sugar * math.sin(szog)], extra="true"))
    for i in range(4):
        szog = 2 * math.pi * i / 4 + math.pi / 4
        sorok.append(map_sor("StaticObj_Airfield_Light_Navig", [k[0] + (sugar + 6) * math.cos(szog), talaj, k[2] + (sugar + 6) * math.sin(szog)]))
    return "\n".join(sorok) + "\n"


def kuldetes_osszerakasa(cfg: dict, szerver: Path, modok: list[dict], ujra: bool) -> Path:
    cel = kuldetes_mappa(cfg, szerver)
    vanilla = szerver / "mpmissions" / VANILLA_KULDETES
    if ujra and cel.exists():
        shutil.rmtree(cel)
    if not cel.exists():
        if not vanilla.is_dir():
            raise Hiba(f"Nincs meg az alap küldetés: {vanilla}")
        shutil.copytree(vanilla, cel)
        print(f"  ✓ Küldetés: {cel.name} (az alap Chernarusból)")

    sablon = expansion_sablon()
    # Expansion tárgyak és járművek a loot-rendszerbe
    shutil.copytree(sablon / "expansion_ce", cel / "expansion_ce", dirs_exist_ok=True)
    ec = (cel / "cfgeconomycore.xml").read_text(encoding="utf-8")
    ec = economycore_beir(ec, "expansion_ce", ce_blokk("expansion_ce", [
        ("expansion_types.xml", "types"), ("expansion_spawnabletypes.xml", "spawnabletypes"), ("expansion_events.xml", "events"),
    ]))
    # A modok saját types.xml-jei (pl. Tarkovos tárgyak, .50-es puskák), hogy lootként is előkerüljenek
    goblin_ce = cel / "goblin_ce"
    if goblin_ce.exists():
        shutil.rmtree(goblin_ce)
    fajlok = []
    for mod in modok:
        talalt = mod_types_fajlok(mod["mappa"])
        if mod.get("loot") and not talalt:
            print(f"  ⚠️ {mod['nev']}: nincs a modban types.xml, ezért a tárgyai lootként nem kerülnek elő "
                  "(a mod leírásában szokott lenni letölthető types.xml – azt tedd a mod mappájába, és futtasd újra).")
        for i, p in enumerate(talalt):
            nev = f"{norm(mod['nev'])}_{i}_types.xml"
            goblin_ce.mkdir(exist_ok=True)
            shutil.copy2(p, goblin_ce / nev)
            fajlok.append((nev, "types"))
            print(f"  ✓ Loot: {mod['nev']} → {p.name}")
    ec = economycore_beir(ec, "goblin_ce", ce_blokk("goblin_ce", fajlok) if fajlok else None)
    (cel / "cfgeconomycore.xml").write_text(ec, encoding="utf-8")

    es = (cel / "cfgeventspawns.xml").read_text(encoding="utf-8")
    es, n = eventspawns_osszefuz(es, (sablon / "cfgeventspawns.xml").read_text(encoding="utf-8"))
    (cel / "cfgeventspawns.xml").write_text(es, encoding="utf-8")
    if n:
        print(f"  ✓ {n} Expansion jármű-spawnpont hozzáadva")

    # Csak a Green Mountain kereskedőhely kell, a többi gyári kereskedő nem.
    exp = cel / "expansion"
    for mappa in ("traders", "objects"):
        (exp / mappa).mkdir(parents=True, exist_ok=True)
        for regi in (exp / mappa).glob("*.map"):
            if not regi.name.startswith("Goblin_"):
                regi.unlink()
        shutil.copy2(sablon / "expansion" / mappa / GREEN_MOUNTAIN_FAJLOK[mappa], exp / mappa / GREEN_MOUNTAIN_FAJLOK[mappa])
    tr = exp / "traders" / GREEN_MOUNTAIN_FAJLOK["traders"]
    szoveg = tr.read_text(encoding="utf-8")
    szoveg = re.sub(r"^(\w+)\.Vehicles\|", rf"\1.{AUTO_KERESKEDO}|", szoveg, flags=re.M)
    tr.write_text(szoveg, encoding="utf-8")
    gm = map_poziciok(szoveg)
    ir_szoveg(exp / "objects" / "Goblin_GreenMountain_Fenyek.map", fenyek_map(gm, cfg["green_mountain"].get("fenyek_sugara", 14)))
    print("  ✓ Green Mountain kereskedőhely + kivilágítás (a többi gyári kereskedő kikapcsolva)")
    return cel


def szerver_cfg(cfg: dict) -> str:
    s = cfg["szerver"]
    return f"""hostname = "{s['nev']}";
password = "{s.get('jelszo', '')}";
passwordAdmin = "{s['admin_jelszo']}";
maxPlayers = {s.get('max_jatekos', 5)};
verifySignatures = 2;
forceSameBuild = 1;
disableVoN = 0;
vonCodecQuality = 20;
disable3rdPerson = 0;
disableCrosshair = 0;
disablePersonalLight = 1;
lightingConfig = 0;
serverTime = "SystemTime";
serverTimeAcceleration = 6;
serverNightTimeAcceleration = 4;
serverTimePersistent = 0;
guaranteedUpdates = 1;
loginQueueConcurrentPlayers = 5;
loginQueueMaxPlayers = 50;
instanceId = 1;
storageAutoFix = 1;

class Missions
{{
    class DayZ
    {{
        template = "{s['kuldetes']}";
    }};
}};
"""


def inditas_bat(cfg: dict, modok: list[dict]) -> str:
    modlista = ";".join(f"@{m['nev']}" for m in modok if not m.get("csak_szerver"))
    szerver_modok = ";".join(f"@{m['nev']}" for m in modok if m.get("csak_szerver"))
    szerver_param = f' "-serverMod={szerver_modok}"' if szerver_modok else ""
    return f"""@echo off
chcp 65001 >nul
title Loot Goblinok DayZ szerver
cd /d "%~dp0"
:start
echo [%date% %time%] Szerver indul...
DayZServer_x64.exe -config=serverDZ.cfg -port={cfg['szerver'].get('port', 2302)} -profiles=profiles -dologs -adminlog -netlog -freezecheck "-mod={modlista}"{szerver_param}
echo [%date% %time%] A szerver leallt. Ujrainditas 10 masodperc mulva (bezarashoz: Ctrl+C, majd I).
timeout /t 10
goto start
"""


def telepit(ujra: bool = False, frissit: bool = False) -> None:
    cfg = beallitasok()
    dayz, szerver = utvonalak(cfg, kell_szerver=False)
    szerver = modok_letoltese(cfg, szerver, mindet=frissit)
    print(f"\nDayZ szerver: {szerver}\n\nModok:")
    modok = modok_masolasa(cfg, dayz, szerver)
    print("\nKüldetés:")
    kuldetes_osszerakasa(cfg, szerver, modok, ujra)

    if not cfg["szerver"].get("admin_jelszo"):
        cfg["szerver"]["admin_jelszo"] = secrets.token_urlsafe(9)
        ment_beallitasok(cfg)
        print(f"\n🔑 Admin jelszó (elmentve a beallitasok.json-ba): {cfg['szerver']['admin_jelszo']}")
    (szerver / "serverDZ.cfg").write_text(szerver_cfg(cfg), encoding="utf-8")
    (szerver / "inditas.bat").write_text(inditas_bat(cfg, modok), encoding="utf-8")

    admins = [a for a in cfg.get("superadminok_steam64", []) if a.isdigit()]
    if admins:
        ir_szoveg(szerver / "profiles" / "VPPAdminTools" / "Permissions" / "SuperAdmins" / "SuperAdmins.txt", "\n".join(admins) + "\n")
        print(f"✓ Admin (VPP): {', '.join(admins)}")
    else:
        print("⚠️ Nincs megadva Steam64 azonosító a superadminok_steam64 mezőben, így admin eszköz nem lesz.")
    print(f"\n✅ Kész. Indítás: {szerver / 'inditas.bat'}\n"
          "A haveroknak nem kell előre feliratkozniuk: a DayZ launcher csatlakozáskor felajánlja a hiányzó modok letöltését.\n"
          "Az első indítás után állítsd le a szervert, és futtasd: python goblin.py testreszab")


# ---------------------------------------------------------------- testreszabás (az első indítás után)
def piac_index(market: Path) -> tuple[dict, dict | None, dict | None]:
    """ClassName (kisbetű) → tárgy, plusz egy minta kategória és minta tárgy a formátumhoz."""
    index: dict[str, dict] = {}
    minta_kat = minta_targy = None
    for p in sorted(market.glob("*.json")):
        if p.name.startswith("GOBLIN_"):
            continue
        try:
            kat = olvas_json(p)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(kat, dict) or "Items" not in kat:
            continue
        minta_kat = minta_kat or kat
        for t in kat["Items"]:
            minta_targy = minta_targy or t
            index.setdefault(t.get("ClassName", "").lower(), t)
    return index, minta_kat, minta_targy


def piaci_targy(index: dict, minta: dict | None, osztaly: str, ar) -> dict:
    t = copy.deepcopy(index.get(osztaly.lower()))
    if t is None:
        t = {k: copy.deepcopy(v) for k, v in (minta or {}).items()}
        t.update({"ClassName": osztaly.lower(), "SellPricePercent": -1, "MaxStockThreshold": 10, "MinStockThreshold": 1,
                  "QuantityPercent": -1, "SpawnAttachments": [], "Variants": []})
    if ar:
        t["MinPriceThreshold"], t["MaxPriceThreshold"] = int(ar[0]), int(ar[1])
    return t


def kategoria(minta: dict, nev: str, targyak: list[dict], szin: str = "FBFCFEFF") -> dict:
    k = {key: copy.deepcopy(v) for key, v in minta.items() if key != "Items"}
    k.update({"DisplayName": nev, "Color": szin, "IsExchange": 0, "InitStockPercent": 75.0, "Items": targyak})
    return k


def kereskedo(minta: dict, nev: str, kategoriak: list[str]) -> dict:
    k = copy.deepcopy(minta)
    k["DisplayName"] = nev
    k["Categories"] = [f"{c}:0" for c in kategoriak]  # 0 = csak vásárlás
    k["Items"] = {}
    for kulcs in ("MinRequiredReputation", "MaxRequiredReputation", "RequiredCompletedQuestID", "MinRequiredHumanity"):
        if kulcs in k:
            k[kulcs] = 0
    if "RequiredFaction" in k:
        k["RequiredFaction"] = ""
    return k


def hivis_loadout(alap: dict) -> dict:
    lo = copy.deepcopy(alap)
    slotok = {s.get("SlotName"): s for s in lo.get("InventoryAttachments", [])}
    for slot, ruhak in HIVIS_RUHAK.items():
        targyak = [{"ClassName": r, "Include": "", "Chance": 1.0, "Quantity": {"Min": 0.0, "Max": 0.0}, "Health": [],
                    "InventoryAttachments": [], "InventoryCargo": [], "ConstructionPartsBuilt": [], "Sets": []} for r in ruhak]
        if slot in slotok:
            # A régi ruhadarab rakományát (pl. tárak) átvisszük az újakba, hogy legyen mivel tölteni.
            regi_cargo = [c for t in slotok[slot].get("Items", []) for c in t.get("InventoryCargo", [])]
            for t in targyak:
                t["InventoryCargo"] = copy.deepcopy(regi_cargo)
            slotok[slot]["Items"] = targyak
        else:
            lo.setdefault("InventoryAttachments", []).append({"SlotName": slot, "Items": targyak})
    return lo


def katonai_csoportok(mapgrouppos: str, tavolsag: float, min_epulet: int) -> list[dict]:
    pontok = []
    for m in re.finditer(r'<group\s+name="(Land_Mil_[^"]+)"\s+pos="([^"]+)"', mapgrouppos):
        pontok.append((m[1], vektor(m[2])))
    csoportok: list[dict] = []
    for nev, p in pontok:
        cel = None
        for cs in csoportok:
            if any(tav2d(p, q) <= tavolsag for q in cs["pontok"]):
                cel = cs
                break
        if cel is None:
            cel = {"pontok": [], "nevek": []}
            csoportok.append(cel)
        cel["pontok"].append(p)
        cel["nevek"].append(nev)
    # Az egymásba érő csoportokat összevonjuk.
    valtozott = True
    while valtozott:
        valtozott = False
        for i in range(len(csoportok)):
            for j in range(i + 1, len(csoportok)):
                a, b = csoportok[i], csoportok[j]
                if any(tav2d(p, q) <= tavolsag for p in a["pontok"] for q in b["pontok"]):
                    a["pontok"] += b["pontok"]
                    a["nevek"] += b["nevek"]
                    del csoportok[j]
                    valtozott = True
                    break
            if valtozott:
                break
    out = []
    for cs in csoportok:
        if len(cs["pontok"]) < min_epulet:
            continue
        cs["kozep"] = kozeppont(cs["pontok"])
        cs["repter"] = any(REPTER_MINTA.search(n) for n in cs["nevek"])
        out.append(cs)
    return out


def utvonal(pontok: list[list[float]], max_pont: int = 8) -> list[list[float]]:
    k = kozeppont(pontok)
    rendezett = sorted(pontok, key=lambda p: math.atan2(p[2] - k[2], p[0] - k[0]))
    lepes = max(1, len(rendezett) // max_pont)
    return [[round(c, 3) for c in p] for p in rendezett[::lepes][:max_pont]]


ALAP_JARULOR = {
    "Name": "", "Persist": False, "Faction": "West", "Formation": "RANDOM", "FormationScale": 1.5, "FormationLooseness": 0.1,
    "Loadout": HIVIS_LOADOUT, "Units": [], "NumberOfAI": 1, "NumberOfAIMax": 2, "Behaviour": "LOOP_OR_ALTERNATE",
    "LootingBehaviour": "DEFAULT", "Speed": "WALK", "UnderThreatSpeed": "SPRINT", "DefaultStance": "STANDING",
    "DefaultLookAngle": 0.0, "CanBeLooted": True, "LootDropOnDeath": "", "UnlimitedReload": 0,
    "SniperProneDistanceThreshold": 0.0, "AccuracyMin": 0.25, "AccuracyMax": 0.5, "ThreatDistanceLimit": -1.0,
    "NoiseInvestigationDistanceLimit": -1.0, "MaxFlankingDistance": -1.0, "EnableFlankingOutsideCombat": -1,
    "DamageMultiplier": 0.8, "DamageReceivedMultiplier": 1.0, "HeadshotResistance": 0.0, "ShoryukenChance": 0.0,
    "ShoryukenDamageMultiplier": 0.0, "CanSpawnInContaminatedArea": False, "CanBeTriggeredByAI": False,
    "MinDistRadius": -2.0, "MaxDistRadius": -2.0, "DespawnRadius": -2.0, "MinSpreadRadius": 1.0, "MaxSpreadRadius": 30.0,
    "Chance": 1.0, "DespawnTime": -1.0, "RespawnTime": 1800.0, "LoadBalancingCategory": "", "ObjectClassName": "",
    "WaypointInterpolation": "", "UseRandomWaypointAsStartPoint": True, "Waypoints": [],
}


def jarorok(csoportok: list[dict], ai: dict, minta: dict | None, kizart: list[list[float]]) -> list[dict]:
    alap = {**ALAP_JARULOR, **({k: v for k, v in minta.items() if k in ALAP_JARULOR} if minta else {})}
    alap.update({"Loadout": HIVIS_LOADOUT, "Faction": "West", "Chance": 1.0, "ObjectClassName": "", "LoadBalancingCategory": "",
                 "AccuracyMin": ai["pontossag"][0], "AccuracyMax": ai["pontossag"][1],
                 "DamageMultiplier": ai["sebzes_szorzo"], "DamageReceivedMultiplier": ai["kapott_sebzes_szorzo"],
                 "RespawnTime": float(ai["ujraeledes_perc"] * 60), "CanBeLooted": True, "Persist": False})
    out = []
    for i, cs in enumerate(sorted(csoportok, key=lambda c: (-c["kozep"][2], c["kozep"][0])), 1):
        if any(tav2d(cs["kozep"], k) < 400 for k in kizart):
            continue
        eszak = cs["kozep"][2] >= ai["eszak_hatar"]
        lo, hi = ai["eszak"] if eszak else ai["del"]
        if cs["repter"]:
            lo, hi = lo + ai["repter_plusz"], hi + ai["repter_plusz"]
        j = copy.deepcopy(alap)
        tipus = "Reptér" if cs["repter"] else ("Észak" if eszak else "Dél")
        j.update({"Name": f"Goblin {tipus} #{i} ({cs['kozep'][0]:.0f} / {cs['kozep'][2]:.0f})",
                  "NumberOfAI": lo, "NumberOfAIMax": hi, "Waypoints": utvonal(cs["pontok"])})
        out.append(j)
    return out


def jelolo_es_safezone_szures(lista: list, kulcs_jeloltek: tuple[str, ...], megtart: list[list[float]], sugar: float) -> list:
    """Csak azokat tartja meg, amik a megtartandó helyek közelében vannak."""
    out = []
    for elem in lista:
        pos = next((elem[k] for k in kulcs_jeloltek if k in elem), None)
        try:
            p = vektor(pos)
        except (Hiba, ValueError, TypeError):
            p = None
        if p and any(tav2d(p, m) <= sugar for m in megtart):
            out.append(elem)
    return out


def bm_map(bm: dict) -> tuple[str, str]:
    pos = vektor(bm["helyzet"])
    irany = float(bm.get("irany", 0))
    rad = math.radians(irany)
    elol = [pos[0] + 2.5 * math.sin(rad), pos[1], pos[2] + 2.5 * math.cos(rad)]
    trader = map_sor(f"ExpansionTraderLinda.{BM_KERESKEDO}", pos, (irany, 0, 0),
                     "Balaclava3Holes_Black,M65Jacket_Black,CargoPants_Black,MilitaryBoots_Black,TacticalGloves_Black,PlateCarrierVest_Black")
    objektumok = "\n".join([
        map_sor("StaticObj_Misc_Table_Market", elol, (irany, 0, 0)),
        map_sor("bldr_fire_barrel", [pos[0] + 3.5, pos[1], pos[2] + 1.5]),
        map_sor("StaticObj_Misc_WoodenCrate_3x", [pos[0] - 3, pos[1], pos[2] - 1], (irany + 15, 0, 0)),
        map_sor("ExpansionPointLight", [pos[0], pos[1] + 2.5, pos[2]], extra="true"),
    ]) + "\n"
    return trader + "\n", objektumok


def lerako(lista: list, pos, minta: list) -> list:
    """Jármű-lerakóhely hozzáadása (ha még nincs ott)."""
    if any(tav2d(vektor(e["Position"]), pos) < 5 for e in lista if isinstance(e, dict) and "Position" in e):
        return lista
    uj = copy.deepcopy(minta[0]) if minta and isinstance(minta[0], dict) else {}
    uj["Position"] = pos
    uj["Orientation"] = [0.0, 0.0, 0.0]
    return lista + [uj]


def testreszab() -> None:
    cfg = beallitasok()
    _, szerver = utvonalak(cfg)
    kuldetes = kuldetes_mappa(cfg, szerver)
    profil = szerver / "profiles" / "ExpansionMod"
    settings = kuldetes / "expansion" / "settings"
    if not (profil / "Market").is_dir() or not settings.is_dir():
        raise Hiba("Még nem futott a szerver. Indítsd el egyszer (inditas.bat), várd meg, amíg betölt, állítsd le, és futtasd újra.")

    gm_map = (kuldetes / "expansion" / "traders" / GREEN_MOUNTAIN_FAJLOK["traders"]).read_text(encoding="utf-8")
    gm = kozeppont(map_poziciok(gm_map))
    bm = cfg["black_market"]
    bm_pos = vektor(bm.get("helyzet"))

    # --- piac: kategóriák
    market = profil / "Market"
    index, minta_kat, minta_targy = piac_index(market)
    if not minta_kat:
        raise Hiba(f"Nincs alap piaci kategória itt: {market}")
    autok = [piaci_targy(index, minta_targy, a["osztaly"], a.get("ar")) for a in cfg["green_mountain"]["autok"]]
    ir_json(market / "GOBLIN_Autok.json", kategoria(minta_kat, "Goblin autók", autok))
    kategoriak_bm = []
    for h in bm["helik"]:
        if not h.get("osztaly"):
            print(f"  ⚠️ BM heli kihagyva, nincs megadva az osztályneve: {h['nev']} (python goblin.py keres …)")
    helik = [piaci_targy(index, minta_targy, h["osztaly"], h.get("ar")) for h in bm["helik"] if h.get("osztaly")]
    ir_json(market / "GOBLIN_BM_Legi.json", kategoria(minta_kat, "Helikopterek", helik, "1A1A1AFF"))
    kategoriak_bm.append("GOBLIN_BM_Legi")
    bm_autok = [a for a in bm["autok"] if a.get("osztaly")]
    for a in bm["autok"]:
        if not a.get("osztaly"):
            print(f"  ⚠️ BM autó kihagyva, nincs megadva az osztályneve: {a['nev']} (python goblin.py keres …)")
    if bm_autok:
        ir_json(market / "GOBLIN_BM_Autok.json", kategoria(minta_kat, "Különleges autók",
                [piaci_targy(index, minta_targy, a["osztaly"], a.get("ar")) for a in bm_autok], "1A1A1AFF"))
        kategoriak_bm.append("GOBLIN_BM_Autok")
    elif (market / "GOBLIN_BM_Autok.json").exists():
        (market / "GOBLIN_BM_Autok.json").unlink()
    if bm.get("egyeb"):
        ir_json(market / "GOBLIN_BM_Egyeb.json", kategoria(minta_kat, "Feketepiac", [
            piaci_targy(index, minta_targy, t["osztaly"], t.get("ar")) for t in bm["egyeb"] if t.get("osztaly")], "1A1A1AFF"))
        kategoriak_bm.append("GOBLIN_BM_Egyeb")
    print(f"  ✓ Piac: {len(autok)} autó a Green Mountainen, {len(helik)} heli + {len(bm_autok)} különleges autó a BM-ben")

    # --- kereskedők
    traders = profil / "Traders"
    minta_tr = None
    for nev in ("Vehicles.json", "Aircraft.json"):
        if (traders / nev).exists():
            minta_tr = olvas_json(traders / nev)
            break
    if minta_tr is None:
        jeloltek = [p for p in traders.glob("*.json") if not p.name.startswith("GOBLIN_")]
        if not jeloltek:
            raise Hiba(f"Nincs alap kereskedő itt: {traders}")
        minta_tr = olvas_json(jeloltek[0])
    ir_json(traders / f"{AUTO_KERESKEDO}.json", kereskedo(minta_tr, "Autókereskedő", ["GOBLIN_Autok"]))
    ir_json(traders / f"{BM_KERESKEDO}.json", kereskedo(minta_tr, "Feketepiac", kategoriak_bm))
    print("  ✓ Kereskedők: Autókereskedő (Green Mountain), Feketepiac (csak készpénz)")

    # --- Black Market a térképen (jelölő nélkül)
    exp = kuldetes / "expansion"
    if bm_pos:
        trader_sor, objektumok = bm_map(bm)
        ir_szoveg(exp / "traders" / "Goblin_BlackMarket.map", trader_sor)
        ir_szoveg(exp / "objects" / "Goblin_BlackMarket.map", objektumok)
        print(f"  ✓ Black Market: {bm_pos[0]:.0f} / {bm_pos[2]:.0f}")
    else:
        for p in (exp / "traders" / "Goblin_BlackMarket.map", exp / "objects" / "Goblin_BlackMarket.map"):
            if p.exists():
                p.unlink()
        print("  ⚠️ A Black Market helye még nincs megadva (black_market → helyzet), ezért most kimarad.")

    # --- piaci beállítások: kulcs a járműhöz, lerakóhelyek
    ms_p = settings / "MarketSettings.json"
    if ms_p.exists():
        ms = olvas_json(ms_p)
        ms["VehicleKeys"] = ["ExpansionCarKey"]
        if bm_pos:
            for kulcs, mezo in (("LandSpawnPositions", "jarmu_lerako"), ("AirSpawnPositions", "heli_lerako")):
                pos = vektor(bm.get(mezo))
                if pos:
                    ms[kulcs] = lerako(ms.get(kulcs, []), pos, ms.get(kulcs, []))
                else:
                    print(f"  ⚠️ black_market → {mezo} nincs megadva, ott még nem tud lerakódni a megvett jármű.")
        ir_json(ms_p, ms)
        print("  ✓ Vásárláskor a jármű zárva, a vevő kulcsot kap hozzá")

    # --- járművek: csak kulccsal indul, nem lehet feltörni
    vs_p = settings / "VehicleSettings.json"
    if vs_p.exists():
        vs = olvas_json(vs_p)
        vs["VehicleRequireKeyToStart"] = 1
        vs["CanPickLock"] = False
        vs["CanChangeLock"] = False
        ir_json(vs_p, vs)
        print("  ✓ Járművek: csak a saját kulccsal nyithatók és indíthatók; üres kulcs párosítható gazdátlan járműhöz")

    # --- térképjelölők és biztonsági zónák: csak a Green Mountain (a BM titkos)
    mp_p = settings / "MapSettings.json"
    if mp_p.exists():
        mp = olvas_json(mp_p)
        if isinstance(mp.get("ServerMarkers"), list):
            elotte = len(mp["ServerMarkers"])
            mp["ServerMarkers"] = jelolo_es_safezone_szures(mp["ServerMarkers"], ("m_Position", "Position"), [gm], 300)
            print(f"  ✓ Térképjelölők: {len(mp['ServerMarkers'])} marad (Green Mountain), {elotte - len(mp['ServerMarkers'])} törölve; a BM nem látszik")
        ir_json(mp_p, mp)
    sz_p = settings / "SafeZoneSettings.json"
    if sz_p.exists():
        sz = olvas_json(sz_p)
        megtart = [gm]
        kor = jelolo_es_safezone_szures(sz.get("CircleZones", []), ("Center",), megtart, 300)
        if bm_pos and bm.get("safezone"):
            kor.append({"Center": bm_pos, "Radius": float(bm.get("safezone_sugar", 60))})
        sz["CircleZones"] = kor
        sz["PolygonZones"] = jelolo_es_safezone_szures(
            [{"_p": z, "Center": kozeppont([vektor(x) for x in z.get("Positions", [])])} for z in sz.get("PolygonZones", []) if z.get("Positions")],
            ("Center",), megtart, 300)
        sz["PolygonZones"] = [z["_p"] for z in sz["PolygonZones"]]
        if "CylinderZones" in sz:
            sz["CylinderZones"] = jelolo_es_safezone_szures(sz["CylinderZones"], ("Center",), megtart, 300)
        ir_json(sz_p, sz)
        print("  ✓ Biztonsági zóna: Green Mountain" + (" + Black Market" if bm_pos and bm.get("safezone") else ""))

    # --- AI: jól látható ruha, csak katonai helyeken, északon több
    loadouts = profil / "Loadouts"
    alap_lo = next((loadouts / n for n in ("WestLoadout.json", "HumanLoadout.json") if (loadouts / n).exists()), None)
    if alap_lo:
        ir_json(loadouts / f"{HIVIS_LOADOUT}.json", hivis_loadout(olvas_json(alap_lo)))
        print(f"  ✓ AI öltözet: {HIVIS_LOADOUT} (piros, láthatósági mellény) a(z) {alap_lo.stem} fegyvereivel")
    else:
        print(f"  ⚠️ Nem találom az alap AI loadoutot itt: {loadouts}")
    ap_p = settings / "AIPatrolSettings.json"
    mgp = kuldetes / "mapgrouppos.xml"
    if ap_p.exists() and mgp.exists():
        ap = olvas_json(ap_p)
        ai = cfg["ai"]
        csoportok = katonai_csoportok(mgp.read_text(encoding="utf-8", errors="ignore"), ai["csoport_tavolsag"], ai["min_epulet"])
        minta = (ap.get("Patrols") or [None])[0]
        kizart = [gm] + ([bm_pos] if bm_pos else [])
        uj = jarorok(csoportok, ai, minta, kizart)
        ap["Enabled"] = True
        ap["Patrols"] = uj
        ap["ObjectPatrols"] = []  # a gyári (pl. rendőrségi, roncs körüli) AI ki: csak katonai helyeken legyen
        ir_json(ap_p, ap)
        db = {"Dél": 0, "Észak": 0, "Reptér": 0}
        for j in uj:
            db[j["Name"].split()[1]] += 1
        print(f"  ✓ AI járőrök: {len(uj)} katonai helyen (dél: {db['Dél']}, észak: {db['Észak']}, reptér: {db['Reptér']})")
    else:
        print("  ⚠️ Nem találom az AIPatrolSettings.json-t vagy a mapgrouppos.xml-t, az AI beállítás kimaradt.")

    print("\n✅ Kész. Indítsd el újra a szervert (inditas.bat).")


# ---------------------------------------------------------------- osztálynév-kereső
def keres(szo: str) -> None:
    cfg = beallitasok()
    _, szerver = utvonalak(cfg)
    minta = re.compile(rb"[A-Za-z_][A-Za-z0-9_]{2,63}")
    szo_l = szo.lower().encode()
    talalat: dict[str, set[str]] = {}
    for mod in sorted(szerver.glob("@*")):
        for f in list(mod.rglob("*.pbo")) + list(mod.rglob("*.xml")):
            try:
                adat = f.read_bytes()
            except OSError:
                continue
            for m in minta.finditer(adat):
                s = m[0]
                if szo_l in s.lower() and not s.lower().startswith((b"str_", b"dz_")):
                    talalat.setdefault(mod.name, set()).add(s.decode())
    if not talalat:
        print(f"Nincs találat erre: {szo}")
    for mod, nevek in talalat.items():
        print(f"\n{mod}:")
        for n in sorted(nevek, key=lambda x: (len(x), x))[:40]:
            print("   ", n)
    print("\nTipp: az autó osztályneve általában a legrövidebb, nagybetűs, alulvonásos név (pl. a mod nevével kezdődik).")


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # ékezetek és ikonok a Windows konzolon is
        except (AttributeError, ValueError):
            pass
    if len(argv) < 2 or argv[1] not in ("telepit", "frissit", "testreszab", "keres"):
        print(__doc__)
        return 1
    try:
        if argv[1] == "telepit":
            telepit(ujra="--ujra" in argv)
        elif argv[1] == "frissit":
            telepit(frissit=True)
        elif argv[1] == "testreszab":
            testreszab()
        else:
            if len(argv) < 3:
                print("Mit keressek? Pl.: python goblin.py keres GTR")
                return 1
            keres(argv[2])
    except Hiba as e:
        print(f"\n❌ {e}")
        return 1
    except KeyboardInterrupt:
        print("\nMegszakítva.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
