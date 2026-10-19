"""A gyilkossági rejtély tiszta játéklogikája (Discord nélkül, így tesztelhető)."""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import asdict, dataclass, field

MURDERER = "gyilkos"
DETECTIVE = "detektiv"
DOCTOR = "orvos"
CIVILIAN = "civil"

ROLE_INFO = {
    MURDERER: (
        "🔪 Gyilkos",
        "Minden éjjel kiválasztasz egy áldozatot (`/rejtely akcio`). Éjjelente egyszer "
        "névtelenül suttoghatsz a csatornába (`/rejtely suttogas`). Nappal játszd az ártatlant – "
        "és vigyázz, a tetthelyen hagyott nyomok rád utalnak!",
    ),
    DETECTIVE: (
        "🕵️ Detektív",
        "Minden éjjel kihallgathatsz valakit (`/rejtely akcio`), és megtudod, ő-e a gyilkos. "
        "Óvatosan oszd meg, amit tudsz – a gyilkos rád fog vadászni.",
    ),
    DOCTOR: (
        "🩺 Orvos",
        "Minden éjjel megvédhetsz valakit, akár saját magadat is (`/rejtely akcio`). "
        "Ha a gyilkos őt támadja meg, túléli.",
    ),
    CIVILIAN: (
        "🙂 Civil",
        "Nincs éjszakai képességed, de nappal a szavazatod mindent eldönthet. Figyeld a nyomokat! "
        "Éjjel te is nyugodtan használd a `/rejtely akcio` parancsot, hogy ne lógj ki.",
    ),
}

TRAITS = {
    "ital": ["kávé", "vörösbor", "energiaital", "forró kakaó", "pálinka", "zöld tea"],
    "illat": ["levendula", "cigarettafüst", "fahéj", "benzin", "rózsa", "menta"],
    "targy": ["bőrkesztyű", "öngyújtó", "kulcscsomó", "napszemüveg", "kötött sál", "töltőtoll"],
}
TRAIT_LABEL = {"ital": "🍷 Ital", "illat": "👃 Illat", "targy": "🧤 Tárgy"}
CLUE_TEMPLATES = {
    "ital": "A holttest mellett egy pohár maradt, benne: **{v}**.",
    "illat": "A tetthelyen erős illat terjengett: **{v}**.",
    "targy": "A tettes elhagyott valamit a helyszínen: **{v}**.",
}

MIN_PLAYERS = 4
MAX_PLAYERS = 20
SKIP = 0  # szavazás: "senkit"

TOWN_WIN = "varos"
MURDERER_WIN = "gyilkos"


class GameError(Exception):
    """Felhasználónak megmutatható hiba."""


@dataclass
class Player:
    id: int
    name: str
    role: str = CIVILIAN
    alive: bool = True
    traits: dict = field(default_factory=dict)

    def trait_line(self) -> str:
        return " · ".join(self.traits.get(k, "?") for k in TRAITS)


@dataclass
class NightResult:
    victim: Player | None
    saved: Player | None
    clue: str | None
    random_kill: bool


@dataclass
class DayResult:
    eliminated: Player | None
    tally: dict
    tie: bool
    no_votes: bool


