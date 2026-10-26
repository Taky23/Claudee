"""
Discord szerver automata beállító
=================================
Ez a szkript egyszer lefuttatva felépíti a teljes szervert: rangokat,
kategóriákat, csatornákat a helyes jogosultságokkal, és kiírja a szabályzatot.

Újra lefuttatható: amit már létrehozott (azonos néven), azt nem hozza létre
újra, úgyhogy nem lesznek duplikált csatornák/rangok.

Használat: lásd a README.md fájlt ugyanebben a mappában.
"""

import os
import asyncio

import discord

# ---------------------------------------------------------------------------
#  BEÁLLÍTÁSOK – ezt a részt nyugodtan átírhatod
# ---------------------------------------------------------------------------

# A szerver neve (csak akkor használja, ha nincs TOKEN-hez kötött szerver kiválasztva).
# A GUILD_ID-t a .env fájlban add meg (jobb klikk a szerver nevére -> Azonosító másolása;
# ehhez a Discordban a Fejlesztői mód bekapcsolása kell).

# Rangok fentről lefelé. "color": hex szín, "perms": jogosultság-kulcsok.
# Elérhető perms-kulcsok lejjebb, a ROLE_PERMS szótárban.
ROLES = [
    {"name": "👑 Admin",      "color": 0xE74C3C, "perms": "admin",     "hoist": True},
    {"name": "🛡️ Moderátor",  "color": 0x3498DB, "perms": "moderator", "hoist": True},
    {"name": "🤖 Bot",        "color": 0x95A5A6, "perms": "bot",       "hoist": True},
    {"name": "⭐ Tag",         "color": 0x2ECC71, "perms": "member",    "hoist": True},
]

# Kategóriák és a bennük lévő csatornák.
#   type:      "text" vagy "voice"
#   visibility: "all" (mindenki), "read_only" (mindenki olvassa, csak mod/admin ír),
#               "staff" (csak Moderátor + Admin látja)
STRUCTURE = [
    {
        "category": "📋 INFORMÁCIÓ",
        "visibility": "all",
        "channels": [
            {"name": "📢・bejelentések", "type": "text", "visibility": "read_only",
             "topic": "Fontos hírek és bejelentések."},
            {"name": "📜・szabályzat",   "type": "text", "visibility": "read_only",
             "topic": "A szerver szabályai. Olvasd el, mielőtt írsz!"},
            {"name": "👋・üdvözlés",      "type": "text", "visibility": "read_only",
             "topic": "Itt köszöntjük az új tagokat."},
            {"name": "🎭・rang-választó",  "type": "text", "visibility": "read_only",
             "topic": "Válassz rangokat reakciókkal."},
        ],
    },
    {
        "category": "💬 KÖZÖSSÉG",
        "visibility": "all",
        "channels": [
            {"name": "💬・általános",     "type": "text", "visibility": "all",
             "topic": "Kötetlen beszélgetés."},
            {"name": "🎲・játék",         "type": "text", "visibility": "all",
             "topic": "Játékokról minden."},
            {"name": "🖼️・képek-média",   "type": "text", "visibility": "all",
             "topic": "Képek, videók, mémek."},
            {"name": "🤖・bot-parancsok",  "type": "text", "visibility": "all",
             "topic": "Itt használd a botok parancsait."},
        ],
    },
    {
        "category": "🔊 HANGCSATORNÁK",
        "visibility": "all",
        "channels": [
            {"name": "🔊 Általános", "type": "voice", "visibility": "all"},
            {"name": "🎮 Gaming",    "type": "voice", "visibility": "all"},
            {"name": "🎵 Zene",      "type": "voice", "visibility": "all"},
            {"name": "💤 AFK",       "type": "voice", "visibility": "all"},
        ],
    },
    {
        "category": "🛠️ STÁB",
        "visibility": "staff",
        "channels": [
            {"name": "🛠️・mod-chat", "type": "text", "visibility": "staff",
             "topic": "Csak a stábnak."},
            {"name": "📋・napló",     "type": "text", "visibility": "staff",
             "topic": "Moderációs napló."},
        ],
    },
]

