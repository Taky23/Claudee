"""/raid: közös játék vagy watch party szervezése jelentkező gombokkal, emlékeztetővel."""
from __future__ import annotations

import logging
import time
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks

from szerverbot.idopont import HELP, TZ, parse_time

log = logging.getLogger("szerverbot.raid")

REMIND_BEFORE = 15 * 60
# kulcs: (cím, pingelt rang, alap létszám, szín)
GAMES = {
    "tarkov": ("🎯 Tarkov raid", "🎯 Tarkov", 5, 0x6B8E23),
    "dayz": ("🧟 DayZ túlélés", "🧟 DayZ", None, 0xA93226),
    "anime": ("🌸 Anime watch party", "🌸 Anime", None, 0xFF69B4),
    "egyeb": ("🎲 Közös játék", "🎲 Egyéb játékok", None, 0x1ABC9C),
}
STATUS_LABEL = {"jovok": "✅ Jönnek", "talan": "🤔 Talán", "nem": "❌ Nem jönnek"}


def t(ts: float, style: str = "R") -> str:
    return f"<t:{int(ts)}:{style}>"


def mentions(ids: list[int]) -> str:
    return ", ".join(f"<@{i}>" for i in ids) or "—"


def event_embed(ev, rsvps: dict[str, list[int]]) -> discord.Embed:
    title, _, _, color = GAMES[ev["game"]]
    if ev["cancelled"]:
        title += " — ❌ ELMARAD"
    elif ev["started"]:
        title += " — 🚀 ELINDULT"
    desc = f"👤 Szervező: <@{ev['creator_id']}>" + (f"\n\n{ev['note']}" if ev["note"] else "")
    e = discord.Embed(title=title, description=desc, color=color)
    e.add_field(name="🕒 Mikor", value=f"{t(ev['start_at'], 'F')}\n{t(ev['start_at'])}", inline=False)
    for status, label in STATUS_LABEL.items():
        ids = rsvps[status]
        count = f"{len(ids)}/{ev['max_players']}" if status == "jovok" and ev["max_players"] else str(len(ids))
        e.add_field(name=f"{label} ({count})", value=mentions(ids)[:1024], inline=False)
    e.set_footer(text=f"#{ev['id']} · 15 perccel előtte és induláskor szólok a jelentkezőknek")
    return e


