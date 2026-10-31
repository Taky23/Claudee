local active = nil

local function notify(msg)
    BeginTextCommandThefeedPost('STRING')
    AddTextComponentSubstringPlayerName(msg)
    EndTextCommandThefeedPostTicker(true, true)
end

local function drawText(text, x, y, scale)
    SetTextFont(4)
    SetTextScale(0.0, scale or 0.5)
    SetTextColour(255, 255, 255, 255)
    SetTextOutline()
    SetTextCentre(true)
    BeginTextCommandDisplayText('STRING')
    AddTextComponentSubstringPlayerName(text)
    EndTextCommandDisplayText(x, y)
end

local function deleteVehicle(veh)
    if veh and DoesEntityExist(veh) then
        SetEntityAsMissionEntity(veh, true, true)
        DeleteVehicle(veh)
    end
end

local function cleanup()
    if not active then return end
    if active.blips then
        for _, b in ipairs(active.blips) do
            if DoesBlipExist(b) then RemoveBlip(b) end
        end
    end
    deleteVehicle(active.veh)
    active = nil
end

-- A kocsira ráteszi a közös alap-handlinget, a profilja szerinti eltérést és a fix végsebességet.
local function applyHandling(veh, model)
    local profileName = Config.CarProfiles[string.lower(model)] or 'alap'
    local profile = Config.HandlingProfiles[profileName] or Config.HandlingProfiles.alap
    for field, base in pairs(Config.HandlingBase) do
        SetVehicleHandlingFloat(veh, 'CHandlingData', field, base * (profile[field] or 1.0))
    end
    local maxMs = Config.MaxSpeedKmh / 3.6
    -- A „papíron” elérhető végsebesség legyen kicsit a fix határ fölött, hogy minden kocsi elérje azt.
    SetVehicleHandlingFloat(veh, 'CHandlingData', 'fInitialDriveMaxFlatVel', Config.MaxSpeedKmh * 1.15)
    ModifyVehicleTopSpeed(veh, 1.0)
    SetVehicleMaxSpeed(veh, maxMs)
    return profile.label or profileName
end

local function spawnVehicle(model, s)
    local hash = GetHashKey(model)
    if not IsModelInCdimage(hash) then
        notify('Nincs ilyen kocsi: ' .. model)
        return nil
    end
    RequestModel(hash)
    local deadline = GetGameTimer() + 10000
    while not HasModelLoaded(hash) and GetGameTimer() < deadline do Wait(0) end
    if not HasModelLoaded(hash) then
        notify('Nem sikerült betölteni: ' .. model)
        return nil
    end
    local ped = PlayerPedId()
    SetEntityCoords(ped, s.x, s.y, s.z, false, false, false, false)
    local veh = CreateVehicle(hash, s.x, s.y, s.z, s.h, true, false)
    SetModelAsNoLongerNeeded(hash)
    SetVehicleOnGroundProperly(veh)
    SetVehicleFixed(veh)
    SetVehicleEngineHealth(veh, 1000.0)
    SetVehicleNumberPlateText(veh, 'GOBLIN')
    SetPedIntoVehicle(ped, veh, -1)
    return veh, applyHandling(veh, model)
end

-- A menekülő kliense figyeli a saját kocsiját; ha füstöl, szól a szervernek.
local function watchRunner(myActive)
    CreateThread(function()
        local outSince = nil
        while active == myActive and not myActive.finished do
            Wait(200)
            if GetGameTimer() >= myActive.startAt then
                local ped = PlayerPedId()
                local veh = myActive.veh
                local reason = nil
                if IsEntityDead(ped) then
                    reason = 'dead'
                elseif not DoesEntityExist(veh) or IsEntityDead(veh) then
                    reason = 'destroyed'
                elseif GetVehicleEngineHealth(veh) <= Config.SmokeThreshold then
                    reason = 'smoke'
                elseif GetVehiclePedIsIn(ped, false) ~= veh then
                    outSince = outSince or GetGameTimer()
                    if GetGameTimer() - outSince >= Config.OutOfCarSeconds * 1000 then
                        reason = 'left_car'
                    end
                else
                    outSince = nil
                end
                if reason then
                    TriggerServerEvent('goblin_chase:caught', reason)
                    return
                end
            end
        end
    end)
end