# A #szabályzat csatornába kiírt szöveg.
RULES_TITLE = "📜 Szerver szabályzat"
RULES = [
    ("1. Légy kedves", "Tiszteld a többieket. Sértegetés, zaklatás, gyűlölködés tilos."),
    ("2. Semmi spam", "Ne áraszd el a csatornákat ismételt üzenettel vagy reklámmal."),
    ("3. Jó helyre írj", "Használd a témának megfelelő csatornát."),
    ("4. Nincs NSFW / illegális tartalom", "Pornó, erőszak, illegális dolgok tiltva."),
    ("5. Védd a magánéletet", "Ne ossz meg másokról adatot vagy felvételt az engedélyük nélkül."),
    ("6. A stáb szava dönt", "A moderátorok döntését tartsd tiszteletben. Kérdés esetén írj priviben."),
]
WELCOME_MESSAGE = (
    "👋 **Üdv a szerveren!**\n\n"
    "Örülünk, hogy itt vagy! Mielőtt elkezdenéd:\n"
    "• Olvasd el a 📜・szabályzat csatornát.\n"
    "• A 🎭・rang-választóban választhatsz magadnak rangokat.\n"
    "• Mutatkozz be a 💬・általános csatornában!\n\n"
    "Jó szórakozást! 🎉"
)

# ---------------------------------------------------------------------------
#  Innentől a motorháztető – ehhez nem kell hozzányúlni
# ---------------------------------------------------------------------------

def _perm(**kwargs):
    p = discord.Permissions.none()
    p.update(**kwargs)
    return p

# Jogosultság-csomagok a rangokhoz.
ROLE_PERMS = {
    "admin": _perm(administrator=True),
    "moderator": _perm(
        kick_members=True, ban_members=True, manage_messages=True,
        manage_nicknames=True, mute_members=True, deafen_members=True,
        move_members=True, manage_threads=True, moderate_members=True,
        view_audit_log=True, read_messages=True, send_messages=True,
        connect=True, speak=True, read_message_history=True,
    ),
    "bot": _perm(
        read_messages=True, send_messages=True, embed_links=True,
        attach_files=True, manage_messages=True, read_message_history=True,
        add_reactions=True, connect=True, speak=True,
    ),
    "member": _perm(
        read_messages=True, send_messages=True, embed_links=True,
        attach_files=True, read_message_history=True, add_reactions=True,
        connect=True, speak=True, stream=True, use_voice_activation=True,
        create_instant_invite=True, change_nickname=True,
    ),
}


