"""Discord-réteg a gyilkossági rejtélyhez: /rejtely parancsok, gombok, időzítő."""
from __future__ import annotations

import logging
import random
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.mystery import (
    MIN_PLAYERS,
    MURDERER,
    ROLE_INFO,
    SKIP,
    TOWN_WIN,
    TRAIT_LABEL,
    Game,
    GameError,
)

log = logging.getLogger("rejtely.mystery")

RED = discord.Color.from_rgb(170, 20, 40)
NIGHT = discord.Color.from_rgb(40, 40, 90)
DAY = discord.Color.from_rgb(240, 180, 40)
NO_PINGS = discord.AllowedMentions.none()
YEAR = 365 * 86400


def t(ts: float, style: str = "R") -> str:
    return f"<t:{int(ts)}:{style}>"


def role_name(role: str) -> str:
    return ROLE_INFO[role][0]


def clip(text: str, limit: int = 1024) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def players_block(g: Game) -> str:
    lines = []
    for p in g.players.values():
        if p.alive:
            lines.append(f"🟢 **{p.name}** — {p.trait_line()}")
        else:
            lines.append(f"💀 ~~{p.name}~~ ({role_name(p.role)})")
    return clip("\n".join(lines) or "—")


def clues_block(g: Game) -> str:
    return clip("\n".join(f"🔎 {c}" for c in g.clues()) or "Még nincs nyom. Valaki talán túl óvatos…")


