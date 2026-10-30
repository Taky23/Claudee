from discord_szerver.sablon import CATEGORIES, EVERYONE, ROLES

ROLE_NAMES = [r[0] for r in ROLES]


def test_unique_names():
    assert len(set(ROLE_NAMES)) == len(ROLE_NAMES)
    cats = [c["name"] for c in CATEGORIES]
    assert len(set(cats)) == len(cats)
    for cat in CATEGORIES:
        names = [ch["name"] for ch in cat["channels"]]
        assert len(set(names)) == len(names), cat["name"]


def test_overwrites_reference_known_roles():
    known = set(ROLE_NAMES) | {EVERYONE}
    for cat in CATEGORIES:
        assert set(cat.get("overwrites", {})) <= known
        for ch in cat["channels"]:
            assert set(ch.get("overwrites", {})) <= known


def test_text_channel_names_are_valid():
    # Discord a szövegszobák nevét kisbetűsíti, a szóközt kötőjelre cseréli: így újrafuttatáskor is egyezik.
    for cat in CATEGORIES:
        for ch in cat["channels"]:
            if ch["type"] == "text":
                assert ch["name"] == ch["name"].lower() and " " not in ch["name"], ch["name"]
                assert len(ch["name"]) <= 100 and len(ch["topic"]) <= 1024


def test_exactly_one_afk_and_tarkov_raids_are_five():
    afk = [ch for cat in CATEGORIES for ch in cat["channels"] if ch.get("afk")]
    assert len(afk) == 1 and afk[0]["type"] == "voice"
    raids = [ch for cat in CATEGORIES for ch in cat["channels"] if ch["name"].startswith("Tarkov Raid")]
    assert raids and all(ch["user_limit"] == 5 for ch in raids)
