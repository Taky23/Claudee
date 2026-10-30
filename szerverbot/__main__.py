"""Szerverbot – a baráti Tarkov / DayZ / anime szerver saját botja.

Indítás: python -m szerverbot
"""
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from szerverbot.db import DB

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("szerverbot")

COGS = ["beallitas", "raid", "rangok", "hangszoba", "kilepok", "szulinap", "szorakozas"]


class Szerverbot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True  # a kilépők észleléséhez (Developer Portal: Server Members Intent)
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True),
        )
        self.db = DB(os.getenv("SZERVERBOT_DB", "data/szerverbot.db"))

    async def setup_hook(self) -> None:
        for name in COGS:
            await self.load_extension(f"szerverbot.cogs.{name}")
        guild_id = os.getenv("GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
        else:
            synced = await self.tree.sync()
        log.info("%d parancs szinkronizálva", len(synced))

    async def on_ready(self) -> None:
        log.info("Bejelentkezve: %s (%s)", self.user, self.user.id)
        await self.change_presence(activity=discord.Game(name="📅 /raid"))


def main() -> None:
    token = os.getenv("SZERVERBOT_TOKEN")
    if not token:
        raise SystemExit("Hiányzik a SZERVERBOT_TOKEN! Írd bele a .env fájlba (lásd: szerverbot/README.md).")
    Szerverbot().run(token, log_handler=None)


if __name__ == "__main__":
    main()