# ---------------------------------------------------------------- gombok
class LobbyView(discord.ui.View):
    def __init__(self, cog: "Mystery") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Csatlakozom", emoji="🙋", style=discord.ButtonStyle.success, custom_id="rejtely:join")
    async def join(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.cog.on_lobby(interaction, "join")

    @discord.ui.button(label="Kilépek", emoji="🚪", style=discord.ButtonStyle.secondary, custom_id="rejtely:leave")
    async def leave(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.cog.on_lobby(interaction, "leave")

    @discord.ui.button(label="Indítás", emoji="🔪", style=discord.ButtonStyle.danger, custom_id="rejtely:start")
    async def start(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.cog.on_lobby(interaction, "start")


class RoleView(discord.ui.View):
    def __init__(self, cog: "Mystery") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Szerepem", emoji="🎭", style=discord.ButtonStyle.primary, custom_id="rejtely:role")
    async def role(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.cog.show_role(interaction)


# ---------------------------------------------------------------- cog
@app_commands.guild_only()
class Mystery(commands.GroupCog, group_name="rejtely", group_description="🔪 Gyilkossági rejtély játék"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.rng = random.Random()
        self.games: dict[int, Game] = {}
        for data in bot.storage.load_games():
            g = Game.from_dict(data)
            self.games[g.channel_id] = g
        bot.add_view(LobbyView(self))
        bot.add_view(RoleView(self))

    async def cog_load(self) -> None:
        self.phase_loop.start()

    async def cog_unload(self) -> None:
        self.phase_loop.cancel()

    # ---------- segédek ----------
    def save(self, g: Game) -> None:
        self.bot.storage.save_game(g.channel_id, g.to_dict())

    def drop(self, g: Game) -> None:
        self.games.pop(g.channel_id, None)
        self.bot.storage.delete_game(g.channel_id)

    def game_here(self, interaction: discord.Interaction) -> Game:
        g = self.games.get(interaction.channel_id)
        if g is None:
            raise GameError("Ebben a csatornában nem fut játék. Indíts egyet: `/rejtely uj`")
        return g

    @staticmethod
    def is_host(g: Game, user: discord.abc.User) -> bool:
        perms = getattr(user, "guild_permissions", None)
        return user.id == g.host_id or bool(perms and perms.manage_guild)

    @staticmethod
    async def error(interaction: discord.Interaction, msg: str) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(f"⚠️ {msg}", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ {msg}", ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        err = getattr(error, "original", error)
        if isinstance(err, GameError):
            await self.error(interaction, str(err))
        else:
            log.exception("Parancshiba", exc_info=err)
            await self.error(interaction, "Hoppá, valami elromlott. Próbáld újra! 😵")

    async def channel_of(self, g: Game) -> discord.abc.Messageable | None:
        ch = self.bot.get_channel(g.channel_id)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(g.channel_id)
            except (discord.NotFound, discord.Forbidden):
                return None
        return ch

    # ---------- embedek ----------
    def lobby_embed(self, g: Game) -> discord.Embed:
        e = discord.Embed(
            title="🔪 Gyilkossági rejtély – jelentkezés",
            description=(
                "Valaki közülünk **gyilkos**. Éjjel lecsap, nappal köztetek mosolyog.\n"
                "A tetthelyeken hagyott nyomok és a ti eszetek az egyetlen fegyver.\n\n"
                f"🌙 Éjszaka: **{g.night_minutes} perc** · ☀️ Nappal: **{g.day_minutes} perc**\n"
                f"Legalább **{MIN_PLAYERS}** játékos kell. A házigazda (<@{g.host_id}>) indítja a játékot."
            ),
            color=RED,
        )
        names = "\n".join(f"• {p.name}" for p in g.players.values()) or "Még senki…"
        e.add_field(name=f"Játékosok ({len(g.players)})", value=clip(names))
        e.set_footer(text="Szabályok: /rejtely szabalyok")
        return e

    def night_embed(self, g: Game) -> discord.Embed:
        return discord.Embed(
            title=f"🌙 {g.round}. éjszaka",
            description=(
                "Leszállt az éj. A városra csend borul… de nem mindenki alszik.\n\n"
                "**Mindenki** küldje el az éjszakai akcióját: `/rejtely akcio` – a civilek is, hogy senki ne lógjon ki.\n"
                "A szerepedet a fenti **🎭 Szerepem** gombbal nézheted meg.\n\n"
                f"Napfelkelte: {t(g.deadline)}"
            ),
            color=NIGHT,
        )

    def day_embed(self, g: Game) -> discord.Embed:
        e = discord.Embed(
            title=f"☀️ {g.round}. nap",
            description=(
                "Beszéljétek meg, ki gyanús! Vessétek össze a nyomokat az ismertetőjegyekkel.\n"
                "Szavazás: `/rejtely szavaz` (célpont nélkül = senkit ne végezzünk ki).\n\n"
                f"A szavazás lezárul: {t(g.deadline)} – vagy amint mindenki szavazott."
            ),
            color=DAY,
        )
        e.add_field(name="Nyomok", value=clues_block(g), inline=False)
        e.add_field(name="Játékosok (ital · illat · tárgy)", value=players_block(g), inline=False)
        return e

    def end_embed(self, g: Game) -> discord.Embed:
        m = g.murderer()
        if g.winner == TOWN_WIN:
            title, desc = "🎉 A város győzött!", f"Lebukott a gyilkos: **{m.name}**. Az igazság diadalmaskodott."
        else:
            title, desc = "🩸 A gyilkos győzött!", f"**{m.name}** mindenkit átvert. Ügyes volt… túl ügyes."
        e = discord.Embed(title=title, description=desc, color=RED)
        roles = "\n".join(
            f"{'🟢' if p.alive else '💀'} **{p.name}** – {role_name(p.role)}" for p in g.players.values()
        )
        e.add_field(name="Szerepek", value=clip(roles), inline=False)
        e.set_footer(text="📜 Az eredmény időkapszulába került – pontosan egy év múlva előkerül ebben a csatornában.")
        return e

    # ---------- lobby gombok ----------
    async def on_lobby(self, interaction: discord.Interaction, action: str) -> None:
        g = self.games.get(interaction.channel_id)
        if g is None or g.phase != "lobby":
            return await self.error(interaction, "Ez a jelentkezés már lezárult.")
        try:
            if action == "join":
                g.add_player(interaction.user.id, interaction.user.display_name)
            elif action == "leave":
                g.remove_player(interaction.user.id)
            else:
                if not self.is_host(g, interaction.user):
                    raise GameError("Csak a házigazda indíthatja a játékot.")
                g.start(time.time(), self.rng)
        except GameError as err:
            return await self.error(interaction, str(err))
        self.save(g)

        if action != "start":
            return await interaction.response.edit_message(embed=self.lobby_embed(g))

        closed = self.lobby_embed(g)
        closed.title = "🔪 Gyilkossági rejtély – a játék elindult!"
        await interaction.response.edit_message(embed=closed, view=None)
        await interaction.channel.send(
            content=" ".join(f"<@{p.id}>" for p in g.players.values()),
            embed=discord.Embed(
                title="🎭 Kiosztottam a szerepeket!",
                description=(
                    "Nyomd meg a gombot, hogy titokban megnézd a szereped (csak te látod).\n"
                    "Mindenkinek vannak **ismertetőjegyei** (ital, illat, tárgy). Amikor valaki meghal, "
                    "a tetthelyen a gyilkos egyik ismertetőjegye marad – ebből lehet kinyomozni, ki az."
                ),
                color=RED,
            ),
            view=RoleView(self),
        )
        await interaction.channel.send(embed=self.night_embed(g))

    async def show_role(self, interaction: discord.Interaction) -> None:
        g = self.games.get(interaction.channel_id)
        p = g.get(interaction.user.id) if g else None
        if p is None:
            return await self.error(interaction, "Nem vagy játékos ebben a játékban.")
        name, desc = ROLE_INFO[p.role]
        e = discord.Embed(title=f"A szereped: {name}", description=desc, color=RED)
        e.add_field(
            name="Ismertetőjegyeid",
            value="\n".join(f"{TRAIT_LABEL[k]}: **{v}**" for k, v in p.traits.items()),
            inline=False,
        )
        if p.role == MURDERER:
            e.add_field(
                name="⚠️ Vigyázz",
                value="Minden gyilkosság után ezek közül egy nyomként előkerül. Szerencsére másoknál is előfordulnak…",
                inline=False,
            )
        if not p.alive:
            e.set_footer(text="Te már halott vagy. Kísértetként figyelheted a játékot, de ne súgj! 👻")
        await interaction.response.send_message(embed=e, ephemeral=True)

    # ---------- fázisváltás ----------
    async def advance_game(self, g: Game, expected_phase: str, expected_round: int) -> None:
        # A váltás szinkron fut, így két egyidejű hívás nem léptetheti kétszer a játékot.
        if g.phase != expected_phase or g.round != expected_round or self.games.get(g.channel_id) is not g:
            return
        kind, res = g.advance(time.time(), self.rng)
        if g.phase == "ended":
            self.drop(g)
        else:
            self.save(g)

        ch = await self.channel_of(g)
        if ch is None:
            log.warning("A %s csatorna eltűnt, a játékot törlöm.", g.channel_id)
            return self.drop(g)

        lines: list[str] = []
        if kind == "night":
            if res.victim:
                if res.random_kill:
                    lines.append("A gyilkos az éjjel nem döntött… ezért találomra csapott le.")
                lines.append(f"Reggel **{res.victim.name}** holttestére bukkantatok. 💀\nSzerepe: **{role_name(res.victim.role)}**")
            elif res.saved:
                lines.append("Az éjjel valakit megtámadtak, de az orvos időben ott volt – **ma mindenki túlélte!** 🩺")
            if res.clue:
                lines.append(f"🔎 **Új nyom:** {res.clue}")
            result = discord.Embed(title="🌅 Felkelt a nap", description="\n\n".join(lines), color=DAY)
        else:
            if res.eliminated:
                lines.append(f"A város döntött: **{res.eliminated.name}** kötélen végezte. ⚖️\nSzerepe: **{role_name(res.eliminated.role)}**")
            elif res.no_votes:
                lines.append("Senki nem szavazott – ma senkit nem végeztek ki.")
            elif res.tie:
                lines.append("Döntetlen lett a szavazás – ma senkit nem végeztek ki.")
            else:
                lines.append("A többség úgy döntött: ma senkit nem végeznek ki.")
            if res.tally:
                tally = ", ".join(
                    f"{'senki' if tid == SKIP else g.get(tid).name}: {n}"
                    for tid, n in sorted(res.tally.items(), key=lambda x: -x[1])
                )
                lines.append(f"🗳️ Szavazatok – {tally}")
            result = discord.Embed(title="🌆 Leszáll az este", description="\n\n".join(lines), color=NIGHT)

        if g.phase == "ended":
            await ch.send(embeds=[result, self.end_embed(g)], allowed_mentions=NO_PINGS)
            self.bury_in_capsule(g)
        elif g.phase == "day":
            await ch.send(embeds=[result, self.day_embed(g)], allowed_mentions=NO_PINGS)
        else:
            await ch.send(embeds=[result, self.night_embed(g)], allowed_mentions=NO_PINGS)

    def bury_in_capsule(self, g: Game) -> None:
        m = g.murderer()
        now = time.time()
        names = ", ".join(p.name for p in g.players.values())
        outcome = "végül lebukott" if g.winner == TOWN_WIN else "megúszta, és mindenkit átvert"
        text = (
            "🔪 **Egy éve ezen a napon** ért véget egy gyilkossági rejtély ebben a csatornában.\n"
            f"A gyilkos **{m.name}** volt, és {outcome}.\n"
            f"Játékosok: {names}\nEmlékszel még, kit gyanúsítottál? 👀"
        )
        self.bot.storage.add_capsule(g.guild_id, g.channel_id, None, "Rejtély bot", text, now, now + YEAR)

    @tasks.loop(seconds=15)
    async def phase_loop(self) -> None:
        now = time.time()
        for g in list(self.games.values()):
            if g.phase in ("night", "day") and g.deadline and now >= g.deadline:
                try:
                    await self.advance_game(g, g.phase, g.round)
                except Exception:
                    log.exception("Fázisváltási hiba (%s)", g.channel_id)

    @phase_loop.before_loop
    async def _wait(self) -> None:
        await self.bot.wait_until_ready()

    # ---------- parancsok ----------
    @app_commands.command(name="uj", description="Új gyilkossági rejtély indítása ebben a csatornában")
    @app_commands.describe(
        ejszaka_perc="Meddig tartson egy éjszaka (perc, alap: 10)",
        nappal_perc="Meddig tartson egy nappal (perc, alap: 20). Lassú játékhoz: 1440 = 1 nap",
    )
    async def uj(
        self,
        interaction: discord.Interaction,
        ejszaka_perc: app_commands.Range[int, 1, 1440] = 10,
        nappal_perc: app_commands.Range[int, 1, 2880] = 20,
    ) -> None:
        if interaction.channel_id in self.games:
            raise GameError("Ebben a csatornában már fut egy játék. (Leállítás: `/rejtely leallit`)")
        g = Game(
            channel_id=interaction.channel_id,
            guild_id=interaction.guild_id,
            host_id=interaction.user.id,
            night_minutes=ejszaka_perc,
            day_minutes=nappal_perc,
        )
        g.add_player(interaction.user.id, interaction.user.display_name)
        self.games[g.channel_id] = g
        await interaction.response.send_message(embed=self.lobby_embed(g), view=LobbyView(self))
        g.lobby_message_id = (await interaction.original_response()).id
        self.save(g)

    @app_commands.command(name="akcio", description="Éjszakai akció (gyilkos, detektív, orvos) – csak te látod")
    @app_commands.describe(celpont="Kire irányul az akciód")
    async def akcio(self, interaction: discord.Interaction, celpont: discord.Member) -> None:
        g = self.game_here(interaction)
        msg = g.act(interaction.user.id, celpont.id)
        self.save(g)
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="suttogas", description="Gyilkosként névtelen üzenet a sötétből (éjjelente egyszer)")
    @app_commands.describe(uzenet="Amit névtelenül a csatornába suttogsz")
    async def suttogas(self, interaction: discord.Interaction, uzenet: app_commands.Range[str, 1, 300]) -> None:
        g = self.game_here(interaction)
        g.whisper(interaction.user.id)
        self.save(g)
        await interaction.response.send_message("🩸 Elsuttogtad. Senki sem tudja, hogy te voltál.", ephemeral=True)
        await interaction.channel.send(
            embed=discord.Embed(title="🩸 Egy hang suttog a sötétből…", description=f"*{uzenet}*", color=RED),
            allowed_mentions=NO_PINGS,
        )

    @app_commands.command(name="szavaz", description="Nappali szavazás: kit végezzünk ki?")
    @app_commands.describe(celpont="Akire szavazol. Hagyd üresen, ha ma senkit nem akarsz kivégezni")
    async def szavaz(self, interaction: discord.Interaction, celpont: discord.Member | None = None) -> None:
        g = self.game_here(interaction)
        target = g.vote(interaction.user.id, celpont.id if celpont else None)
        self.save(g)
        voter = g.get(interaction.user.id).name
        text = f"🗳️ **{voter}** szavazata: **{target.name}**" if target else f"🗳️ **{voter}** ma senkit nem végezne ki."
        alive = g.alive_players()
        voted = sum(1 for p in alive if str(p.id) in g.votes)
        await interaction.response.send_message(f"{text}  ({voted}/{len(alive)})", allowed_mentions=NO_PINGS)
        if voted == len(alive):
            await self.advance_game(g, "day", g.round)

    @app_commands.command(name="allas", description="A játék állása: nyomok, játékosok, szavazatok")
    async def allas(self, interaction: discord.Interaction) -> None:
        g = self.game_here(interaction)
        if g.phase == "lobby":
            return await interaction.response.send_message(embed=self.lobby_embed(g), ephemeral=True)
        phase = f"🌙 {g.round}. éjszaka" if g.phase == "night" else f"☀️ {g.round}. nap"
        e = discord.Embed(title=f"📋 Állás – {phase}", description=f"Fázis vége: {t(g.deadline)}", color=RED)
        e.add_field(name="Nyomok", value=clues_block(g), inline=False)
        e.add_field(name="Játékosok (ital · illat · tárgy)", value=players_block(g), inline=False)
        if g.phase == "day" and g.votes:
            votes = "\n".join(
                f"{g.get(int(v)).name} → {'senki' if tid == SKIP else g.get(tid).name}" for v, tid in g.votes.items()
            )
            e.add_field(name="Szavazatok", value=clip(votes), inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="tovabb", description="(Házigazda) Az aktuális fázis azonnali lezárása")
    async def tovabb(self, interaction: discord.Interaction) -> None:
        g = self.game_here(interaction)
        if not self.is_host(g, interaction.user):
            raise GameError("Ezt csak a házigazda vagy egy szerverkezelő teheti meg.")
        if g.phase not in ("night", "day"):
            raise GameError("Most nincs mit lezárni – a játék még nem indult el.")
        await interaction.response.send_message("⏩ Lezárom a fázist…", ephemeral=True)
        await self.advance_game(g, g.phase, g.round)

    @app_commands.command(name="leallit", description="(Házigazda) A játék leállítása és a szerepek felfedése")
    async def leallit(self, interaction: discord.Interaction) -> None:
        g = self.game_here(interaction)
        if not self.is_host(g, interaction.user):
            raise GameError("Ezt csak a házigazda vagy egy szerverkezelő teheti meg.")
        self.drop(g)
        e = discord.Embed(title="🛑 A játékot leállították", color=RED)
        if g.phase != "lobby":
            roles = "\n".join(f"**{p.name}** – {role_name(p.role)}" for p in g.players.values())
            e.add_field(name="A szerepek ezek voltak", value=clip(roles))
        await interaction.response.send_message(embed=e, allowed_mentions=NO_PINGS)

    @app_commands.command(name="szabalyok", description="Hogyan működik a gyilkossági rejtély?")
    async def szabalyok(self, interaction: discord.Interaction) -> None:
        e = discord.Embed(title="📖 Gyilkossági rejtély – szabályok", color=RED)
        e.add_field(
            name="Szerepek",
            value="\n".join(f"**{n}** – {d}" for n, d in (ROLE_INFO[r] for r in ROLE_INFO)),
            inline=False,
        )
        e.add_field(
            name="Menet",
            value=(
                "🌙 **Éjjel** a különleges szerepek titokban cselekszenek (`/rejtely akcio`).\n"
                "☀️ **Nappal** kiderül, ki halt meg, és előkerül egy **nyom** a gyilkos egyik ismertetőjegyéről. "
                "Ezután vita és szavazás (`/rejtely szavaz`) – akire a legtöbben szavaznak, kiesik. Döntetlennél senki.\n"
                "🧩 Mindenkinek három ismertetőjegye van (ital, illat, tárgy). Egy nyom sosem elég – "
                "mindegyik legalább még egy ártatlanra is illik. A nyomokat együtt kell összerakni!"
            ),
            inline=False,
        )
        e.add_field(
            name="Győzelem",
            value="A **város** nyer, ha kivégzi a gyilkost. A **gyilkos** nyer, ha már csak egy ártatlan marad életben.",
            inline=False,
        )
        await interaction.response.send_message(embed=e, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Mystery(bot))
