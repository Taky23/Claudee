"""Sorsolás és csapatosztás a hangszobában lévők között."""
from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from szerverbot.idopont import split_teams


def voice_people(interaction: discord.Interaction) -> list[discord.Member] | None:
    voice = interaction.user.voice
    if not voice or not voice.channel:
        return None
    return [m for m in voice.channel.members if not m.bot]


class Szorakozas(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="sorsol", description="Kisorsol valakit a hangszobádból (pl. ki megy előre)")
    @app_commands.describe(mire="Pl. ki megy előre, ki hozza a lootot, ki a csali")
    @app_commands.guild_only()
    async def sorsol(self, interaction: discord.Interaction, mire: app_commands.Range[str, 0, 100] = "") -> None:
        people = voice_people(interaction)
        if not people:
            return await interaction.response.send_message("🔊 Ehhez lépj be egy hangszobába.", ephemeral=True)
        winner = random.choice(people)
        what = f" — {mire}" if mire else ""
        await interaction.response.send_message(f"🎲 A sors döntött{what}: **{winner.display_name}**! {winner.mention}")

    @app_commands.command(name="csapatok", description="Véletlen csapatokra osztja a hangszobádban lévőket")
    @app_commands.describe(szam="Hány csapat legyen")
    @app_commands.guild_only()
    async def csapatok(self, interaction: discord.Interaction, szam: app_commands.Range[int, 2, 10] = 2) -> None:
        people = voice_people(interaction)
        if not people or len(people) < szam:
            return await interaction.response.send_message(
                f"🔊 Legalább {szam} ember kell a hangszobádban.", ephemeral=True
            )
        e = discord.Embed(title="⚔️ Csapatok", color=discord.Color.orange())
        for i, team in enumerate(split_teams(people, szam), 1):
            e.add_field(name=f"{i}. csapat", value="\n".join(m.display_name for m in team), inline=True)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="fejvagyiras", description="Pénzfeldobás")
    async def fejvagyiras(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"🪙 **{random.choice(['Fej', 'Írás'])}**!")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Szorakozas(bot))
