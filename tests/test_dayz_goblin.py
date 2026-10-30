import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("goblin", ROOT / "dayz-szerver" / "goblin.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

GM_TRADERS = """ExpansionTraderDenis.Clothing|3697.249512 402.01 5977.625488|70.48 0 0|SurgicalMask
ExpansionTraderRolf.Vehicles|3698.172607 402.01 5995.337402|-93.59 0 0|ReflexVest
ExpansionTraderNaomi.Vehicle_Parts|3690.062988 402.100067 6006.763672|131.95 0 0|ReflexVest
"""
ECON = """<?xml version="1.0"?>
<economycore>
	<ce folder="db">
		<file name="types.xml" type="types" />
	</ce>
</economycore>"""


def test_economycore_insert_replace_remove():
    s = g.economycore_beir(ECON, "goblin_ce", g.ce_blokk("goblin_ce", [("a.xml", "types")]))
    assert s.count('folder="goblin_ce"') == 1 and 'name="a.xml"' in s
    s = g.economycore_beir(s, "goblin_ce", g.ce_blokk("goblin_ce", [("b.xml", "types")]))
    assert s.count('folder="goblin_ce"') == 1 and 'name="b.xml"' in s and 'name="a.xml"' not in s
    s = g.economycore_beir(s, "goblin_ce", None)
    assert "goblin_ce" not in s and 'folder="db"' in s and s.strip().endswith("</economycore>")


def test_eventspawns_merge_skips_existing():
    cel = '<eventposdef>\n<event name="VehicleUAZ"><pos x="1" z="2" a="0" /></event>\n</eventposdef>'
    forras = '<eventposdef>\n\t<event name="VehicleUAZ">\n\t\t<pos x="9" /></event>\n\t<event name="VehicleBus">\n<pos x="3" /></event>\n</eventposdef>'
    out, n = g.eventspawns_osszefuz(cel, forras)
    assert n == 1 and out.count('name="VehicleUAZ"') == 1 and 'name="VehicleBus"' in out
    assert g.eventspawns_osszefuz(out, forras)[1] == 0


def test_vektor():
    assert g.vektor("1 2 3") == [1, 2, 3]
    assert g.vektor("1500.5, 210, 14000") == [1500.5, 210, 14000]
    assert g.vektor("") is None
    with pytest.raises(g.Hiba):
        g.vektor("1 2")


MGP = """<map>
<group name="Land_Mil_Barracks1" pos="1600 300 14000" rpy="0 0 0" a="0" />
<group name="Land_Mil_Barracks1" pos="1650 300 14050" rpy="0 0 0" a="0" />
<group name="Land_Mil_GuardTower" pos="1700 300 14100" rpy="0 0 0" a="0" />
<group name="Land_Mil_Barracks2" pos="2000 50 3000" rpy="0 0 0" a="0" />
<group name="Land_Mil_Tent_Big1_2" pos="2050 50 3050" rpy="0 0 0" a="0" />
<group name="Land_Mil_Barracks3" pos="2100 50 3100" rpy="0 0 0" a="0" />
<group name="Land_Mil_ATC_Big" pos="4800 10 2500" rpy="0 0 0" a="0" />
<group name="Land_Mil_Airfield_HQ" pos="4900 10 2500" rpy="0 0 0" a="0" />
<group name="Land_Mil_Barracks4" pos="5000 10 2500" rpy="0 0 0" a="0" />
<group name="Land_Mil_GuardBox_Green" pos="9000 100 9000" rpy="0 0 0" a="0" />
<group name="Land_House_1W01" pos="1610 300 14010" rpy="0 0 0" a="0" />
</map>"""
AI = {"eszak_hatar": 7680, "csoport_tavolsag": 250, "min_epulet": 3, "del": [1, 2], "eszak": [2, 4], "repter_plusz": 2,
      "pontossag": [0.25, 0.5], "sebzes_szorzo": 0.8, "kapott_sebzes_szorzo": 1.0, "ujraeledes_perc": 30}


def test_military_clusters_and_patrols():
    cs = g.katonai_csoportok(MGP, 250, 3)
    assert len(cs) == 3  # a magányos őrbódé és a civil ház kimarad
    assert sum(c["repter"] for c in cs) == 1
    pat = g.jarorok(cs, AI, None, kizart=[])
    by = {p["Name"].split()[1]: p for p in pat}
    assert (by["Észak"]["NumberOfAI"], by["Észak"]["NumberOfAIMax"]) == (2, 4)
    assert (by["Dél"]["NumberOfAI"], by["Dél"]["NumberOfAIMax"]) == (1, 2)
    assert (by["Reptér"]["NumberOfAI"], by["Reptér"]["NumberOfAIMax"]) == (3, 4)  # déli reptér: 1–2 + 2
    for p in pat:
        assert p["Loadout"] == g.HIVIS_LOADOUT and p["Chance"] == 1.0 and len(p["Waypoints"]) >= 3
        assert set(g.ALAP_JARULOR) <= set(p)
    # BM közelében nincs járőr
    assert len(g.jarorok(cs, AI, None, kizart=[[1650, 0, 14050]])) == 2


def test_hivis_loadout_keeps_weapons_and_cargo():
    alap = {"ClassName": "", "InventoryAttachments": [
        {"SlotName": "Shoulder", "Items": [{"ClassName": "M4A1"}]},
        {"SlotName": "Body", "Items": [{"ClassName": "M65Jacket_Olive", "InventoryCargo": [{"ClassName": "Mag_STANAG_30Rnd"}]}]},
    ]}
    lo = g.hivis_loadout(alap)
    slots = {s["SlotName"]: s for s in lo["InventoryAttachments"]}
    assert slots["Shoulder"]["Items"][0]["ClassName"] == "M4A1"
    assert [i["ClassName"] for i in slots["Body"]["Items"]] == g.HIVIS_RUHAK["Body"]
    assert all(i["InventoryCargo"][0]["ClassName"] == "Mag_STANAG_30Rnd" for i in slots["Body"]["Items"])
    assert slots["Vest"]["Items"][0]["ClassName"] == "ReflexVest"
    assert alap["InventoryAttachments"][1]["Items"][0]["ClassName"] == "M65Jacket_Olive"  # az eredeti érintetlen


def test_bm_map():
    trader, obj = g.bm_map({"helyzet": "1500 250 13900", "irany": 90})
    assert trader.startswith("ExpansionTraderLinda.GOBLIN_BlackMarket|1500.000000 250.000000 13900.000000|90.000000")
    assert len(obj.strip().splitlines()) == 4 and all(len(s.split("|")) >= 3 for s in obj.strip().splitlines())


# ---------------------------------------------------------------- teljes folyamat kamu szerveren
def fake_server(tmp_path, template):
    srv = tmp_path / "DayZServer"
    van = srv / "mpmissions" / "dayzOffline.chernarusplus"
    van.mkdir(parents=True)
    (van / "cfgeconomycore.xml").write_text(ECON, encoding="utf-8")
    (van / "cfgeventspawns.xml").write_text("<eventposdef>\n</eventposdef>", encoding="utf-8")
    (van / "mapgrouppos.xml").write_text(MGP, encoding="utf-8")
    (srv / "DayZServer_x64.exe").write_bytes(b"")
    tpl = tmp_path / "tpl"
    (tpl / "expansion" / "traders").mkdir(parents=True)
    (tpl / "expansion" / "objects").mkdir(parents=True)
    (tpl / "expansion_ce").mkdir()
    (tpl / "expansion_ce" / "expansion_types.xml").write_text("<types></types>")
    (tpl / "cfgeconomycore.xml").write_text("x")
    (tpl / "cfgeventspawns.xml").write_text('<eventposdef><event name="VehicleUAZ"><pos x="1" /></event></eventposdef>')
    (tpl / "expansion" / "traders" / "GreenMountain_Traders.map").write_text(GM_TRADERS)
    (tpl / "expansion" / "traders" / "Kamenka_Traders.map").write_text("x")
    (tpl / "expansion" / "objects" / "Green_Mountain_Trader.map").write_text("bldr_TB_Doors_C|3711 402 5955|0 0 0\n")
    return srv, tpl


def test_full_flow(tmp_path, monkeypatch):
    srv, tpl = fake_server(tmp_path, None)
    dayz = tmp_path / "DayZ"
    ws = dayz / "!Workshop"
    for name, extra in [("@CF", None), ("@Dabs Framework", None), ("@VPPAdminTools", None),
                        ("@DayZ-Expansion-Licensed", None), ("@DayZ-Expansion-Bundle", None),
                        ("@Escape From Tarkov", "types"), ("@SNAFU Weapons", "types")]:
        d = ws / name
        (d / "Keys").mkdir(parents=True)
        (d / "Keys" / f"{g.norm(name)}.bikey").write_bytes(b"k")
        (d / "addons").mkdir()
        (d / "addons" / "x.pbo").write_bytes(b"\x00class Bandit_NissanGTR\x00GTR_Wheel\x00")
        if extra:
            (d / "extras").mkdir()
            (d / "extras" / "types.xml").write_text('<types>\n<type name="EFT_Item"></type>\n</types>')
    cfg = json.loads((ROOT / "dayz-szerver" / "beallitasok.json").read_text(encoding="utf-8"))
    cfg["utvonalak"] = {"dayz": str(dayz), "dayz_szerver": str(srv)}
    cfg["superadminok_steam64"] = ["76561198000000000"]
    cfg["steam_felhasznalo"] = "goblin"
    for m in cfg["modok"]:  # a teszthez csak kettő jön a Workshopról, a többi a !Workshop mappából
        if m["nev"] not in ("CF", "DayZ-Expansion-Vehicles"):
            m["workshop"] = ""
    # a CF és az Expansion-Vehicles Workshop azonosítóval van megadva → SteamCMD tölti le (itt kamu letöltő)
    hivasok = []

    def kamu_steamcmd(args):
        hivasok.append(args)
        for i, a in enumerate(args):
            if a == "+workshop_download_item":
                wid = args[i + 2]
                d = g.workshop_tartalom(wid)
                (d / "keys").mkdir(parents=True)
                (d / "keys" / f"{wid}.bikey").write_bytes(b"k")
                nev = {"1559212036": "CF", "2291785437": "DayZ-Expansion-Vehicles"}[wid]
                (d / "meta.cpp").write_text(f'protocol = 1;\nname = "{nev}";\n')
    monkeypatch.setattr(g, "steamcmd_futtat", kamu_steamcmd)
    monkeypatch.setattr(g, "workshop_cimek", lambda ids: {"1559212036": "CF", "2291785437": "DayZ-Expansion-Vehicles"})
    cfgfile = tmp_path / "beallitasok.json"
    cfgfile.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setattr(g, "ITT", tmp_path)
    monkeypatch.setattr(g, "expansion_sablon", lambda: tpl)

    g.telepit()
    assert len(hivasok) == 1 and "+app_update" not in hivasok[0]  # a szerver már megvolt
    assert hivasok[0][:2] == ["+login", "goblin"] and hivasok[0].count("+workshop_download_item") == 2
    mis = srv / "mpmissions" / "goblin.chernarusplus"
    assert (srv / "@CF").is_dir() and (srv / "@DabsFramework").is_dir() and (srv / "keys" / "1559212036.bikey").exists()
    assert (srv / "@CF" / "meta.cpp").exists()  # a SteamCMD-s példány ment, nem a !Workshop-os
    bat = (srv / "inditas.bat").read_text()
    assert '"-mod=@CF;@DabsFramework;@VPPAdminTools;@DayZ-Expansion-Licensed;@DayZ-Expansion-Bundle;@DayZ-Expansion-Vehicles;@EscapeFromTarkov;@SNAFUWeapons"' in bat
    cfgtxt = (srv / "serverDZ.cfg").read_text(encoding="utf-8")
    assert 'template = "goblin.chernarusplus"' in cfgtxt and "maxPlayers = 5" in cfgtxt and "Loot Goblinok" in cfgtxt
    assert json.loads(cfgfile.read_text(encoding="utf-8"))["szerver"]["admin_jelszo"]
    econ = (mis / "cfgeconomycore.xml").read_text()
    assert 'folder="expansion_ce"' in econ and 'folder="goblin_ce"' in econ
    assert (mis / "goblin_ce" / "escapefromtarkov_0_types.xml").exists() and (mis / "goblin_ce" / "snafuweapons_0_types.xml").exists()
    assert not (srv / "@MortysWeapons").exists()  # nem kötelező, nincs feliratkozva
    assert 'name="VehicleUAZ"' in (mis / "cfgeventspawns.xml").read_text()
    tr = mis / "expansion" / "traders"
    assert sorted(p.name for p in tr.glob("*.map")) == ["GreenMountain_Traders.map"]
    assert "ExpansionTraderRolf.GOBLIN_Autok|" in (tr / "GreenMountain_Traders.map").read_text()
    assert "Vehicle_Parts|" in (tr / "GreenMountain_Traders.map").read_text()  # csak a Vehicles cserélődik
    assert len((mis / "expansion" / "objects" / "Goblin_GreenMountain_Fenyek.map").read_text().splitlines()) == 14
    assert (srv / "profiles" / "VPPAdminTools" / "Permissions" / "SuperAdmins" / "SuperAdmins.txt").read_text().strip() == "76561198000000000"
    g.telepit()  # újrafuttatható, és a már letöltött modokat nem tölti le újra
    assert len(hivasok) == 1
    assert (mis / "cfgeconomycore.xml").read_text().count('folder="goblin_ce"') == 1

    # --- testreszab előtt: első indítás nélkül szól
    with pytest.raises(g.Hiba):
        g.testreszab()
    # az "első indítás" kamu eredménye
    prof = srv / "profiles" / "ExpansionMod"
    car = {"ClassName": "offroadhatchback", "MaxPriceThreshold": 33600, "MinPriceThreshold": 20160, "SellPricePercent": -1,
           "MaxStockThreshold": 4, "MinStockThreshold": 1, "QuantityPercent": -1, "SpawnAttachments": ["HatchbackWheel"], "Variants": ["OffroadHatchback_Blue"]}
    g.ir_json(prof / "Market" / "Cars.json", {"m_Version": 12, "DisplayName": "Cars", "Icon": "Deliver", "Color": "FBFCFEFF", "IsExchange": 0, "InitStockPercent": 75, "Items": [car]})
    g.ir_json(prof / "Market" / "Helicopters.json", {"m_Version": 12, "DisplayName": "Helis", "Icon": "x", "Color": "x", "IsExchange": 0, "InitStockPercent": 75,
                                                    "Items": [dict(car, ClassName="ExpansionMh6", SpawnAttachments=["ExpansionHelicopterBattery"])]})
    g.ir_json(prof / "Traders" / "Vehicles.json", {"m_Version": 13, "DisplayName": "Vehicles", "TraderIcon": "Car", "Currencies": ["expansionbanknotehryvnia"],
                                                    "Categories": ["Cars:1"], "Items": {"offroadhatchback": 1}, "RequiredFaction": "", "MinRequiredReputation": 5})
    g.ir_json(prof / "Loadouts" / "WestLoadout.json", {"ClassName": "", "InventoryAttachments": [{"SlotName": "Shoulder", "Items": [{"ClassName": "M4A1"}]}]})
    st = mis / "expansion" / "settings"
    g.ir_json(st / "MarketSettings.json", {"VehicleKeys": [], "LandSpawnPositions": [{"Position": [3722.77, 402, 6018.93], "Orientation": [0, 0, 0]}],
                                           "AirSpawnPositions": [{"Position": [4000, 10, 2500], "Orientation": [0, 0, 0]}]})
    g.ir_json(st / "VehicleSettings.json", {"VehicleRequireKeyToStart": 0, "CanPickLock": True, "CanChangeLock": True})
    g.ir_json(st / "MapSettings.json", {"ServerMarkers": [
        {"m_UID": "a", "m_Text": "Green Mountain", "m_Position": [3700, 402, 5990]},
        {"m_UID": "b", "m_Text": "Kamenka", "m_Position": [1100, 10, 2400]}]})
    g.ir_json(st / "SafeZoneSettings.json", {"Enabled": 1, "CircleZones": [{"Center": [3700, 402, 5990], "Radius": 150}, {"Center": [1100, 10, 2400], "Radius": 100}],
                                             "PolygonZones": [{"Positions": [[11800, 0, 12400], [11900, 0, 12400], [11850, 0, 12500]]}], "CylinderZones": []})
    g.ir_json(st / "AIPatrolSettings.json", {"m_Version": 32, "Enabled": 1, "Patrols": [{"Name": "default", "Faction": "Civilian", "Chance": 0.3, "Behaviour": "ROAMING"}],
                                             "ObjectPatrols": [{"ObjectClassName": "Land_City_PoliceStation"}]})

    # BM helye még nincs megadva → kimarad, de minden más lefut
    g.testreszab()
    assert not (tr / "Goblin_BlackMarket.map").exists()
    autok = g.olvas_json(prof / "Market" / "GOBLIN_Autok.json")["Items"]
    assert len(autok) == 6
    ada = next(i for i in autok if i["ClassName"].lower() == "offroadhatchback")
    assert ada["SpawnAttachments"] == ["HatchbackWheel"] and (ada["MinPriceThreshold"], ada["MaxPriceThreshold"]) == (20000, 34000)
    assert next(i for i in autok if i["ClassName"] == "offroad_02")["SpawnAttachments"] == []  # nem volt az indexben: új, üres
    assert g.olvas_json(prof / "Market" / "GOBLIN_BM_Legi.json")["Items"][1]["SpawnAttachments"] == ["ExpansionHelicopterBattery"]
    bmt = g.olvas_json(prof / "Traders" / "GOBLIN_BlackMarket.json")
    assert bmt["Categories"] == ["GOBLIN_BM_Legi:0"] and bmt["Items"] == {} and bmt["MinRequiredReputation"] == 0
    assert bmt["Currencies"] == ["expansionbanknotehryvnia"]
    assert g.olvas_json(prof / "Traders" / "GOBLIN_Autok.json")["Categories"] == ["GOBLIN_Autok:0"]
    assert g.olvas_json(st / "MarketSettings.json")["VehicleKeys"] == ["ExpansionCarKey"]
    vs = g.olvas_json(st / "VehicleSettings.json")
    assert vs["VehicleRequireKeyToStart"] == 1 and vs["CanPickLock"] is False
    assert [m["m_UID"] for m in g.olvas_json(st / "MapSettings.json")["ServerMarkers"]] == ["a"]
    sz = g.olvas_json(st / "SafeZoneSettings.json")
    assert len(sz["CircleZones"]) == 1 and sz["PolygonZones"] == []
    ap = g.olvas_json(st / "AIPatrolSettings.json")
    assert ap["ObjectPatrols"] == [] and len(ap["Patrols"]) == 3 and all(p["Faction"] == "West" for p in ap["Patrols"])
    assert ap["Patrols"][0]["Behaviour"] == "ROAMING"  # a gyári minta mezői megmaradnak, ahol nem írjuk felül
    lo = g.olvas_json(prof / "Loadouts" / "GoblinHiVisLoadout.json")
    assert {s["SlotName"] for s in lo["InventoryAttachments"]} >= {"Shoulder", "Body", "Vest"}

    # BM megadva → NPC, tárgyak, lerakók, safezone, autók; jelölő nincs
    cfg = json.loads(cfgfile.read_text(encoding="utf-8"))
    cfg["black_market"].update({"helyzet": "1650 300 14050", "irany": 45, "jarmu_lerako": "1680 300 14060", "heli_lerako": "1700 300 14100"})
    cfg["black_market"]["autok"][0]["osztaly"] = "Bandit_NissanGTR"
    cfgfile.write_text(json.dumps(cfg), encoding="utf-8")
    g.testreszab()
    assert (tr / "Goblin_BlackMarket.map").read_text().startswith("ExpansionTraderLinda.GOBLIN_BlackMarket|1650.000000")
    assert g.olvas_json(prof / "Traders" / "GOBLIN_BlackMarket.json")["Categories"] == ["GOBLIN_BM_Legi:0", "GOBLIN_BM_Autok:0"]
    ms = g.olvas_json(st / "MarketSettings.json")
    assert len(ms["LandSpawnPositions"]) == 2 and len(ms["AirSpawnPositions"]) == 2
    g.testreszab()  # újrafuttatva nem duplikál
    ms = g.olvas_json(st / "MarketSettings.json")
    assert len(ms["LandSpawnPositions"]) == 2 and len(ms["AirSpawnPositions"]) == 2
    sz = g.olvas_json(st / "SafeZoneSettings.json")
    assert len(sz["CircleZones"]) == 2 and sz["CircleZones"][1]["Radius"] == 60.0
    assert len(g.olvas_json(st / "MapSettings.json")["ServerMarkers"]) == 1
    ap = g.olvas_json(st / "AIPatrolSettings.json")
    assert len(ap["Patrols"]) == 2  # a BM melletti katonai hely kimaradt


def test_keres(tmp_path, monkeypatch, capsys):
    srv = tmp_path / "DayZServer"
    (srv / "@BanditsNissanGTR" / "addons").mkdir(parents=True)
    (srv / "DayZServer_x64.exe").write_bytes(b"")
    (srv / "@BanditsNissanGTR" / "addons" / "gtr.pbo").write_bytes(b"\x00\x01Bandit_NissanGTR\x00Bandit_NissanGTR_Door_1_1\x00str_gtr_name\x00")
    monkeypatch.setattr(g, "beallitasok", lambda: {"utvonalak": {"dayz": str(tmp_path), "dayz_szerver": str(srv)}})
    g.keres("NissanGTR")
    out = capsys.readouterr().out
    assert "Bandit_NissanGTR" in out and "str_gtr_name" not in out


def test_workshop_id():
    assert g.workshop_id("2291785437") == "2291785437"
    assert g.workshop_id("https://steamcommunity.com/sharedfiles/filedetails/?id=2291785437&searchtext=") == "2291785437"
    assert g.workshop_id("") == "" and g.workshop_id("valami") == ""


def test_illik():
    cf = {"nev": "CF", "minta": "cf", "pontos": True, "mas_nevek": ["communityframework"]}
    assert g.illik(cf, "@CF") and g.illik(cf, "Community Framework") and not g.illik(cf, "@CF-Addon")
    assert g.illik({"minta": "snafu"}, "SNAFU Weapons")


def test_wrong_workshop_link_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "ITT", tmp_path)
    monkeypatch.setattr(g, "workshop_cimek", lambda ids: {ids[0]: "Some Random Map"})
    monkeypatch.setattr(g, "steamcmd_futtat", lambda args: pytest.fail("nem szabad letölteni"))
    cfg = {"steam_felhasznalo": "x", "modok": [{"nev": "SNAFUWeapons", "minta": "snafu", "workshop": "123"}]}
    with pytest.raises(g.Hiba, match="másik modra"):
        g.modok_letoltese(cfg, tmp_path, mindet=False)