class SetupBot(discord.Client):
    def __init__(self, guild_id):
        super().__init__(intents=discord.Intents.default())
        self.guild_id = guild_id

    async def on_ready(self):
        print(f"Bejelentkezve mint: {self.user}")
        try:
            guild = self._resolve_guild()
            if guild is None:
                return
            print(f"\nSzerver: {guild.name}\n{'='*40}")
            roles = await self._ensure_roles(guild)
            await self._ensure_structure(guild, roles)
            await self._write_rules_and_welcome(guild)
            print(f"\n{'='*40}\n✅ Kész! A szerver fel van építve.")
        except discord.Forbidden:
            print("\n❌ HIBA: a botnak nincs elég joga. Győződj meg róla, hogy a bot "
                  "rangja a lista tetején van, és megadtad neki az Administrator jogot "
                  "meghíváskor.")
        except Exception as e:  # noqa: BLE001
            print(f"\n❌ Váratlan hiba: {e!r}")
        finally:
            await self.close()

    def _resolve_guild(self):
        if self.guild_id:
            g = self.get_guild(self.guild_id)
            if g is None:
                print(f"❌ Nem találom a {self.guild_id} azonosítójú szervert. "
                      "A bot tényleg rajta van? Jó a GUILD_ID?")
            return g
        if len(self.guilds) == 1:
            return self.guilds[0]
        print("❌ A bot több szerveren is van. Add meg a GUILD_ID-t a .env fájlban. "
              f"Elérhető szerverek: {[(g.name, g.id) for g in self.guilds]}")
        return None

    async def _ensure_roles(self, guild):
        existing = {r.name: r for r in guild.roles}
        result = {}
        # Fentről lefelé hozzuk létre, hogy a rangsorrend stimmeljen.
        for spec in ROLES:
            role = existing.get(spec["name"])
            if role is None:
                role = await guild.create_role(
                    name=spec["name"],
                    colour=discord.Colour(spec["color"]),
                    permissions=ROLE_PERMS[spec["perms"]],
                    hoist=spec.get("hoist", False),
                    mentionable=True,
                    reason="Automata szerver-beállítás",
                )
                print(f"  ➕ Rang létrehozva: {spec['name']}")
            else:
                print(f"  ✔️  Rang már létezik: {spec['name']}")
            result[spec["perms"]] = role
        return result

    def _overwrites(self, guild, visibility, roles):
        everyone = guild.default_role
        mod, admin = roles.get("moderator"), roles.get("admin")
        if visibility == "all":
            return {}
        if visibility == "read_only":
            ow = {everyone: discord.PermissionOverwrite(
                read_messages=True, send_messages=False, add_reactions=False)}
            for r in (mod, admin):
                if r:
                    ow[r] = discord.PermissionOverwrite(send_messages=True, add_reactions=True)
            return ow
        if visibility == "staff":
            ow = {everyone: discord.PermissionOverwrite(read_messages=False)}
            for r in (mod, admin):
                if r:
                    ow[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            return ow
        return {}

    async def _ensure_structure(self, guild, roles):
        for block in STRUCTURE:
            cat = discord.utils.get(guild.categories, name=block["category"])
            if cat is None:
                cat = await guild.create_category(
                    block["category"],
                    overwrites=self._overwrites(guild, block["visibility"], roles),
                    reason="Automata szerver-beállítás",
                )
                print(f"\n📂 Kategória létrehozva: {block['category']}")
            else:
                print(f"\n📂 Kategória már létezik: {block['category']}")

            for ch in block["channels"]:
                exists = discord.utils.get(cat.channels, name=_norm(ch["name"]))
                if exists is not None:
                    print(f"   ✔️  Csatorna már létezik: {ch['name']}")
                    continue
                ow = self._overwrites(guild, ch.get("visibility", "all"), roles)
                if ch["type"] == "voice":
                    await guild.create_voice_channel(
                        ch["name"], category=cat, overwrites=ow,
                        reason="Automata szerver-beállítás")
                else:
                    await guild.create_text_channel(
                        ch["name"], category=cat, overwrites=ow,
                        topic=ch.get("topic"), reason="Automata szerver-beállítás")
                print(f"   ➕ Csatorna létrehozva: {ch['name']}")

    async def _write_rules_and_welcome(self, guild):
        rules_ch = discord.utils.get(guild.text_channels, name=_norm("📜・szabályzat"))
        if rules_ch and not await _has_bot_message(rules_ch, self.user):
            embed = discord.Embed(title=RULES_TITLE, colour=0x5865F2)
            for name, value in RULES:
                embed.add_field(name=name, value=value, inline=False)
            embed.set_footer(text=f"{guild.name} • jó itt lenni!")
            await rules_ch.send(embed=embed)
            print("\n📜 Szabályzat kiírva.")

        welcome_ch = discord.utils.get(guild.text_channels, name=_norm("👋・üdvözlés"))
        if welcome_ch and not await _has_bot_message(welcome_ch, self.user):
            await welcome_ch.send(WELCOME_MESSAGE)
            print("👋 Üdvözlő üzenet kiírva.")


def _norm(name):
    """A Discord a csatornaneveket kisbetűsíti és a szóközt kötőjelre cseréli."""
    return name.lower().replace(" ", "-")


async def _has_bot_message(channel, me):
    try:
        async for msg in channel.history(limit=20):
            if msg.author.id == me.id:
                return True
    except discord.Forbidden:
        pass
    return False


def main():
    token = os.environ.get("DISCORD_TOKEN")
    guild_id = os.environ.get("GUILD_ID")

    # .env fájl beolvasása, ha van (külső csomag nélkül).
    if (not token) and os.path.exists(os.path.join(os.path.dirname(__file__), ".env")):
        for line in open(os.path.join(os.path.dirname(__file__), ".env"), encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
        token = os.environ.get("DISCORD_TOKEN")
        guild_id = os.environ.get("GUILD_ID")

    if not token:
        raise SystemExit(
            "Nincs DISCORD_TOKEN. Hozz létre egy .env fájlt a .env.example alapján, "
            "és írd bele a bot tokenjét.")

    bot = SetupBot(int(guild_id) if guild_id else None)
    bot.run(token)


if __name__ == "__main__":
    main()
