"""Időkapszula: üzenet a jövőnek, amit a bot a megadott időben kiposztol."""
from __future__ import annotations

import logging
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.timeparse import HELP, parse_when

log = logging.getLogger("rejtely.capsule")

GOLD = discord.Color.from_rgb(212, 160, 23)
MAX_PENDING = 25


def t(ts: float, style: str = "R") -> str:
    return f"<t:{int(ts)}:{style}>"


@app_commands.guild_only()
class Capsule(commands.GroupCog, group_name="idokapszula", group_description="📜 Üzenet a jövőnek"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.open_loop.start()

    async def cog_unload(self) -> None:
        self.open_loop.cancel()

    @app_commands.command(name="lezar", description="Üzenet lezárása egy időkapszulába – a megadott időben kinyílik")
    @app_commands.describe(
        uzenet="Amit a jövőnek üzensz (a kinyitásig senki sem látja)",
        mikor="Mikor nyíljon ki? Pl. 3 nap, 2 hét, 6 hónap, 1 év, 2027-01-01 18:00",
        csatorna="Hol nyíljon ki (alapból ez a csatorna)",
    )
    async def lezar(
        self,
        interaction: discord.Interaction,
        uzenet: app_commands.Range[str, 1, 1500],
        mikor: str,
        csatorna: discord.TextChannel | None = None,
    ) -> None:
        channel = csatorna or interaction.channel
        now = time.time()
        try:
            open_at = parse_when(mikor, now)
        except ValueError as err:
            return await interaction.response.send_message(f"⚠️ {err}", ephemeral=True)

        if not channel.permissions_for(interaction.user).send_messages:
            return await interaction.response.send_message("⚠️ Abba a csatornába nem írhatsz.", ephemeral=True)
        me = channel.guild.me
        perms = channel.permissions_for(me)
        if not (perms.send_messages and perms.embed_links):
            return await interaction.response.send_message(
                f"⚠️ Nincs jogom üzenni a(z) {channel.mention} csatornába.", ephemeral=True
            )
        storage = self.bot.storage
        if len(storage.user_capsules(interaction.guild_id, interaction.user.id)) >= MAX_PENDING:
            return await interaction.response.send_message(
                f"⚠️ Legfeljebb {MAX_PENDING} lezárt kapszulád lehet egyszerre.", ephemeral=True
            )

        cid = storage.add_capsule(
            interaction.guild_id, channel.id, interaction.user.id, interaction.user.display_name, uzenet, now, open_at
        )
        e = discord.Embed(
            title="🔒 Időkapszula lezárva",
            description=(
                f"**{interaction.user.display_name}** üzenetet küldött a jövőbe.\n\n"
                f"Kinyílik: {t(open_at, 'F')} ({t(open_at)})\nHelye: {channel.mention}"
            ),
            color=GOLD,
        )
        e.set_footer(text=f"Kapszula #{cid} · Saját kapszuláid: /idokapszula listam")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="listam", description="A még lezárt időkapszuláid (csak te látod)")
    async def listam(self, interaction: discord.Interaction) -> None:
        rows = self.bot.storage.user_capsules(interaction.guild_id, interaction.user.id)
        if not rows:
            return await interaction.response.send_message(
                "Nincs lezárt kapszulád. Készíts egyet: `/idokapszula lezar`", ephemeral=True
            )
        lines = []
        for r in rows:
            preview = r["content"].replace("\n", " ")
            preview = preview if len(preview) <= 50 else preview[:49] + "…"
            lines.append(f"**#{r['id']}** · <#{r['channel_id']}> · kinyílik {t(r['open_at'])}\n> {preview}")
        e = discord.Embed(title="📜 A lezárt kapszuláid", description="\n".join(lines)[:4000], color=GOLD)
        e.set_footer(text="Törlés: /idokapszula torol <azonosító>")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="torol", description="Egy saját, még lezárt időkapszula törlése")
    @app_commands.describe(azonosito="A kapszula száma (lásd: /idokapszula listam)")
    async def torol(self, interaction: discord.Interaction, azonosito: int) -> None:
        ok = self.bot.storage.delete_capsule(azonosito, interaction.user.id)
        msg = f"🗑️ A #{azonosito} kapszulát töröltem." if ok else "⚠️ Nincs ilyen lezárt kapszulád."
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="sugo", description="Hogyan működik az időkapszula?")
    async def sugo(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "📜 **Időkapszula** – írj üzenetet a jövőnek!\n"
            "`/idokapszula lezar` → az üzenet titokban marad, és a megadott időben a bot kiposztolja.\n"
            f"{HELP}\n"
            "Ha egy gyilkossági rejtély véget ér, a bot magától is lezár egy kapszulát, ami egy év múlva emlékeztet rá. 🔪",
            ephemeral=True,
        )

    # ---------- kinyitás ----------
    async def open_capsule(self, row) -> None:
        e = discord.Embed(title="📜 Kinyílt egy időkapszula!", description=row["content"], color=GOLD)
        e.add_field(name="Lezárta", value=row["author_name"])
        e.add_field(name="Lezárva", value=f"{t(row['created_at'], 'F')}\n({t(row['created_at'])})")
        mention = f"<@{row['author_id']}>, kinyílt az időkapszulád! ✨" if row["author_id"] else None
        only_author = discord.AllowedMentions(everyone=False, roles=False, users=True)

        try:
            ch = self.bot.get_channel(row["channel_id"]) or await self.bot.fetch_channel(row["channel_id"])
            await ch.send(content=mention, embed=e, allowed_mentions=only_author)
        except (discord.NotFound, discord.Forbidden):
            # Eltűnt a csatorna vagy nincs jogom: megpróbálom privátban elküldeni a szerzőnek.
            if row["author_id"]:
                try:
                    user = await self.bot.fetch_user(row["author_id"])
                    await user.send(content="Az időkapszulád csatornája már nem elérhető, ezért ide hoztam:", embed=e)
                except discord.HTTPException:
                    log.warning("A #%s kapszulát nem tudtam kézbesíteni.", row["id"])
        self.bot.storage.mark_opened(row["id"])

    @tasks.loop(seconds=30)
    async def open_loop(self) -> None:
        for row in self.bot.storage.due_capsules(time.time()):
            try:
                await self.open_capsule(row)
            except discord.HTTPException:
                log.exception("Átmeneti hiba a #%s kapszulánál, később újrapróbálom.", row["id"])

    @open_loop.before_loop
    async def _wait(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Capsule(bot))
