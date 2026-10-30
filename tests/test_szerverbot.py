import random
from datetime import date, datetime

import pytest

from szerverbot.db import DB
from szerverbot.idopont import TZ, is_birthday, parse_birthday, parse_time, split_teams

# 2026-10-30 péntek, 18:00
NOW = datetime(2026, 10, 30, 18, 0, tzinfo=TZ)


def at(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=TZ)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("20:00", at(2026, 10, 30, 20)),
        ("20.30", at(2026, 10, 30, 20, 30)),
        ("21", at(2026, 10, 30, 21)),
        ("17:00", at(2026, 10, 31, 17)),  # elmúlt → holnap
        ("holnap 20:00", at(2026, 10, 31, 20)),
        ("Holnapután 9", at(2026, 11, 1, 9)),
        ("szombat 19:00", at(2026, 10, 31, 19)),
        ("csütörtök 20:00", at(2026, 11, 5, 20)),
        ("csutortok 20:00", at(2026, 11, 5, 20)),
        ("péntek 20:00", at(2026, 10, 30, 20)),
        ("péntek 10:00", at(2026, 11, 6, 10)),  # ma már elmúlt → jövő hét
        ("11.02 20:00", at(2026, 11, 2, 20)),
        ("2026-11-02 20:00", at(2026, 11, 2, 20)),
        ("30 perc", at(2026, 10, 30, 18, 30)),
        ("2 óra múlva", at(2026, 10, 30, 20)),
        ("most", NOW),
    ],
)
def test_parse_time(text, expected):
    assert parse_time(text, NOW) == expected


@pytest.mark.parametrize("bad", ["ma 10:00", "25:00", "20:61", "valamikor", "02.30 20:00", "2027-06-01 20:00", "0 perc", "31 nap"])
def test_parse_time_invalid(bad):
    with pytest.raises(ValueError):
        parse_time(bad, NOW)


def test_birthday():
    assert parse_birthday("03-15") == (3, 15)
    assert parse_birthday("3.15.") == (3, 15)
    assert parse_birthday("02/29") == (2, 29)
    for bad in ("13-01", "02-30", "márc 15"):
        with pytest.raises(ValueError):
            parse_birthday(bad)
    assert is_birthday(3, 15, date(2027, 3, 15))
    assert is_birthday(2, 29, date(2027, 2, 28))
    assert not is_birthday(2, 29, date(2028, 2, 28))
    assert is_birthday(2, 29, date(2028, 2, 29))


def test_split_teams():
    teams = split_teams(list(range(7)), 3, random.Random(1))
    assert sorted(len(t) for t in teams) == [2, 2, 3]
    assert sorted(x for t in teams for x in t) == list(range(7))


def test_db_events(tmp_path):
    db = DB(str(tmp_path / "t.db"))
    ev = db.add_event(1, 2, 3, "tarkov", "", 1000.0, 5, reminded=False)
    db.set_rsvp(ev, 3, "jovok", 1.0)
    db.set_rsvp(ev, 4, "talan", 2.0)
    db.set_rsvp(ev, 4, "jovok", 3.0)
    assert db.rsvps(ev) == {"jovok": [3, 4], "talan": [], "nem": []}
    assert [r["id"] for r in db.events_to_remind(100.0, 900)] == [ev]
    assert db.events_to_start(999.0) == []
    db.set_event(ev, reminded=1, message_id=42)
    assert db.events_to_remind(100.0, 900) == []
    assert db.event_by_message(42)["id"] == ev
    db.delete_old_events(2000.0)
    assert db.event(ev) is None and db.rsvps(ev)["jovok"] == []


def test_db_settings(tmp_path):
    db = DB(str(tmp_path / "t.db"))
    assert db.settings(1)["leave_channel"] is None
    db.set_setting(1, "leave_channel", 55)
    db.set_setting(1, "lobby_channel", 66)
    db.set_setting(1, "leave_channel", None)
    assert db.settings(1)["leave_channel"] is None and db.settings(1)["lobby_channel"] == 66
