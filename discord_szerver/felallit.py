"""Egyszer lefutó script: felállítja a sablon szerinti rangokat és szobákat egy Discord szerveren.

Használat: DISCORD_SETUP_TOKEN=... GUILD_ID=... python -m discord_szerver.felallit
Újrafuttatható: ami már megvan (név alapján), azt nem hozza létre újra és nem írja át.
"""
from __future__ import annotations

import asyncio
import os
import sys

import discord

from discord_szerver.sablon import CATEGORIES, DEFAULT_NAMES, EVERYONE, MUTED, NEMITOTT, ROLES, TULAJ


def overwrites_for(spec: dict[str, dict], roles: dict[str, discord.Role]) -> dict:
    return {roles[name]: discord.PermissionOverwrite(**perms) for name, perms in spec.items()}


async def setup_roles(guild: discord.Guild) -> dict[str, discord.Role]:
    existing = {r.name: r for r in guild.roles}
    roles = {EVERYONE: guild.default_role}
    for name, color, perms, hoist, mentionable in ROLES:
        if name in existing:
            print(f"  = {name} (már megvan)")
            roles[name] = existing[name]
            continue
        # Az új rang mindig a lista aljára kerül, így fentről lefelé haladva jó lesz a sorrend.
        roles[name] = await guild.create_role(
            name=name, colour=discord.Colour(color), permissions=discord.Permissions(**perms),
            hoist=hoist, mentionable=mentionable, reason="Szerver felállítása",
        )
        print(f"  + {name}")

    # Az @everyone-t csak az Admin pingelheti.
    base = guild.default_role.permissions
    base.update(mention_everyone=False)
    await guild.default_role.edit(permissions=base, reason="Szerver felállítása")
    return roles


async def setup_channels(guild: discord.Guild, roles: dict[str, discord.Role]) -> discord.VoiceChannel | None:
    channels = await guild.fetch_channels()
    categories = {c.name: c for c in channels if isinstance(c, discord.CategoryChannel)}
    afk = None
    for cat_spec in CATEGORIES:
        cat_ow = {**cat_spec.get("overwrites", {}), NEMITOTT: MUTED}
        category = categories.get(cat_spec["name"])
        if category:
            print(f"  = {cat_spec['name']} (már megvan)")
        else:
            category = await guild.create_category(
                cat_spec["name"], overwrites=overwrites_for(cat_ow, roles), reason="Szerver felállítása"
            )
            print(f"  + {cat_spec['name']}")
        present = {c.name for c in channels if c.category_id == category.id}

        for ch in cat_spec["channels"]:
            if ch["name"] in present:
                print(f"      = {ch['name']} (már megvan)")
                if ch.get("afk"):
                    afk = next(c for c in channels if c.category_id == category.id and c.name == ch["name"])
                continue
            ow = overwrites_for({**cat_ow, **ch.get("overwrites", {})}, roles)
            if ch["type"] == "text":
                created = await guild.create_text_channel(
                    ch["name"], category=category, topic=ch["topic"] or None, overwrites=ow, reason="Szerver felállítása"
                )
            else:
                created = await guild.create_voice_channel(
                    ch["name"], category=category, user_limit=ch["user_limit"], overwrites=ow,
                    reason="Szerver felállítása",
                )
            if ch.get("afk"):
                afk = created
            print(f"      + {ch['name']}")
    return afk


async def delete_defaults(guild: discord.Guild) -> None:
    channels = await guild.fetch_channels()
    # Előbb a szobák, utána az (addigra üres) kategóriák.
    for ch in sorted(channels, key=lambda c: isinstance(c, discord.CategoryChannel)):
        if ch.name in DEFAULT_NAMES:
            try:
                await ch.delete(reason="Szerver felállítása: alap szobák törlése")
                print(f"  - {ch.name}")
            except discord.HTTPException as err:
                # Pl. közösségi szerveren a szabály- vagy frissítés-szoba nem törölhető.
                print(f"  ! {ch.name} nem törölhető: {err.text}")


async def main() -> None:
    token = os.getenv("DISCORD_SETUP_TOKEN", "").strip()
    guild_id = os.getenv("GUILD_ID", "").strip()
    if not token or not guild_id.isdigit():
        sys.exit("Hiányzik a DISCORD_SETUP_TOKEN vagy a GUILD_ID (a szerver azonosítója, csak számjegyek).")

    client = discord.Client(intents=discord.Intents.none())
    try:
        await client.login(token)
    except discord.LoginFailure:
        sys.exit("Hibás bot token. Másold ki újra a Developer Portalon (Bot → Reset Token).")
    try:
        try:
            guild = await client.fetch_guild(int(guild_id))
        except (discord.NotFound, discord.Forbidden):
            sys.exit("A bot nincs a megadott szerveren, vagy rossz a szerver azonosítója. Hívd meg a botot!")
        me = await guild.fetch_member(client.user.id)
        if not me.guild_permissions.administrator:
            sys.exit("A botnak Adminisztrátor jog kell. Hívd meg újra a leírásban lévő linkkel!")
        print(f"Szerver: {guild.name}")

        if os.getenv("ALAP_TORLESE", "").lower() == "true":
            print("Alap szobák törlése:")
            await delete_defaults(guild)
        print("Rangok:")
        roles = await setup_roles(guild)
        print("Kategóriák és szobák:")
        afk = await setup_channels(guild, roles)
        if afk:
            await guild.edit(afk_channel=afk, afk_timeout=900, reason="Szerver felállítása")
            print("AFK csatorna beállítva (15 perc).")

        owner = await guild.fetch_member(guild.owner_id)
        if roles[TULAJ] not in owner.roles:
            await owner.add_roles(roles[TULAJ], reason="Szerver felállítása")
            print(f"{owner.display_name} megkapta a {TULAJ} rangot.")
        print("\n✅ Kész! A botot most már kirúghatod a szerverről.")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
