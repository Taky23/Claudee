local round = nil

local function chat(target, msg, color)
    TriggerClientEvent('chat:addMessage', target, { color = color or { 255, 200, 0 }, args = { 'CHASE', msg } })
end

local function pick(list)
    return list[math.random(#list)]
end

local function online(id)
    return id and GetPlayerName(id) ~= nil
end

local function scenarioByName(name)
    for _, s in ipairs(Config.Scenarios) do
        if s.name == name then return s end
    end
    return nil
end

-- A rendőröket a kezdőpont mögé, egymás mögé sorba állítjuk, hogy ne egymásba spawnoljanak.
local function copSpawn(base, index)
    local rad = math.rad(base.h)
    local back = 8.0 * (index - 1)
    return { x = base.x + math.sin(rad) * back, y = base.y - math.cos(rad) * back, z = base.z, h = base.h }
end

local REASONS = {
    smoke = 'füstölni kezdett a kocsija',
    destroyed = 'tönkrement a kocsija',
    dead = 'meghalt',
    left_car = 'kiszállt a kocsijából',
    left = 'kilépett a szerverről',
    time = 'kibírta az időt',
    stopped = 'leállították az üldözést',
}

local function finish(winner, reason)
    if not round then return end
    local runnerName = GetPlayerName(round.runner) or 'A menekülő'
    local text
    if winner == 'cops' then
        text = ('🚓 ELKAPTÁK! %s %s. A rendőrök nyertek!'):format(runnerName, REASONS[reason] or reason)
    elseif winner == 'runner' then
        text = ('🏁 %s %s – a menekülő nyert!'):format(runnerName, REASONS[reason] or reason)
    else
        text = '⛔ Az üldözést leállították.'
    end
    chat(-1, text)
    TriggerClientEvent('goblin_chase:finish', -1, { winner = winner, text = text })
    round = nil
end

local function startRound(source, args)
    if round then
        chat(source, 'Már megy egy üldözés. Leállítás: /chasestop')
        return
    end
    local players = {}
    for _, p in ipairs(GetPlayers()) do players[#players + 1] = tonumber(p) end
    if #players < Config.MinPlayers then
        chat(source, ('Legalább %d játékos kell (most: %d).'):format(Config.MinPlayers, #players))
        return
    end

    local runner = tonumber(args[1])
    if not runner or runner == 0 then
        runner = pick(players)
    elseif not online(runner) then
        chat(source, ('Nincs ilyen játékos: %s. A számot a játékoslistában látod.'):format(args[1]))
        return
    end
    local scenario
    if args[2] then
        scenario = scenarioByName(args[2])
    else
        scenario = pick(Config.Scenarios)
    end
    if not scenario then
        chat(source, ('Nincs ilyen helyszín: %s'):format(args[2]))
        return
    end

    round = { runner = runner, cops = {}, running = false, id = math.random(1, 1000000) }
    local myRound = round.id
    for _, p in ipairs(players) do
        if p ~= runner then round.cops[#round.cops + 1] = p end
    end

    TriggerClientEvent('goblin_chase:start', runner, {
        role = 'runner', spawn = scenario.runner, model = pick(Config.RunnerCars),
        countdown = Config.Countdown, roundTime = Config.RoundTime,
    })
    for i, cop in ipairs(round.cops) do
        TriggerClientEvent('goblin_chase:start', cop, {
            role = 'cop', spawn = copSpawn(scenario.cops, i), model = pick(Config.CopCars),
            countdown = Config.Countdown + Config.HeadStart, roundTime = Config.RoundTime - Config.HeadStart,
        })
    end
    chat(-1, ('🏎️ Üldözés indul (%s)! Menekülő: %s, rendőrök: %d fő. Ha a menekülő kocsija füstölni kezd, vége!')
        :format(scenario.label, GetPlayerName(runner), #round.cops))

    CreateThread(function()
        Wait(Config.Countdown * 1000)
        if not round or round.id ~= myRound then return end
        round.running = true
        local endsAt = os.time() + Config.RoundTime
        local nextPing = os.time() + Config.HeadStart + Config.PingInterval
        while round and round.id == myRound do
            if not online(round.runner) then
                finish('cops', 'left')
                break
            end
            if os.time() >= endsAt then
                finish('runner', 'time')
                break
            end
            if Config.PingInterval > 0 and os.time() >= nextPing then
                nextPing = os.time() + Config.PingInterval
                local c = GetEntityCoords(GetPlayerPed(round.runner))
                for _, cop in ipairs(round.cops) do
                    TriggerClientEvent('goblin_chase:ping', cop, { x = c.x, y = c.y, z = c.z })
                end
            end
            Wait(1000)
        end
    end)
end

RegisterCommand('chase', function(source, args)
    if source == 0 then source = -1 end
    startRound(source, args)
end, false)

RegisterCommand('chasestop', function(source)
    if not round then
        chat(source == 0 and -1 or source, 'Nincs futó üldözés.')
        return
    end
    finish('none', 'stopped')
end, false)

RegisterNetEvent('goblin_chase:caught', function(reason)
    local src = source
    if round and round.running and src == round.runner and REASONS[reason] then
        finish('cops', reason)
    end
end)

AddEventHandler('playerDropped', function()
    local src = source
    if not round then return end
    if src == round.runner then
        finish('cops', 'left')
        return
    end
    for i, cop in ipairs(round.cops) do
        if cop == src then
            table.remove(round.cops, i)
            break
        end
    end
end)
