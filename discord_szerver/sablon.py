"""A baráti (Tarkov / DayZ / anime) Discord szerver sablonja: rangok, kategóriák, szobák."""
from __future__ import annotations

EVERYONE = "@everyone"
TULAJ = "👑 Tulaj"
ADMIN = "🛡️ Admin"
MOD = "🔨 Moderátor"
NEMITOTT = "🔇 Némított"

# Fentről lefelé, ebben a sorrendben kerülnek a ranglistára.
# (név, szín, jogok, külön látszik-e a taglistán, pingelhető-e)
ROLES = [
    (TULAJ, 0xF1C40F, {"administrator": True}, True, False),
    (ADMIN, 0xE74C3C, {
        "manage_guild": True, "manage_roles": True, "manage_channels": True, "manage_messages": True,
        "manage_nicknames": True, "manage_events": True, "view_audit_log": True, "kick_members": True,
        "ban_members": True, "moderate_members": True, "mute_members": True, "deafen_members": True,
        "move_members": True, "mention_everyone": True,
    }, True, False),
    (MOD, 0xE67E22, {
        "manage_messages": True, "manage_nicknames": True, "view_audit_log": True, "kick_members": True,
        "moderate_members": True, "mute_members": True, "deafen_members": True, "move_members": True,
    }, True, False),
    ("💎 VIP", 0x9B59B6, {}, True, False),
    ("🤖 Bot", 0x95A5A6, {}, True, False),
    ("🎮 Tag", 0x3498DB, {}, True, False),
    # Választható játék-rangok: pingelhetők, ha valaki csapatot keres.
    ("🎯 Tarkov", 0x6B8E23, {}, False, True),
    ("🧟 DayZ", 0xA93226, {}, False, True),
    ("🌸 Anime", 0xFF69B4, {}, False, True),
    ("🎲 Egyéb játékok", 0x1ABC9C, {}, False, True),
    (NEMITOTT, 0x4F545C, {}, False, False),
]

# A némítottak sehol nem írhatnak és nem beszélhetnek.
MUTED = {
    "send_messages": False, "send_messages_in_threads": False, "create_public_threads": False,
    "create_private_threads": False, "add_reactions": False, "speak": False,
}
READ_ONLY = {"send_messages": False, "create_public_threads": False, "create_private_threads": False}
STAFF_ONLY = {EVERYONE: {"view_channel": False}, MOD: {"view_channel": True}, ADMIN: {"view_channel": True}}


def text(name: str, topic: str = "", **extra) -> dict:
    return {"type": "text", "name": name, "topic": topic, **extra}


def voice(name: str, user_limit: int = 0, **extra) -> dict:
    return {"type": "voice", "name": name, "user_limit": user_limit, **extra}


# Minden kategória jogai a benne lévő szobákra is érvényesek.
CATEGORIES = [
    {
        "name": "📌 INFORMÁCIÓ",
        "overwrites": {EVERYONE: READ_ONLY, ADMIN: {"send_messages": True}},
        "channels": [
            text("📢・bejelentések", "Fontos hírek a szerverről"),
            text("👋・üdvözlés", "Itt köszöntjük az új tagokat"),
            text("🚪・kilépők", "Missing in Action [MIA]"),
            text("🎭・rangok", "Válaszd ki, mivel játszol: 🎯 Tarkov · 🧟 DayZ · 🌸 Anime · 🎲 Egyéb"),
        ],
    },
    {
        "name": "💬 BESZÉLGETÉS",
        "channels": [
            text("💬・általános", "Bármiről lehet dumálni"),
            text("📸・képek-videók"),
            text("😂・mémek"),
            text("💡・ötletek", "Ötletek a szerverhez"),
            text("🤖・bot-parancsok", "Bot parancsok ide, hogy ne szemeteljük tele a többi szobát"),
        ],
    },
    {
        "name": "🎯 ESCAPE FROM TARKOV",
        "channels": [
            text("🎯・tarkov-chat"),
            text("🔍・tarkov-csapatkeresés", "Ki jön raidelni? Pingeld a @🎯 Tarkov rangot"),
            text("💰・loot-és-árak", "Mi mennyit ér, mit érdemes eladni"),
            text("📋・questek-és-tippek"),
            text("🏆・tarkov-klipek"),
            voice("Tarkov Raid 1", 5),
            voice("Tarkov Raid 2", 5),
        ],
    },
    {
        "name": "🧟 DAYZ",
        "channels": [
            text("🧟・dayz-chat"),
            text("🔍・dayz-csapatkeresés", "Ki jön? Pingeld a @🧟 DayZ rangot"),
            text("🗺️・bázis-és-térkép"),
            text("🏆・dayz-klipek"),
            voice("DayZ Csapat 1"),
            voice("DayZ Csapat 2"),
        ],
    },
    {
        "name": "🎲 EGYÉB JÁTÉKOK",
        "channels": [
            text("🎮・játék-chat"),
            text("🔍・csapatkeresés"),
            text("🏆・klipek"),
            voice("Játék 1"),
            voice("Játék 2"),
        ],
    },
    {
        "name": "🌸 ANIME",
        "channels": [
            text("🌸・anime-chat"),
            text("📺・most-nézem", "Ki mit néz éppen?"),
            text("⭐・ajánlások"),
            text("📅・szezonális-animék"),
            text("🎨・fanart-és-képek"),
            text("⚠️・spoiler", "Spoilert csak ide, ||így eltakarva||"),
            voice("Anime Watch Party"),
        ],
    },
    {
        "name": "🔊 HANGCSATORNÁK",
        "channels": [
            voice("Társalgó"),
            voice("Zene"),
            voice("💤 AFK", afk=True, overwrites={EVERYONE: {"speak": False}}),
        ],
    },
    {
        "name": "🛡️ STAFF",
        "overwrites": STAFF_ONLY,
        "channels": [
            text("🛡️・staff-chat"),
            text("📋・tag-napló", "Ki lépett be, ki lépett ki"),
            voice("Staff megbeszélő"),
        ],
    },
]

# Egy friss szerver alap szobái (angol és magyar Discordon), opcionálisan törölhetők.
DEFAULT_NAMES = {
    "general", "General", "általános", "Általános",
    "Text Channels", "Voice Channels", "Szöveges csatornák", "Hangcsatornák",
}
