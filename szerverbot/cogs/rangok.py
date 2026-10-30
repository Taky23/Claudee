"""/rangvalaszto: gombok, amikkel mindenki maga veheti fel vagy le a játék-rangokat."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

GAME_ROLES = ["🎯 Tarkov", "🧟 DayZ", "🌸 Anime", "🎲 Egyéb játékok"]


class RoleButton(discord.ui.DynamicItem[discord.ui.Button], template=r"rang:(?P<id>[0-9]+)"):
    def __init__(self, role_id: int, label: str | None = None) -> None:
        super().__init__(
            discord.ui.Button(label=label, style=discord.ButtonStyle.secondary, custom_id=f"rang:{role_id}")
        )
        self.role_id = role_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match):
        return cls(int(match["id"]), item.label)

    async def callback(self, interaction: discord.Interaction) -> None:
        role = interaction.guild.get_role(self.role_id)
        if role is None:
            return await interaction.response.send_message("⚠️ Ez a rang már nem létezik.", ephemeral=True)
        member = interaction.user
        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Rangválasztó")
                msg = f"➖ Levettem: **{role.name}**"
            else:
                await member.add_roles(role, reason="Rangválasztó")
                msg = f"➕ Megkaptad: **{role.name}**"
        except discord.Forbidden:
            msg = "⚠️ Nincs jogom ehhez a ranghoz. A bot rangját húzd a játék-rangok fölé (Szerverbeállítások → Szerepkörök)."
        await interaction.response.send_message(msg, ephemeral=True)


class Rangok(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(RoleButton)

    @app_commands.command(name="rangvalaszto", description="Rangválasztó gombok kiposztolása ebbe a szobába")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guild_only()
    async def rangvalaszto(self, interaction: discord.Interaction) -> None:
        roles = [r for name in GAME_ROLES if (r := discord.utils.get(interaction.guild.roles, name=name))]
        if not roles:
            return await interaction.response.send_message(
                "⚠️ Nem találom a játék-rangokat (" + ", ".join(GAME_ROLES) + ").", ephemeral=True
            )
        view = discord.ui.View(timeout=None)
        for role in roles:
            view.add_item(RoleButton(role.id, role.name))
        e = discord.Embed(
            title="🎭 Mivel játszol?",
            description="Nyomd meg a gombot, és megkapod a rangot. Még egyszer megnyomva leveszi.\n"
            "A rangokat pingeljük, ha valaki csapatot keres. 📣",
            color=discord.Color.blurple(),
        )
        await interaction.channel.send(embed=e, view=view)
        await interaction.response.send_message("✅ Kiposztoltam.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Rangok(bot))