local function hud(myActive)
    CreateThread(function()
        while active == myActive do
            Wait(0)
            local now = GetGameTimer()
            local role = myActive.role == 'runner' and '~r~MENEKÜLŐ' or '~b~RENDŐR'
            drawText(role, 0.5, 0.03, 0.6)
            if myActive.profile then
                drawText(('%s · max %d km/h'):format(myActive.profile, Config.MaxSpeedKmh), 0.5, 0.95, 0.4)
            end
            if myActive.finished then
                drawText(myActive.finishedText, 0.5, 0.45, 0.7)
            elseif now < myActive.startAt then
                local left = math.ceil((myActive.startAt - now) / 1000)
                drawText(('Indulás: %d'):format(left), 0.5, 0.40, 1.2)
                DisableControlAction(0, 71, true) -- gáz
                DisableControlAction(0, 72, true) -- fék/hátra
            else
                local remaining = math.max(0, math.floor((myActive.endsAt - now) / 1000))
                drawText(('%d:%02d'):format(remaining // 60, remaining % 60), 0.5, 0.07, 0.5)
                if myActive.role == 'runner' and DoesEntityExist(myActive.veh) then
                    local hp = GetVehicleEngineHealth(myActive.veh)
                    local pct = math.max(0, math.floor((hp - Config.SmokeThreshold) / (1000.0 - Config.SmokeThreshold) * 100))
                    local color = pct > 50 and '~g~' or (pct > 20 and '~y~' or '~r~')
                    drawText(('Motor: %s%d%%'):format(color, pct), 0.5, 0.11, 0.5)
                end
            end
        end
    end)
end

RegisterNetEvent('goblin_chase:start', function(data)
    cleanup()
    local myActive = { role = data.role, blips = {} }
    active = myActive
    local veh, profileLabel = spawnVehicle(data.model, data.spawn)
    if not veh then return end
    myActive.veh = veh
    myActive.profile = profileLabel
    myActive.startAt = GetGameTimer() + data.countdown * 1000
    myActive.endsAt = myActive.startAt + data.roundTime * 1000
    FreezeEntityPosition(veh, true)
    CreateThread(function()
        while active == myActive and GetGameTimer() < myActive.startAt do Wait(50) end
        if active == myActive and not myActive.finished and DoesEntityExist(veh) then
            FreezeEntityPosition(veh, false)
            if myActive.role == 'cop' then SetVehicleSiren(veh, true) end
        end
    end)
    hud(myActive)
    if data.role == 'runner' then
        notify('Te vagy a ~r~menekülő~s~! Ne hagyd, hogy a kocsid füstölni kezdjen.')
        watchRunner(myActive)
    else
        notify('Te vagy a ~b~rendőr~s~! Rongyold le a menekülő kocsiját, amíg füstölni nem kezd.')
    end
end)

RegisterNetEvent('goblin_chase:ping', function(c)
    if not active or active.role ~= 'cop' then return end
    local area = AddBlipForRadius(c.x, c.y, c.z, Config.PingRadius)
    SetBlipColour(area, 1)
    SetBlipAlpha(area, 120)
    local dot = AddBlipForCoord(c.x, c.y, c.z)
    SetBlipSprite(dot, 161)
    SetBlipColour(dot, 1)
    table.insert(active.blips, area)
    table.insert(active.blips, dot)
    notify('📡 A menekülő utoljára itt járt (térkép).')
    local myActive = active
    SetTimeout(Config.PingInterval * 1000, function()
        for _, b in ipairs({ area, dot }) do
            if DoesBlipExist(b) then RemoveBlip(b) end
        end
        if myActive.blips then
            for i = #myActive.blips, 1, -1 do
                if myActive.blips[i] == area or myActive.blips[i] == dot then table.remove(myActive.blips, i) end
            end
        end
    end)
end)

RegisterNetEvent('goblin_chase:finish', function(data)
    if not active then return end
    local myActive = active
    myActive.finishedText = data.text
    myActive.finished = true -- a figyelés és a visszaszámláló leáll
    notify(data.text)
    SetTimeout(8000, function()
        if active == myActive then cleanup() end
    end)
end)

RegisterCommand('chasepos', function()
    local ped = PlayerPedId()
    local ent = GetVehiclePedIsIn(ped, false)
    if ent == 0 then ent = ped end
    local c = GetEntityCoords(ent)
    local text = ('{ x = %.1f, y = %.1f, z = %.1f, h = %.1f }'):format(c.x, c.y, c.z, GetEntityHeading(ent))
    TriggerEvent('chat:addMessage', { color = { 120, 200, 255 }, args = { 'POZÍCIÓ', text } })
    print(text)
end, false)

-- NPC rendőrök ne szóljanak bele, és a forgalom legyen ritkább.
CreateThread(function()
    while true do
        SetMaxWantedLevel(0)
        ClearPlayerWantedLevel(PlayerId())
        SetVehicleDensityMultiplierThisFrame(Config.Traffic)
        SetRandomVehicleDensityMultiplierThisFrame(Config.Traffic)
        SetParkedVehicleDensityMultiplierThisFrame(Config.Traffic)
        Wait(0)
    end
end)

AddEventHandler('onResourceStop', function(name)
    if name == GetCurrentResourceName() then cleanup() end
end)
