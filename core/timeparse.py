"""Időpontok értelmezése az időkapszulához: "3 nap", "1év 2hónap", "2h", "2027-01-01 18:00"."""
from __future__ import annotations

import re
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("Europe/Budapest")
except Exception:  # nincs tzdata
    TZ = timezone.utc

MIN = 60
HOUR = 3600
DAY = 86400
UNITS = {
    "p": MIN, "perc": MIN, "m": MIN, "min": MIN,
    "ó": HOUR, "o": HOUR, "óra": HOUR, "ora": HOUR, "h": HOUR,
    "n": DAY, "nap": DAY, "d": DAY,
    "hét": 7 * DAY, "het": 7 * DAY, "w": 7 * DAY,
    "hó": 30 * DAY, "ho": 30 * DAY, "hónap": 30 * DAY, "honap": 30 * DAY,
    "év": 365 * DAY, "ev": 365 * DAY, "y": 365 * DAY,
}
MIN_SECONDS = 60
MAX_SECONDS = 10 * 365 * DAY

_PART = re.compile(r"(\d+)\s*([^\d\s]+)")
_DATE = re.compile(r"^(\d{4})[-./](\d{1,2})[-./](\d{1,2})\.?(?:\s+(\d{1,2})[:.](\d{2}))?$")

HELP = "Példák: `30 perc`, `2 óra`, `3 nap`, `2 hét`, `6 hónap`, `1 év`, `1év 2hónap`, `2027-01-01 18:00`"


def parse_when(text: str, now: float) -> float:
    """Visszaadja a kinyitás időpontját (unix timestamp). Hibánál ValueError."""
    s = text.strip().lower()
    m = _DATE.match(s)
    if m:
        y, mo, d, hh, mm = m.groups()
        try:
            dt = datetime(int(y), int(mo), int(d), int(hh or 0), int(mm or 0), tzinfo=TZ)
        except ValueError:
            raise ValueError("Ilyen dátum nem létezik.")
        ts = dt.timestamp()
    else:
        parts = _PART.findall(s)
        if not parts or _PART.sub("", s).strip(" ,") != "":
            raise ValueError(f"Nem értem ezt az időt. {HELP}")
        total = 0
        for num, unit in parts:
            unit = unit.strip(" ,.")
            if unit not in UNITS:
                raise ValueError(f"Ismeretlen időegység: „{unit}”. {HELP}")
            total += int(num) * UNITS[unit]
        ts = now + total

    if ts - now < MIN_SECONDS:
        raise ValueError("Az időpontnak legalább 1 perccel a jövőben kell lennie.")
    if ts - now > MAX_SECONDS:
        raise ValueError("Legfeljebb 10 évre lehet időkapszulát lezárni.")
    return ts
