"""Időpontok és dátumok értelmezése (Discordtól független, tesztelhető)."""
from __future__ import annotations

import random
import re
import unicodedata
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Budapest")
MAX_AHEAD = timedelta(days=30)

WEEKDAYS = ["hetfo", "kedd", "szerda", "csutortok", "pentek", "szombat", "vasarnap"]
HELP = (
    "Példák: `20:00`, `21.30`, `holnap 20:00`, `szombat 19:00`, `11.02 20:00`, "
    "`2026-11-02 20:00`, `30 perc`, `1 óra`, `most`"
)


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.strip().lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def parse_time(text: str, now: datetime) -> datetime:
    """Szövegből jövőbeli időpont (Budapest idő szerint). Hibás bemenetre ValueError."""
    s = re.sub(r"\s+", " ", _plain(text))
    now = now.astimezone(TZ)
    if s == "most":
        return now

    m = re.fullmatch(r"(\d+) ?(perc|p|ora|h)( mulva)?", s)
    if m:
        n = int(m[1])
        delta = timedelta(minutes=n) if m[2] in ("perc", "p") else timedelta(hours=n)
        if not timedelta(0) < delta <= MAX_AHEAD:
            raise ValueError("Ez túl messze van (legfeljebb 30 nap).")
        return now + delta

    m = re.fullmatch(r"(?:(.+) )?(\d{1,2})(?:[:.](\d{2}))?", s)
    if not m:
        raise ValueError(f"Nem értem ezt az időpontot. {HELP}")
    day_part, hour, minute = m[1], int(m[2]), int(m[3] or 0)
    if hour > 23 or minute > 59:
        raise ValueError(f"Nincs ilyen óra: {hour}:{minute:02d}.")

    today = now.date()
    explicit_day = True
    if day_part is None or day_part == "ma":
        day, explicit_day = today, day_part == "ma"
    elif day_part == "holnap":
        day = today + timedelta(days=1)
    elif day_part == "holnaputan":
        day = today + timedelta(days=2)
    elif day_part in WEEKDAYS:
        ahead = (WEEKDAYS.index(day_part) - today.weekday()) % 7
        day = today + timedelta(days=ahead)
        explicit_day = ahead != 0  # a mai napnál átfordulhat a jövő hétre
    elif dm := re.fullmatch(r"(?:(\d{4})[-.])?(\d{1,2})[-.](\d{1,2})\.?", day_part):
        try:
            day = date(int(dm[1] or today.year), int(dm[2]), int(dm[3]))
        except ValueError:
            raise ValueError("Nincs ilyen nap a naptárban.") from None
        if dm[1] is None and day < today:
            day = day.replace(year=today.year + 1)
    else:
        raise ValueError(f"Nem értem ezt a napot: „{day_part}”. {HELP}")

    when = datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ)
    if when <= now and not explicit_day:
        # „20:00” vagy „szombat 20:00”, ami már elmúlt: a következő alkalom.
        when += timedelta(days=7 if day_part in WEEKDAYS else 1)
    if when <= now:
        raise ValueError("Ez az időpont már elmúlt.")
    if when - now > MAX_AHEAD:
        raise ValueError("Ez túl messze van (legfeljebb 30 nap).")
    return when


def parse_birthday(text: str) -> tuple[int, int]:
    """„03-15”, „3.15.”, „03/15” → (hónap, nap)."""
    m = re.fullmatch(r"(\d{1,2})[-./](\d{1,2})\.?", text.strip())
    if not m:
        raise ValueError("Hónap és nap kell, pl. `03-15` vagy `3.15.`")
    month, day = int(m[1]), int(m[2])
    try:
        date(2000, month, day)  # szökőév, így a február 29. is érvényes
    except ValueError:
        raise ValueError("Nincs ilyen nap a naptárban.") from None
    return month, day


def is_birthday(month: int, day: int, today: date) -> bool:
    if (month, day) == (2, 29) and not _leap(today.year):
        return (today.month, today.day) == (2, 28)
    return (today.month, today.day) == (month, day)


def _leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def split_teams(people: list, n: int, rng: random.Random | None = None) -> list[list]:
    """Véletlen, a lehető legegyenlőbb csapatok."""
    people = list(people)
    (rng or random).shuffle(people)
    return [people[i::n] for i in range(n)]
