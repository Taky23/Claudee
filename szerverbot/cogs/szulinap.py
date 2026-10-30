"""/szulinap: a bot reggel 9-kor felköszönti a szülinaposokat."""
from __future__ import annotations

import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from szerverbot.idopont import TZ, is_birthday, parse_birthday

log = logging.getLogger("szerverbot.szulinap")

GREET_HOUR = 9
MONTHS = ["január", "február", "március", "április", "május", "június",
          "július", "augusztus", "szeptember", "október", "november", "december"]


def fmt(month: int, day: int) -> str:
    return f"{MONTHS[month - 1]} {day}."


@app_commands.guild_only()
class Szulinap(commands.GroupCog, group_name="szulinap", group_description="🎂 Szülinapok"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.loop.start()

    async def cog_unload(self) -> None:
        self.loop.cancel()

    @app_commands.command(name="beallit", description="A szülinapod megadása (év nélkül)")
    @app_commands.describe(datum="Hónap és nap, pl. 03-15 vagy 3.15.")
    async def beallit(self, interaction: discord.Interaction, datum: str) -> None:
        try:
            month, day = parse_birthday(datum)
        except ValueError as err:
            return await interaction.response.send_message(f"⚠️ {err}", ephemeral=True)
        today = datetime.now(TZ)
        # Ha ma van, és a mai köszöntés már kiment, idén már ne jöjjön újra.
        last = today.year if is_birthday(month, day, today.date()) and today.hour >= GREET_HOUR else 0
        self.bot.db.set_birthday(interaction.guild_id, interaction.user.id, month, day, last)
        await interaction.response.send_message(f"🎂 Megjegyeztem: **{fmt(month, day)}**", ephemeral=True)

    @app_commands.command(name="torol", description="A szülinapod törlése")
    async def torol(self, interaction: discord.Interaction) -> None:
        ok = self.bot.db.delete_birthday(interaction.guild_id, interaction.user.id)
        await interaction.response.send_message("🗑️ Töröltem." if ok else "Nem volt megadva szülinapod.", ephemeral=True)

    @app_commands.command(name="lista", description="A következő szülinapok")
    async def lista(self, interaction: discord.Interaction) -> None:
        today = datetime.now(TZ).date()
        rows = self.bot.db.birthdays(interaction.guild_id)
        if not rows:
            return await interaction.response.send_message("Még senki nem adta meg. `/szulinap beallit`", ephemeral=True)
        key = lambda r: ((r["month"], r["day"]) < (today.month, today.day), r["month"], r["day"])  # noqa: E731
        lines = [f"🎂 **{fmt(r['month'], r['day'])}** — <@{r['user_id']}>" for r in sorted(rows, key=key)]
        e = discord.Embed(title="🎂 Következő szülinapok", description="\n".join(lines)[:4000], color=0xF1C40F)
        await interaction.response.send_message(embed=e, allowed_mentions=discord.AllowedMentions.none())

    @tasks.loop(minutes=5)
    async def loop(self) -> None:
        now = datetime.now(TZ)
        if now.hour < GREET_HOUR:
            return
        db = self.bot.db
        for r in db.birthdays():
            if r["last_year"] == now.year or not is_birthday(r["month"], r["day"], now.date()):
                continue
            channel_id = db.settings(r["guild_id"])["birthday_channel"]
            channel = self.bot.get_channel(channel_id) if channel_id else None
            if channel is None:
                continue
            guild = channel.guild
            if guild.get_member(r["user_id"]) is None:
                continue  # már nincs a szerveren
            try:
                await channel.send(f"🎂🎉 Boldog szülinapot, <@{r['user_id']}>! Ma te vagy a raid főnöke! 🥳")
                db.mark_birthday(r["guild_id"], r["user_id"], now.year)
            except discord.HTTPException:
                log.warning("Nem tudtam felköszönteni (%s).", r["user_id"])

    @loop.before_loop
    async def _wait(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Szulinap(bot))