def test_server_is_installed_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "ITT", tmp_path)
    monkeypatch.setattr(g, "workshop_cimek", lambda ids: {})
    hivas = []

    def kamu(args):
        hivas.append(args)
        d = Path(args[args.index("+force_install_dir") + 1])
        d.mkdir(parents=True)
        (d / "DayZServer_x64.exe").write_bytes(b"")
    monkeypatch.setattr(g, "steamcmd_futtat", kamu)
    cfg = {"steam_felhasznalo": "x", "modok": []}
    szerver = g.modok_letoltese(cfg, None, mindet=False)
    assert szerver == tmp_path / "DayZServer" and (szerver / "DayZServer_x64.exe").exists()
    assert hivas[0][:2] == ["+force_install_dir", str(tmp_path / "DayZServer")] and "223350" in hivas[0]


def test_server_side_mods_go_to_servermod():
    bat = g.inditas_bat({"szerver": {"port": 2302}}, [{"nev": "CF"}, {"nev": "HelicopterPack"}, {"nev": "SibnicServerSide", "csak_szerver": True}])
    assert '"-mod=@CF;@HelicopterPack" "-serverMod=@SibnicServerSide"' in bat
    assert "-serverMod" not in g.inditas_bat({"szerver": {}}, [{"nev": "CF"}])


def test_local_server_mod_is_found(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "ITT", tmp_path)
    (tmp_path / "szerver_modok" / "@Sibnic_Server_Side" / "addons").mkdir(parents=True)
    srv = tmp_path / "srv"
    srv.mkdir()
    cfg = {"modok": [{"nev": "SibnicServerSide", "minta": "sibnic", "csak_szerver": True, "helyi_mappa": "szerver_modok"}]}
    modok = g.modok_masolasa(cfg, None, srv)
    assert modok[0]["nev"] == "SibnicServerSide" and (srv / "@SibnicServerSide" / "addons").is_dir()


def test_broken_config_gives_readable_error(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "ITT", tmp_path)
    (tmp_path / "beallitasok.json").write_text('{\n  "szerver": {\n    "nev": "a" "b",\n  }\n}', encoding="utf-8")
    with pytest.raises(g.Hiba, match=r"3\. sorában") as e:
        g.beallitasok()
    assert '"nev": "a" "b",' in str(e.value)
    # a Jegyzettömb BOM-mal mentett fájlja is működik
    (tmp_path / "beallitasok.json").write_text('﻿{"a": 1}', encoding="utf-8")
    assert g.beallitasok() == {"a": 1}
