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
Config.RunnerCars = { 'sultan', 'elegy2', 'kuruma', 'jester', 'comet2' }
Config.CopCars = { 'police', 'police2', 'police3' }

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
