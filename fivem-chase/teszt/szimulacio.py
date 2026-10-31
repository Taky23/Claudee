"""A goblin_chase szerver- és kliens-logikájának szimulációja kamu FiveM API-val (lupa kell hozzá: pip install lupa)."""
import pathlib

import lupa

ROOT = pathlib.Path(__file__).resolve().parent.parent / "goblin_chase"

MOCK_SERVER = r"""
events, commands, handlers, threads, sent = {}, {}, {}, {}, {}
NOW = 1000
os = { time = function() return NOW end }
math.randomseed(1)
PLAYERS = { "1", "2", "3" }
NAMES = { [1] = "Taky", [2] = "Haver", [3] = "Masik" }
function GetPlayers() return PLAYERS end
function GetPlayerName(id) return NAMES[tonumber(id)] end
function GetPlayerPed(id) return id end
function GetEntityCoords(e) return { x = 1, y = 2, z = 3 } end
function TriggerClientEvent(name, target, data) table.insert(sent, { name = name, target = target, data = data }) end
function RegisterCommand(n, f) commands[n] = f end
function RegisterNetEvent(n, f) events[n] = f end
function AddEventHandler(n, f) handlers[n] = f end
THREADS = {}
function CreateThread(f) table.insert(THREADS, { co = coroutine.create(f), wake = 0 }) end
function Wait(ms) coroutine.yield(ms) end
function tick(seconds)
  for _ = 1, seconds do
    NOW = NOW + 1
    for i = #THREADS, 1, -1 do
      local th = THREADS[i]
      if coroutine.status(th.co) == "dead" then table.remove(THREADS, i)
      elseif NOW >= th.wake then
        local ok, w = coroutine.resume(th.co); if not ok then error(w) end
        th.wake = NOW + math.floor((w or 0) / 1000)
      end
    end
  end
end
function count(name) local n = 0; for _, m in ipairs(sent) do if m.name == name then n = n + 1 end end; return n end
function last(name) for i = #sent, 1, -1 do if sent[i].name == name then return sent[i] end end end
function lastchat() for i = #sent, 1, -1 do if sent[i].name == "chat:addMessage" then return sent[i].data.args[2] end end end
"""


def server():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK_SERVER)
    lua.execute((ROOT / "config.lua").read_text())
    lua.execute((ROOT / "server.lua").read_text())
    return lua


def test_smoke_ends_chase():
    lua = server()
    lua.execute("commands.chase(1, { '2', 'sivatag' })")
    assert lua.eval("count('goblin_chase:start')") == 3
    assert lua.eval("last('goblin_chase:start').target") == 3  # a második rendőr
    runner_start = lua.eval("(function() for _, m in ipairs(sent) do if m.name=='goblin_chase:start' and m.data.role=='runner' then return m.target end end end)()")
    assert runner_start == 2
    # visszaszámlálás alatt a "füst" még nem számít
    lua.execute("source = 2; events['goblin_chase:caught']('smoke')")
    assert lua.eval("count('goblin_chase:finish')") == 0
    lua.execute("tick(6)")
    lua.execute("source = 1; events['goblin_chase:caught']('smoke')")  # nem a menekülő küldte
    assert lua.eval("count('goblin_chase:finish')") == 0
    lua.execute("source = 2; events['goblin_chase:caught']('smoke')")
    assert lua.eval("count('goblin_chase:finish')") == 1
    assert lua.eval("last('goblin_chase:finish').data.winner") == "cops"
    assert "füstölni" in lua.eval("lastchat()")
    lua.execute("tick(5)")  # a szerver szála leáll, nincs több üzenet
    assert lua.eval("count('goblin_chase:finish')") == 1
    lua.execute("commands.chase(1, {})")  # újra indítható
    assert lua.eval("count('goblin_chase:start')") == 6


def test_runner_wins_on_time_and_pings():
    lua = server()
    lua.execute("Config.RoundTime = 60; Config.PingInterval = 20; commands.chase(1, { '1' })")
    lua.execute("tick(64)")
    assert lua.eval("count('goblin_chase:finish')") == 0
    assert lua.eval("count('goblin_chase:ping')") >= 2  # 2 rendőr x legalább 1 jelzés
    lua.execute("tick(2)")
    assert lua.eval("last('goblin_chase:finish').data.winner") == "runner"