class RaidView(discord.ui.View):
    def __init__(self, cog: "Raid") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Jövök", emoji="✅", style=discord.ButtonStyle.success, custom_id="raid:jovok")
    async def jovok(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.cog.answer(interaction, "jovok")

    @discord.ui.button(label="Talán", emoji="🤔", style=discord.ButtonStyle.secondary, custom_id="raid:talan")
    async def talan(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.cog.answer(interaction, "talan")

    @discord.ui.button(label="Nem jövök", emoji="❌", style=discord.ButtonStyle.secondary, custom_id="raid:nem")
    async def nem(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.cog.answer(interaction, "nem")

    @discord.ui.button(label="Lemondás", emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="raid:lemond")
    async def lemond(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.cog.cancel(interaction)


class Raid(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.view = RaidView(self)

    async def cog_load(self) -> None:
        self.bot.add_view(self.view)
        self.loop.start()

    async def cog_unload(self) -> None:
        self.loop.cancel()

    @app_commands.command(name="raid", description="Közös játék vagy watch party szervezése")
    @app_commands.describe(
        jatek="Mit játszotok?",
        mikor="Pl. 20:00, holnap 20:00, szombat 19:00, 30 perc",
        leiras="Pl. Customs, quest: Delivery from the Past",
        max_fo="Hány fő jöhet (Tarkovnál alapból 5)",
        ping="Pingelje a játék rangját? (alapból igen)",
    )
    @app_commands.choices(jatek=[app_commands.Choice(name=v[0], value=k) for k, v in GAMES.items()])
    @app_commands.guild_only()
    async def raid(
        self,
        interaction: discord.Interaction,
        jatek: app_commands.Choice[str],
        mikor: str,
        leiras: app_commands.Range[str, 0, 300] = "",
        max_fo: app_commands.Range[int, 1, 50] | None = None,
        ping: bool = True,
    ) -> None:
        try:
            start = parse_time(mikor, datetime.now(TZ)).timestamp()
        except ValueError as err:
            return await interaction.response.send_message(f"⚠️ {err}", ephemeral=True)

        title, role_name, default_max, _ = GAMES[jatek.value]
        db = self.bot.db
        now = time.time()
        ev_id = db.add_event(
            interaction.guild_id, interaction.channel_id, interaction.user.id, jatek.value, leiras, start,
            max_fo or default_max, reminded=start - now <= REMIND_BEFORE,
        )
        db.set_rsvp(ev_id, interaction.user.id, "jovok", now)

        role = discord.utils.get(interaction.guild.roles, name=role_name) if ping else None
        content = f"{role.mention if role else ''} **{interaction.user.display_name}** szervez: {title}!".strip()
        await interaction.response.send_message(
            content, embed=event_embed(db.event(ev_id), db.rsvps(ev_id)), view=self.view,
            allowed_mentions=discord.AllowedMentions(roles=[role] if role else [], users=False),
        )
        msg = await interaction.original_response()
        db.set_event(ev_id, message_id=msg.id)

    async def answer(self, interaction: discord.Interaction, status: str) -> None:
        db = self.bot.db
        ev = db.event_by_message(interaction.message.id)
        if ev is None or ev["cancelled"] or ev["started"]:
            return await interaction.response.send_message("Ez az esemény már lezárult.", ephemeral=True)
        rsvps = db.rsvps(ev["id"])
        uid = interaction.user.id
        if status == "jovok" and uid not in rsvps["jovok"] and ev["max_players"] and len(rsvps["jovok"]) >= ev["max_players"]:
            return await interaction.response.send_message(
                "😬 Megtelt. Nyomj **Talán**-t, és ha valaki kiesik, szólunk.", ephemeral=True
            )
        db.set_rsvp(ev["id"], uid, status, time.time())
        await interaction.response.edit_message(embed=event_embed(ev, db.rsvps(ev["id"])))

    async def cancel(self, interaction: discord.Interaction) -> None:
        db = self.bot.db
        ev = db.event_by_message(interaction.message.id)
        if ev is None or ev["cancelled"] or ev["started"]:
            return await interaction.response.send_message("Ez az esemény már lezárult.", ephemeral=True)
        if interaction.user.id != ev["creator_id"] and not interaction.permissions.manage_messages:
            return await interaction.response.send_message("Csak a szervező mondhatja le.", ephemeral=True)
        db.set_event(ev["id"], cancelled=1)
        await interaction.response.edit_message(embed=event_embed(db.event(ev["id"]), db.rsvps(ev["id"])), view=None)
        going = [i for i in db.rsvps(ev["id"])["jovok"] if i != interaction.user.id]
        if going:
            await interaction.followup.send(f"❌ Elmarad: **{GAMES[ev['game']][0]}**. {mentions(going)}")

    # ---------- időzítő ----------
    async def _channel(self, channel_id: int):
        return self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)

    @tasks.loop(seconds=30)
    async def loop(self) -> None:
        db = self.bot.db
        now = time.time()
        for ev in db.events_to_remind(now, REMIND_BEFORE):
            db.set_event(ev["id"], reminded=1)
            going = db.rsvps(ev["id"])["jovok"]
            try:
                ch = await self._channel(ev["channel_id"])
                await ch.send(f"⏰ {t(ev['start_at'])} indul: **{GAMES[ev['game']][0]}**! Készülődés! {mentions(going)}")
            except discord.HTTPException:
                log.warning("Nem tudtam emlékeztetni (#%s).", ev["id"])
        for ev in db.events_to_start(now):
            db.set_event(ev["id"], started=1, reminded=1)
            rsvps = db.rsvps(ev["id"])
            try:
                ch = await self._channel(ev["channel_id"])
                if ev["message_id"]:
                    await ch.get_partial_message(ev["message_id"]).edit(embed=event_embed(db.event(ev["id"]), rsvps), view=None)
                await ch.send(f"🚀 Indulás: **{GAMES[ev['game']][0]}**! Mindenki a hangszobába! {mentions(rsvps['jovok'])}")
            except discord.HTTPException:
                log.warning("Nem tudtam elindítani (#%s).", ev["id"])
        db.delete_old_events(now - 7 * 86400)

    @loop.before_loop
    async def _wait(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Raid(bot))
