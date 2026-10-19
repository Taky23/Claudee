"""SQLite tárolás: futó játékok és időkapszulák (újraindítás után is megmaradnak)."""
from __future__ import annotations

import json
import os
import sqlite3


class Storage:
    def __init__(self, path: str):
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS games (
                channel_id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS capsules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER NOT NULL,
                author_id INTEGER,
                author_name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL,
                open_at REAL NOT NULL,
                opened INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_capsules_due ON capsules(opened, open_at);
            """
        )
        self.db.commit()

    # ---------- játékok ----------
    def save_game(self, channel_id: int, data: dict) -> None:
        self.db.execute(
            "INSERT INTO games(channel_id, data) VALUES(?, ?) "
            "ON CONFLICT(channel_id) DO UPDATE SET data = excluded.data",
            (channel_id, json.dumps(data, ensure_ascii=False)),
        )
        self.db.commit()

    def delete_game(self, channel_id: int) -> None:
        self.db.execute("DELETE FROM games WHERE channel_id = ?", (channel_id,))
        self.db.commit()

    def load_games(self) -> list[dict]:
        return [json.loads(r["data"]) for r in self.db.execute("SELECT data FROM games")]

    # ---------- időkapszulák ----------
    def add_capsule(self, guild_id, channel_id, author_id, author_name, content, created_at, open_at) -> int:
        cur = self.db.execute(
            "INSERT INTO capsules(guild_id, channel_id, author_id, author_name, content, created_at, open_at) "
            "VALUES(?, ?, ?, ?, ?, ?, ?)",
            (guild_id, channel_id, author_id, author_name, content, created_at, open_at),
        )
        self.db.commit()
        return cur.lastrowid

    def due_capsules(self, now: float) -> list[sqlite3.Row]:
        return list(self.db.execute("SELECT * FROM capsules WHERE opened = 0 AND open_at <= ? ORDER BY open_at", (now,)))

    def mark_opened(self, capsule_id: int) -> None:
        self.db.execute("UPDATE capsules SET opened = 1 WHERE id = ?", (capsule_id,))
        self.db.commit()

    def user_capsules(self, guild_id: int, author_id: int) -> list[sqlite3.Row]:
        return list(
            self.db.execute(
                "SELECT * FROM capsules WHERE guild_id = ? AND author_id = ? AND opened = 0 ORDER BY open_at",
                (guild_id, author_id),
            )
        )

    def delete_capsule(self, capsule_id: int, author_id: int) -> bool:
        cur = self.db.execute(
            "DELETE FROM capsules WHERE id = ? AND author_id = ? AND opened = 0", (capsule_id, author_id)
        )
        self.db.commit()
        return cur.rowcount > 0
