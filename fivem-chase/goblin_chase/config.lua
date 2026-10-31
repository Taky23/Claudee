Config = {}

-- Ennyi játékos kell egy üldözéshez (1 menekülő + legalább 1 rendőr).
Config.MinPlayers = 2

-- A motor „egészsége” 1000 (új) és -4000 (felrobbant) között van. Kb. 400 alatt kezd füstölni.
-- Ha a menekülő kocsija ez alá esik, az üldözésnek vége: a rendőrök nyertek.
Config.SmokeThreshold = 400.0

-- Ha a menekülő ennyi másodpercig nincs a kocsijában, elkapottnak számít.
Config.OutOfCarSeconds = 10

-- Visszaszámlálás az indulásig (mp), és ennyivel később indulhatnak a rendőrök.
Config.Countdown = 5
Config.HeadStart = 10

-- Ha a menekülő ennyi ideig kibírja, ő nyer (mp).
Config.RoundTime = 600

-- A rendőrök ilyen időközönként látják a térképen, merre jár nagyjából a menekülő (mp). 0 = soha.
Config.PingInterval = 20
Config.PingRadius = 120.0

-- Forgalom sűrűsége (0.0 = üres utak, 1.0 = normál).
Config.Traffic = 0.5

-- Kocsik: a listából véletlenszerűen kap egyet mindenki.
-- Az autók (add-on modok, lásd README). Ugyanezeket kapják a menekülők ÉS a rendőrök is, csak más színben.
-- A neveket a kocsik vehicles.meta fájljában lévő <modelName> alapján kell ellenőrizni!
Config.Cars = {
    'bolide',   -- 2020 Bugatti Bolide
    'rsq3',     -- 2021 Audi RS Q3 (Prior Design)
    'm3comp',   -- BMW M3 Competition
    'jesko',    -- Koenigsegg Jesko
}
Config.RunnerCars = Config.Cars
Config.CopCars = Config.Cars

-- Színek (RGB): a menekülő fekete, a rendőrök sötétkékek.
Config.RunnerColor = { 8, 8, 8 }
Config.CopColor = { 10, 25, 80 }
Config.RunnerPlate = 'GOBLIN'
Config.CopPlate = 'RENDOR'

-- Ha egy kocsi nincs telepítve (vagy elírtuk a nevét), ezt kapja helyette, hogy az üldözés ne akadjon el.
Config.FallbackRunnerCar = 'sultan'
Config.FallbackCopCar = 'sultan'

-- ---------------------------------------------------------------- HANDLING
-- Fix végsebesség: ennél egyik kocsi sem megy gyorsabban (km/h), és mindegyik el is éri.
Config.MaxSpeedKmh = 180

-- Közös alap: minden üldözős kocsi ebből indul, így hasonlóak maradnak.
-- A kár-értékek mindenkinél azonosak, hogy a „füst” szabály igazságos legyen.
Config.HandlingBase = {
    fMass = 1500.0,                 -- tömeg (kg): nehezebb = erősebb ütközésnél, lomhább
    fInitialDriveForce = 0.32,      -- gyorsulás
    fTractionCurveMax = 2.45,       -- tapadás kanyarban (max)
    fTractionCurveMin = 2.20,       -- tapadás csúszásnál (min)
    fBrakeForce = 0.95,             -- fék
    fSteeringLock = 40.0,           -- kormány kitérés (fok)
    fEngineDamageMult = 1.0,        -- mennyire sérül a motor ütközéstől (mindenkinél ugyanannyi!)
    fCollisionDamageMult = 1.0,
    fDeformationDamageMult = 0.8,
}

-- Profilok: kis eltérések (szorzók) az alaphoz képest, hogy mindegyik kocsi más legyen, de egyik se legyen sokkal jobb.
-- Ami nincs felsorolva, az az alap szerint marad.
Config.HandlingProfiles = {
    alap      = { label = 'Kiegyensúlyozott' },
    gyorsulo  = { label = 'Gyorsuló',   fInitialDriveForce = 1.15, fTractionCurveMax = 0.93, fTractionCurveMin = 0.93 },
    tapados   = { label = 'Tapadós',    fTractionCurveMax = 1.10, fTractionCurveMin = 1.10, fInitialDriveForce = 0.92 },
    nehez     = { label = 'Nehéz',      fMass = 1.35, fInitialDriveForce = 0.95, fBrakeForce = 0.92 },
    forgekony = { label = 'Fordulékony', fSteeringLock = 1.15, fBrakeForce = 1.08, fMass = 0.90, fTractionCurveMax = 0.97 },
}

-- Melyik kocsi melyik profilt kapja (a modell neve kisbetűvel). Ami nincs itt, az „alap”.
-- Saját (mod) autónál ide írd be a modell nevét és a profilt, pl.: ['skyline'] = 'gyorsulo',
Config.CarProfiles = {
    bolide  = 'gyorsulo',
    jesko   = 'forgekony',
    m3comp  = 'tapados',
    rsq3    = 'nehez',
    sultan  = 'alap',
}

-- Helyszínek. Saját helyszínhez állj oda a kocsival, írd be a chatbe: /chasepos
-- és a kiírt koordinátát másold ide. A /chase parancs véletlenszerűen választ, vagy név szerint: /chase 0 sivatag
Config.Scenarios = {
    {
        name = 'varos',
        label = 'Los Santos belváros',
        runner = { x = 215.0, y = -810.0, z = 30.7, h = 160.0 },
        cops = { x = 428.0, y = -983.0, z = 30.7, h = 90.0 },
    },
    {
        name = 'sivatag',
        label = 'Sandy Shores',
        runner = { x = 1720.0, y = 3260.0, z = 41.2, h = 105.0 },
        cops = { x = 1855.0, y = 3680.0, z = 34.2, h = 210.0 },
    },
}
