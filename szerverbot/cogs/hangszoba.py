"""Ideiglenes hangszobák: aki belép az indító szobába, saját szobát kap, ami kiürülve eltűnik."""
from __future__ import annotations

import logging

import discord
from discord.ext import commands

log = logging.getLogger("szerverbot.hangszoba")


class Hangszoba(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # Ami a bot leállása alatt kiürült, azt most takarítom el.
        for channel_id in self.bot.db.temp_voices():
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                self.bot.db.delete_temp_voice(channel_id)
            elif not channel.members:
                await self._delete(channel)

    async def _delete(self, channel: discord.VoiceChannel) -> None:
        try:
            await channel.delete(reason="Ideiglenes hangszoba kiürült")
        except discord.NotFound:
            pass
        except discord.HTTPException:
            log.warning("Nem tudtam törölni: %s", channel.id)
            return
        self.bot.db.delete_temp_voice(channel.id)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        db = self.bot.db
        if before.channel and before.channel != after.channel and db.is_temp_voice(before.channel.id):
            if not before.channel.members:
                await self._delete(before.channel)

        lobby = db.settings(member.guild.id)["lobby_channel"]
        if member.bot or not after.channel or after.channel.id != lobby:
            return
        category = after.channel.category
        overwrites = dict(category.overwrites) if category else {}
        # A tulaj átnevezheti, létszámot állíthat, és kidobhat embereket a saját szobájából.
        overwrites[member] = discord.PermissionOverwrite(
            view_channel=True, connect=True, manage_channels=True, move_members=True
        )
        try:
            channel = await member.guild.create_voice_channel(
                f"🎮 {member.display_name} szobája"[:100], category=category, overwrites=overwrites,
                reason="Ideiglenes hangszoba",
            )
        except discord.HTTPException:
            log.warning("Nem tudtam hangszobát létrehozni (%s).", member.guild.id)
            return
        db.add_temp_voice(channel.id, member.guild.id, member.id)
        try:
            await member.move_to(channel, reason="Ideiglenes hangszoba")
        except discord.HTTPException:
            await self._delete(channel)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Hangszoba(bot))
