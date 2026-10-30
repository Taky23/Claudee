"""Kilépők: 💀 Missing in Action [MIA]."""
from __future__ import annotations

import logging

import discord
from discord.ext import commands

log = logging.getLogger("szerverbot.kilepok")


class Kilepok(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        channel_id = self.bot.db.settings(member.guild.id)["leave_channel"]
        channel = member.guild.get_channel(channel_id) if channel_id else None
        if not isinstance(channel, discord.TextChannel):
            return
        name = discord.utils.escape_markdown(member.display_name)
        try:
            await channel.send(f"💀 **{name}** — Missing in Action [MIA]", allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            log.warning("Nem tudtam írni a kilépők szobájába (%s).", channel_id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Kilepok(bot))
