"""/beallit: melyik szobát használja a bot a kilépőkhöz, szülinapokhoz és az ideiglenes hangszobákhoz."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands


def ch(channel_id: int | None) -> str:
    return f"<#{channel_id}>" if channel_id else "— (nincs beállítva)"


class Beallitas(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="beallit", description="A bot beállításai (paraméter nélkül: a mostaniak)")
    @app_commands.describe(
        kilepok="Ide írja ki a kilépőket: 💀 Missing in Action [MIA]",
        szulinap="Ide köszönti fel a szülinaposokat",
        hangszoba="Aki ebbe a hangszobába belép, saját ideiglenes hangszobát kap",
        kikapcsol="Egy funkció kikapcsolása",
    )
    @app_commands.choices(kikapcsol=[
        app_commands.Choice(name="💀 Kilépők", value="leave_channel"),
        app_commands.Choice(name="🎂 Szülinapok", value="birthday_channel"),
        app_commands.Choice(name="🔊 Ideiglenes hangszobák", value="lobby_channel"),
    ])
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def beallit(
        self,
        interaction: discord.Interaction,
        kilepok: discord.TextChannel | None = None,
        szulinap: discord.TextChannel | None = None,
        hangszoba: discord.VoiceChannel | None = None,
        kikapcsol: app_commands.Choice[str] | None = None,
    ) -> None:
        db = self.bot.db
        gid = interaction.guild_id
        for key, value in (("leave_channel", kilepok), ("birthday_channel", szulinap), ("lobby_channel", hangszoba)):
            if value:
                db.set_setting(gid, key, value.id)
        if kikapcsol:
            db.set_setting(gid, kikapcsol.value, None)

        s = db.settings(gid)
        e = discord.Embed(title="⚙️ Beállítások", color=discord.Color.blurple())
        e.add_field(name="💀 Kilépők", value=ch(s["leave_channel"]), inline=False)
        e.add_field(name="🎂 Szülinapok", value=ch(s["birthday_channel"]), inline=False)
        e.add_field(name="🔊 Ideiglenes hangszoba-indító", value=ch(s["lobby_channel"]), inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Beallitas(bot))
