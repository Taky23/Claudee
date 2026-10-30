"""SQLite tárolás: beállítások, események, szülinapok, ideiglenes hangszobák."""
from __future__ import annotations

import os
import sqlite3

SETTINGS = ("leave_channel", "birthday_channel", "lobby_channel")


class DB:
    def __init__(self, path: str):
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                guild_id INTEGER PRIMARY KEY,
                leave_channel INTEGER,
                birthday_channel INTEGER,
                lobby_channel INTEGER
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,
                creator_id INTEGER NOT NULL,
                game TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                start_at REAL NOT NULL,
                max_players INTEGER,
                reminded INTEGER NOT NULL DEFAULT 0,
                started INTEGER NOT NULL DEFAULT 0,
                cancelled INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS rsvps (
                event_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                at REAL NOT NULL,
                PRIMARY KEY (event_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS birthdays (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                last_year INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS temp_voice (
                channel_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                owner_id INTEGER NOT NULL
            );
            """
        )
        self.db.commit()

    def _run(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        cur = self.db.execute(sql, args)
        self.db.commit()
        return cur

    # ---------- beállítások ----------
    def settings(self, guild_id: int) -> dict:
        row = self.db.execute("SELECT * FROM settings WHERE guild_id = ?", (guild_id,)).fetchone()
        return dict(row) if row else {k: None for k in SETTINGS}

    def set_setting(self, guild_id: int, key: str, value: int | None) -> None:
        assert key in SETTINGS
        self._run("INSERT OR IGNORE INTO settings(guild_id) VALUES(?)", (guild_id,))
        self._run(f"UPDATE settings SET {key} = ? WHERE guild_id = ?", (value, guild_id))

    # ---------- események ----------
    def add_event(self, guild_id, channel_id, creator_id, game, note, start_at, max_players, reminded) -> int:
        return self._run(
            "INSERT INTO events(guild_id, channel_id, creator_id, game, note, start_at, max_players, reminded) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (guild_id, channel_id, creator_id, game, note, start_at, max_players, int(reminded)),
        ).lastrowid

    def set_event(self, event_id: int, **fields) -> None:
        cols = ", ".join(f"{k} = ?" for k in fields)
        self._run(f"UPDATE events SET {cols} WHERE id = ?", (*fields.values(), event_id))

    def event(self, event_id: int) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

    def event_by_message(self, message_id: int) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM events WHERE message_id = ?", (message_id,)).fetchone()

    def events_to_remind(self, now: float, before: float) -> list[sqlite3.Row]:
        return list(self.db.execute(
            "SELECT * FROM events WHERE reminded = 0 AND started = 0 AND cancelled = 0 AND start_at - ? <= ?",
            (before, now),
        ))

    def events_to_start(self, now: float) -> list[sqlite3.Row]:
        return list(self.db.execute(
            "SELECT * FROM events WHERE started = 0 AND cancelled = 0 AND start_at <= ?", (now,)
        ))

    def delete_old_events(self, older_than: float) -> None:
        old = "SELECT id FROM events WHERE start_at < ?"
        self._run(f"DELETE FROM rsvps WHERE event_id IN ({old})", (older_than,))
        self._run("DELETE FROM events WHERE start_at < ?", (older_than,))

    def set_rsvp(self, event_id: int, user_id: int, status: str, at: float) -> None:
        self._run(
            "INSERT INTO rsvps(event_id, user_id, status, at) VALUES(?, ?, ?, ?) "
            "ON CONFLICT(event_id, user_id) DO UPDATE SET status = excluded.status, at = excluded.at",
            (event_id, user_id, status, at),
        )

    def rsvps(self, event_id: int) -> dict[str, list[int]]:
        out: dict[str, list[int]] = {"jovok": [], "talan": [], "nem": []}
        for r in self.db.execute("SELECT * FROM rsvps WHERE event_id = ? ORDER BY at", (event_id,)):
            out[r["status"]].append(r["user_id"])
        return out

    # ---------- szülinapok ----------
    def set_birthday(self, guild_id: int, user_id: int, month: int, day: int, last_year: int) -> None:
        self._run(
            "INSERT INTO birthdays(guild_id, user_id, month, day, last_year) VALUES(?, ?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET month = excluded.month, day = excluded.day, "
            "last_year = excluded.last_year",
            (guild_id, user_id, month, day, last_year),
        )

    def delete_birthday(self, guild_id: int, user_id: int) -> bool:
        return self._run(
            "DELETE FROM birthdays WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        ).rowcount > 0

    def birthdays(self, guild_id: int | None = None) -> list[sqlite3.Row]:
        if guild_id is None:
            return list(self.db.execute("SELECT * FROM birthdays"))
        return list(self.db.execute("SELECT * FROM birthdays WHERE guild_id = ?", (guild_id,)))

    def mark_birthday(self, guild_id: int, user_id: int, year: int) -> None:
        self._run("UPDATE birthdays SET last_year = ? WHERE guild_id = ? AND user_id = ?", (year, guild_id, user_id))

    # ---------- ideiglenes hangszobák ----------
    def add_temp_voice(self, channel_id: int, guild_id: int, owner_id: int) -> None:
        self._run("INSERT OR REPLACE INTO temp_voice VALUES(?, ?, ?)", (channel_id, guild_id, owner_id))

    def is_temp_voice(self, channel_id: int) -> bool:
        return self.db.execute("SELECT 1 FROM temp_voice WHERE channel_id = ?", (channel_id,)).fetchone() is not None

    def temp_voices(self) -> list[int]:
        return [r[0] for r in self.db.execute("SELECT channel_id FROM temp_voice")]

    def delete_temp_voice(self, channel_id: int) -> None:
        self._run("DELETE FROM temp_voice WHERE channel_id = ?", (channel_id,))
