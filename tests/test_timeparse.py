import pytest

from core.timeparse import DAY, HOUR, parse_when

NOW = 1_800_000_000.0


@pytest.mark.parametrize(
    "text,delta",
    [
        ("30 perc", 30 * 60),
        ("2 óra", 2 * HOUR),
        ("2h", 2 * HOUR),
        ("3 nap", 3 * DAY),
        ("2 hét", 14 * DAY),
        ("6 hónap", 180 * DAY),
        ("1 év", 365 * DAY),
        ("1év 2hónap", 425 * DAY),
        ("1 nap, 2 óra", DAY + 2 * HOUR),
    ],
)
def test_durations(text, delta):
    assert parse_when(text, NOW) == NOW + delta


def test_date():
    ts = parse_when("2027-06-01 18:30", NOW)
    assert ts > NOW
    assert parse_when("2027.06.01", NOW) < ts


@pytest.mark.parametrize("bad", ["holnap", "5", "3 macska", "0 perc", "20 év", "2020-01-01", "2027-02-30"])
def test_invalid(bad):
    with pytest.raises(ValueError):
        parse_when(bad, NOW)