def test_runner_leaving_and_guards():
    lua = server()
    lua.execute("PLAYERS = { '1' }; commands.chase(1, {})")
    assert "Legalább 2" in lua.eval("lastchat()")
    lua.execute("PLAYERS = { '1', '2' }; commands.chase(1, { '9' })")
    assert "Nincs ilyen játékos" in lua.eval("lastchat()")
    lua.execute("commands.chase(1, { '0', 'hold' })")
    assert "Nincs ilyen helyszín" in lua.eval("lastchat()")
    lua.execute("commands.chase(1, { '2' })")
    lua.execute("commands.chase(1, {})")
    assert "Már megy" in lua.eval("lastchat()")
    lua.execute("tick(6); source = 2; handlers.playerDropped()")
    assert lua.eval("last('goblin_chase:finish').data.winner") == "cops"


MOCK_CLIENT = r"""
T = 0
local ENGINE, PEDVEH, DEAD = 1000.0, 77, false
local serverEvents, netEvents, notes, texts = {}, {}, {}, {}
function GetGameTimer() return T end
function PlayerPedId() return 5 end
function PlayerId() return 0 end
function GetHashKey(s) return s end
MISSING = {}
function IsModelInCdimage(h) return not MISSING[h] end
function RequestModel() end
function HasModelLoaded() return true end
function SetEntityCoords() end
function CreateVehicle(h) SPAWNED = h; return 77 end
function SetModelAsNoLongerNeeded() end
function SetVehicleOnGroundProperly() end
function SetVehicleFixed() end
function SetVehicleEngineHealth() end
function SetVehicleNumberPlateText() end
function SetPedIntoVehicle() end
HANDLING = {}
function SetVehicleHandlingFloat(v, cls, field, value) HANDLING[field] = value end
function ModifyVehicleTopSpeed() end
function SetVehicleMaxSpeed(v, ms) MAXSPEED = ms end
function FreezeEntityPosition(e, f) FROZEN = f end
function SetVehicleSiren() end
function DoesEntityExist(e) return e == 77 end
function IsEntityDead(e) return DEAD and e == 5 end
function GetVehicleEngineHealth() return ENGINE end
function GetVehiclePedIsIn() return PEDVEH end
function TriggerServerEvent(n, r) table.insert(serverEvents, r) end
function BeginTextCommandThefeedPost() end
function AddTextComponentSubstringPlayerName(t) table.insert(texts, t) end
function EndTextCommandThefeedPostTicker() end
function SetTextFont() end function SetTextScale() end function SetTextColour() end function SetTextOutline() end
function SetTextCentre() end function BeginTextCommandDisplayText() end function EndTextCommandDisplayText() end
function DisableControlAction() end
function SetMaxWantedLevel() end function ClearPlayerWantedLevel() end
function SetVehicleDensityMultiplierThisFrame() end function SetRandomVehicleDensityMultiplierThisFrame() end
function SetParkedVehicleDensityMultiplierThisFrame() end
function SetEntityAsMissionEntity() end function DeleteVehicle(v) DELETED = v end
function DoesBlipExist() return true end function RemoveBlip() end
function RegisterNetEvent(n, f) netEvents[n] = f end
function RegisterCommand() end
function AddEventHandler() end
function GetCurrentResourceName() return 'goblin_chase' end
TIMEOUTS = {}
function SetTimeout(ms, f) table.insert(TIMEOUTS, { at = T + ms, f = f }) end
THREADS = {}
function CreateThread(f) table.insert(THREADS, { co = coroutine.create(f), wake = 0 }) end
function Wait(ms) coroutine.yield(ms) end
function step(ms)
  local target = T + ms
  while T < target do
    T = T + 50
    for i = #THREADS, 1, -1 do
      local th = THREADS[i]
      if coroutine.status(th.co) == 'dead' then table.remove(THREADS, i)
      elseif T >= th.wake then
        local ok, w = coroutine.resume(th.co); if not ok then error(w) end
        th.wake = T + (w or 0)
      end
    end
    for i = #TIMEOUTS, 1, -1 do if T >= TIMEOUTS[i].at then local f = TIMEOUTS[i].f; table.remove(TIMEOUTS, i); f() end end
  end
end
function setEngine(v) ENGINE = v end
function setInCar(b) PEDVEH = b and 77 or 0 end
function caught() return serverEvents[1] end
function start(role, model) netEvents['goblin_chase:start']({ role = role, spawn = { x = 0, y = 0, z = 0, h = 0 }, model = model or 'sultan', countdown = 5, roundTime = 600 }) end
function finish() netEvents['goblin_chase:finish']({ winner = 'cops', text = 'vege' }) end
"""