@dataclass
class Game:
    channel_id: int
    guild_id: int
    host_id: int
    night_minutes: int = 10
    day_minutes: int = 20
    phase: str = "lobby"  # lobby | night | day | ended
    round: int = 0
    deadline: float | None = None
    players: dict = field(default_factory=dict)  # str(id) -> Player
    kill_target: int | None = None
    protect_target: int | None = None
    investigated: bool = False
    whisper_used: bool = False
    votes: dict = field(default_factory=dict)  # str(voter id) -> target id (0 = senki)
    revealed: list = field(default_factory=list)
    winner: str | None = None
    lobby_message_id: int | None = None

    # ---------- segédek ----------
    def get(self, uid: int) -> Player | None:
        return self.players.get(str(uid))

    def alive_players(self) -> list[Player]:
        return [p for p in self.players.values() if p.alive]

    def murderer(self) -> Player | None:
        return next((p for p in self.players.values() if p.role == MURDERER), None)

    def _alive_player(self, uid: int, who: str = "Ő") -> Player:
        p = self.get(uid)
        if p is None:
            raise GameError(f"{who} nem játszik ebben a játékban.")
        if not p.alive:
            raise GameError(f"{who} már halott." if who != "Te" else "Te már halott vagy – a holtak nem cselekedhetnek.")
        return p

    # ---------- lobby ----------
    def add_player(self, uid: int, name: str) -> None:
        if self.phase != "lobby":
            raise GameError("A játék már elindult, most nem lehet csatlakozni.")
        if str(uid) in self.players:
            raise GameError("Már bent vagy a játékban.")
        if len(self.players) >= MAX_PLAYERS:
            raise GameError(f"A játék megtelt ({MAX_PLAYERS} fő).")
        self.players[str(uid)] = Player(id=uid, name=name)

    def remove_player(self, uid: int) -> None:
        if self.phase != "lobby":
            raise GameError("A játék már elindult, most nem lehet kilépni.")
        if self.players.pop(str(uid), None) is None:
            raise GameError("Nem vagy benne a játékban.")

    def start(self, now: float, rng: random.Random | None = None) -> None:
        rng = rng or random.Random()
        if self.phase != "lobby":
            raise GameError("A játék már elindult.")
        n = len(self.players)
        if n < MIN_PLAYERS:
            raise GameError(f"Legalább {MIN_PLAYERS} játékos kell (most {n} van).")

        players = list(self.players.values())
        rng.shuffle(players)
        roles = [MURDERER, DETECTIVE] + ([DOCTOR] if n >= 5 else [])
        roles += [CIVILIAN] * (n - len(roles))
        for p, r in zip(players, roles):
            p.role = r
            p.traits = {k: rng.choice(v) for k, v in TRAITS.items()}

        # Minden gyilkos-tulajdonság legyen meg legalább egy ártatlannál is,
        # így egyetlen nyom sosem bizonyíték, csak a nyomok együtt.
        m = self.murderer()
        others = [p for p in players if p is not m]
        for k in TRAITS:
            if not any(p.traits[k] == m.traits[k] for p in others):
                rng.choice(others).traits[k] = m.traits[k]

        self.round = 1
        self._begin_night(now)

    # ---------- fázisok ----------
    def _begin_night(self, now: float) -> None:
        self.phase = "night"
        self.deadline = now + self.night_minutes * 60
        self.kill_target = None
        self.protect_target = None
        self.investigated = False
        self.whisper_used = False

    def _begin_day(self, now: float) -> None:
        self.phase = "day"
        self.deadline = now + self.day_minutes * 60
        self.votes = {}

    def act(self, actor_id: int, target_id: int) -> str:
        if self.phase != "night":
            raise GameError("Akciót csak éjszaka lehet végrehajtani.")
        actor = self._alive_player(actor_id, "Te")
        if actor.role == CIVILIAN:
            return "Civilként nincs éjszakai képességed. Nyugi, senki nem látja, hogy ezt a parancsot használtad. 🤫"
        target = self._alive_player(target_id, "A célpont")

        if actor.role == MURDERER:
            if target.id == actor.id:
                raise GameError("Saját magadat nem választhatod áldozatnak.")
            self.kill_target = target.id
            return f"🔪 Az áldozatod: **{target.name}**. Ha az orvos nem védi meg, reggelre halott lesz. (Napfelkeltéig meggondolhatod magad.)"
        if actor.role == DETECTIVE:
            if target.id == actor.id:
                raise GameError("Saját magadat nem hallgathatod ki.")
            if self.investigated:
                raise GameError("Ma éjjel már kihallgattál valakit.")
            self.investigated = True
            if target.role == MURDERER:
                return f"🕵️ A kihallgatás eredménye: **{target.name} A GYILKOS!** 🩸"
            return f"🕵️ A kihallgatás eredménye: **{target.name}** nem a gyilkos."
        if actor.role == DOCTOR:
            self.protect_target = target.id
            return f"🩺 Ma éjjel **{target.name}** életére vigyázol. (Napfelkeltéig meggondolhatod magad.)"
        raise GameError("Ismeretlen szerep.")

    def whisper(self, actor_id: int) -> None:
        if self.phase != "night":
            raise GameError("Suttogni csak éjszaka lehet.")
        actor = self._alive_player(actor_id, "Te")
        if actor.role != MURDERER:
            raise GameError("Csak a gyilkos suttoghat a sötétből… és te nem az vagy. 🙂")
        if self.whisper_used:
            raise GameError("Ma éjjel már suttogtál.")
        self.whisper_used = True

    def vote(self, voter_id: int, target_id: int | None) -> Player | None:
        if self.phase != "day":
            raise GameError("Szavazni csak nappal lehet.")
        self._alive_player(voter_id, "Te")
        if target_id is None:
            self.votes[str(voter_id)] = SKIP
            return None
        target = self._alive_player(target_id, "A célpont")
        self.votes[str(voter_id)] = target.id
        return target

    def _next_clue(self, rng: random.Random) -> str | None:
        m = self.murderer()
        left = [k for k in TRAITS if k not in self.revealed]
        if not m or not left:
            return None
        k = rng.choice(left)
        self.revealed.append(k)
        return CLUE_TEMPLATES[k].format(v=m.traits[k])

    def clues(self) -> list[str]:
        m = self.murderer()
        return [CLUE_TEMPLATES[k].format(v=m.traits[k]) for k in self.revealed] if m else []

    def resolve_night(self, rng: random.Random) -> NightResult:
        victim_id, random_kill = self.kill_target, False
        if victim_id is None or not (self.get(victim_id) and self.get(victim_id).alive):
            pool = [p for p in self.alive_players() if p.role != MURDERER]
            victim_id = rng.choice(pool).id if pool else None
            random_kill = True
        if victim_id is None:
            return NightResult(None, None, None, random_kill)
        target = self.get(victim_id)
        if victim_id == self.protect_target:
            return NightResult(None, target, None, random_kill)
        target.alive = False
        clue = self._next_clue(rng)
        self._check_winner()
        return NightResult(target, None, clue, random_kill)

    def resolve_day(self) -> DayResult:
        alive_ids = {p.id for p in self.alive_players()}
        tally = Counter(t for v, t in self.votes.items() if int(v) in alive_ids)
        if not tally:
            return DayResult(None, {}, False, True)
        ranked = tally.most_common()
        top = ranked[0][1]
        leaders = [t for t, c in ranked if c == top]
        if len(leaders) > 1:
            return DayResult(None, dict(tally), True, False)
        if leaders[0] == SKIP:
            return DayResult(None, dict(tally), False, False)
        p = self.get(leaders[0])
        p.alive = False
        self._check_winner()
        return DayResult(p, dict(tally), False, False)

    def _check_winner(self) -> None:
        m = self.murderer()
        if m and not m.alive:
            self.winner = TOWN_WIN
        elif len([p for p in self.alive_players() if p.role != MURDERER]) <= 1:
            self.winner = MURDERER_WIN
        if self.winner:
            self.phase = "ended"
            self.deadline = None

    def advance(self, now: float, rng: random.Random | None = None):
        """Lezárja az aktuális fázist. Visszaad: ("night", NightResult) vagy ("day", DayResult)."""
        rng = rng or random.Random()
        if self.phase == "night":
            res = self.resolve_night(rng)
            if self.phase != "ended":
                self._begin_day(now)
            return "night", res
        if self.phase == "day":
            res = self.resolve_day()
            if self.phase != "ended":
                self.round += 1
                self._begin_night(now)
            return "day", res
        raise GameError("Most nincs lezárható fázis.")

    # ---------- mentés ----------
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Game":
        d = dict(d)
        d["players"] = {k: Player(**v) for k, v in d.get("players", {}).items()}
        return cls(**d)
