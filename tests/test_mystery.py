import random

import pytest

from core.mystery import (
    CIVILIAN, DETECTIVE, DOCTOR, MURDERER, MURDERER_WIN, TOWN_WIN, TRAITS, Game, GameError,
)


def make_game(n=5, seed=1):
    g = Game(channel_id=1, guild_id=1, host_id=100)
    for i in range(n):
        g.add_player(100 + i, f"J{i}")
    g.start(now=0, rng=random.Random(seed))
    return g


def by_role(g, role):
    return [p for p in g.players.values() if p.role == role]


def test_roles_and_traits():
    g = make_game(5)
    assert len(by_role(g, MURDERER)) == 1
    assert len(by_role(g, DETECTIVE)) == 1
    assert len(by_role(g, DOCTOR)) == 1
    assert len(by_role(g, CIVILIAN)) == 2
    m = g.murderer()
    for k in TRAITS:  # minden nyom legalább egy ártatlanra is illik
        assert any(p.traits[k] == m.traits[k] for p in g.players.values() if p is not m)
    assert g.phase == "night" and g.round == 1


def test_four_players_no_doctor_and_min_players():
    assert not by_role(make_game(4), DOCTOR)
    g = Game(channel_id=1, guild_id=1, host_id=1)
    g.add_player(1, "a")
    with pytest.raises(GameError):
        g.start(0)


def test_kill_clue_and_day():
    g = make_game(5)
    m = g.murderer()
    victim = by_role(g, CIVILIAN)[0]
    g.act(m.id, victim.id)
    kind, res = g.advance(100, random.Random(2))
    assert kind == "night" and res.victim is victim and not victim.alive
    assert res.clue and len(g.revealed) == 1
    assert g.phase == "day"


def test_doctor_saves():
    g = make_game(5)
    m, doc = g.murderer(), by_role(g, DOCTOR)[0]
    victim = by_role(g, CIVILIAN)[0]
    g.act(m.id, victim.id)
    g.act(doc.id, victim.id)
    _, res = g.advance(100, random.Random(2))
    assert res.victim is None and res.saved is victim and victim.alive


def test_detective_finds_murderer_once_per_night():
    g = make_game(5)
    det, m = by_role(g, DETECTIVE)[0], g.murderer()
    assert "GYILKOS" in g.act(det.id, m.id)
    with pytest.raises(GameError):
        g.act(det.id, m.id)


def test_vote_out_murderer_town_wins():
    g = make_game(5)
    g.advance(100, random.Random(3))  # random kill, mert a gyilkos nem választott
    m = g.murderer()
    for p in g.alive_players():
        g.vote(p.id, m.id if p is not m else None)
    kind, res = g.advance(200)
    assert res.eliminated is m and g.winner == TOWN_WIN and g.phase == "ended"


def test_tie_means_no_execution():
    g = make_game(4)
    g.advance(100, random.Random(3))
    alive = g.alive_players()
    g.vote(alive[0].id, alive[1].id)
    g.vote(alive[1].id, alive[0].id)
    _, res = g.advance(200)
    assert res.tie and res.eliminated is None and g.phase == "night" and g.round == 2


def test_murderer_wins_when_one_innocent_left():
    g = make_game(4)
    rng = random.Random(5)
    while g.phase != "ended":
        if g.phase == "night":
            g.advance(0, rng)
        else:
            g.advance(0)  # senki nem szavaz
    assert g.winner == MURDERER_WIN


def test_whisper_only_murderer_once():
    g = make_game(5)
    civ = by_role(g, CIVILIAN)[0]
    with pytest.raises(GameError):
        g.whisper(civ.id)
    g.whisper(g.murderer().id)
    with pytest.raises(GameError):
        g.whisper(g.murderer().id)


def test_dead_cannot_act_or_vote():
    g = make_game(5)
    m = g.murderer()
    victim = by_role(g, DETECTIVE)[0]
    g.act(m.id, victim.id)
    g.advance(0, random.Random(1))
    with pytest.raises(GameError):
        g.vote(victim.id, m.id)


def test_roundtrip_serialization():
    g = make_game(6)
    g2 = Game.from_dict(g.to_dict())
    assert g2.to_dict() == g.to_dict()
    assert g2.murderer().id == g.murderer().id