def client():
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK_CLIENT)
    lua.execute((ROOT / "config.lua").read_text())
    lua.execute((ROOT / "client.lua").read_text())
    return lua


def test_client_smoke_detection():
    lua = client()
    lua.execute("start('runner')")
    assert lua.eval("FROZEN") is True
    lua.execute("setEngine(300.0); step(3000)")  # visszaszámlálás alatt nem számít
    assert lua.eval("caught()") is None
    lua.execute("setEngine(1000.0); step(3000)")
    assert lua.eval("FROZEN") is False and lua.eval("caught()") is None
    lua.execute("setEngine(650.0); step(1000)")
    assert lua.eval("caught()") is None
    lua.execute("setEngine(399.0); step(500)")
    assert lua.eval("caught()") == "smoke"
    lua.execute("finish(); step(9000)")
    assert lua.eval("DELETED") == 77  # a kör vége után a kocsi eltűnik


def test_client_out_of_car():
    lua = client()
    lua.execute("start('runner'); step(6000); setInCar(false); step(9000)")
    assert lua.eval("caught()") is None
    lua.execute("step(1500)")
    assert lua.eval("caught()") == "left_car"


def test_cop_never_reports():
    lua = client()
    lua.execute("start('cop'); step(6000); setEngine(100.0); step(2000)")
    assert lua.eval("caught()") is None


def test_handling_profiles_and_fixed_top_speed():
    lua = client()
    lua.execute("start('runner')")  # sultan → tapados
    assert abs(lua.eval("MAXSPEED") - 180 / 3.6) < 1e-6
    assert abs(lua.eval("HANDLING.fTractionCurveMax") - 2.45 * 1.10) < 1e-6
    assert abs(lua.eval("HANDLING.fInitialDriveForce") - 0.32 * 0.92) < 1e-6
    assert lua.eval("HANDLING.fEngineDamageMult") == 1.0  # a kár mindenkinél egyforma
    assert lua.eval("HANDLING.fInitialDriveMaxFlatVel") > 180


def test_unknown_car_gets_base_profile():
    lua = client()
    lua.execute("Config.CarProfiles = {}; start('runner')")
    assert abs(lua.eval("HANDLING.fInitialDriveForce") - 0.32) < 1e-6


def test_profiles_are_balanced():
    lua = client()
    profiles = lua.eval("Config.HandlingProfiles")
    for name in list(profiles.keys()):
        p = profiles[name]
        for k in list(p.keys()):
            if k != "label":
                assert 0.85 <= p[k] <= 1.35, (name, k)  # csak kis eltérések


def test_bolide_runner_and_fallback():
    lua = client()
    lua.execute("start('runner', 'bolide')")
    assert lua.eval("SPAWNED") == "bolide"
    assert abs(lua.eval("HANDLING.fInitialDriveForce") - 0.32 * 1.15) < 1e-6  # gyorsuló profil
    lua2 = client()
    lua2.execute("MISSING['bolide'] = true; start('runner', 'bolide')")
    assert lua2.eval("SPAWNED") == "sultan"  # nincs telepítve → tartalék kocsi
    assert abs(lua2.eval("MAXSPEED") - 180 / 3.6) < 1e-6
