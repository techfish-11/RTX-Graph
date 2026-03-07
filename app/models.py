from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

from .config import AppConfig


class Database:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS routers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    host TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS interfaces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    router_id INTEGER NOT NULL,
                    if_index INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    UNIQUE(router_id, if_index),
                    FOREIGN KEY(router_id) REFERENCES routers(id)
                );

                CREATE TABLE IF NOT EXISTS poll_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    interface_id INTEGER,
                    ts INTEGER NOT NULL,
                    in_octets INTEGER,
                    out_octets INTEGER,
                    status TEXT NOT NULL,
                    error TEXT,
                    FOREIGN KEY(interface_id) REFERENCES interfaces(id)
                );
                """
            )

    def sync_from_config(self, config: AppConfig) -> None:
        with self._lock, self._conn:
            for router in config.routers:
                self._conn.execute(
                    """
                    INSERT INTO routers (name, host)
                    VALUES (?, ?)
                    ON CONFLICT(name) DO UPDATE SET host=excluded.host
                    """,
                    (router.name, router.host),
                )

                row = self._conn.execute(
                    "SELECT id FROM routers WHERE name = ?",
                    (router.name,),
                ).fetchone()
                router_id = int(row["id"])

                for iface in router.interfaces:
                    self._conn.execute(
                        """
                        INSERT INTO interfaces (router_id, if_index, name)
                        VALUES (?, ?, ?)
                        ON CONFLICT(router_id, if_index)
                        DO UPDATE SET name=excluded.name
                        """,
                        (router_id, iface.if_index, iface.name),
                    )

    def get_interface_id(self, router_name: str, if_index: int) -> int | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT i.id AS interface_id
                FROM interfaces i
                JOIN routers r ON i.router_id = r.id
                WHERE r.name = ? AND i.if_index = ?
                """,
                (router_name, if_index),
            ).fetchone()
        if row is None:
            return None
        return int(row["interface_id"])

    def log_poll(
        self,
        ts: int,
        status: str,
        interface_id: int | None = None,
        in_octets: int | None = None,
        out_octets: int | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO poll_logs (interface_id, ts, in_octets, out_octets, status, error)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (interface_id, ts, in_octets, out_octets, status, error),
            )

    def get_routers(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, name, host FROM routers ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_router(self, router_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, name, host FROM routers WHERE id = ?",
                (router_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_interfaces(self, router_id: int) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, if_index, name
                FROM interfaces
                WHERE router_id = ?
                ORDER BY if_index
                """,
                (router_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_interface(self, router_id: int, interface_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT id, if_index, name
                FROM interfaces
                WHERE router_id = ? AND id = ?
                """,
                (router_id, interface_id),
            ).fetchone()
        return dict(row) if row else None
