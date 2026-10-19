"""Rejtély bot – gyilkossági rejtély + időkapszula Discordra."""
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from core.storage import Storage

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("rejtely")


class RejtelyBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=discord.Intents.default(),
            # Senki ne tudjon a boton keresztül @everyone-t vagy rangot pingelni.
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True),
        )
        self.storage = Storage(os.getenv("DB_PATH", "data/bot.db"))

    async def setup_hook(self) -> None:
        await self.load_extension("cogs.mystery")
        await self.load_extension("cogs.capsule")

        guild_id = os.getenv("GUILD_ID")
        if guild_id:
            # Egy szerverre azonnal frissülnek a parancsok (fejlesztéshez ideális).
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("%d parancs szinkronizálva a(z) %s szerverre", len(synced), guild_id)
        else:
            synced = await self.tree.sync()
            log.info("%d globális parancs szinkronizálva", len(synced))

    async def on_ready(self) -> None:
        log.info("Bejelentkezve: %s (%s)", self.user, self.user.id)
        await self.change_presence(activity=discord.Game(name="🔪 /rejtely uj"))


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Hiányzik a DISCORD_TOKEN! Másold le a .env.example fájlt .env néven, és írd bele a tokent.")
    RejtelyBot().run(token, log_handler=None)


if __name__ == "__main__":
    main()
