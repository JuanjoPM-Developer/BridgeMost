"""Persistent message ID mapping using SQLite.

Survives restarts so edits, deletes, and reactions continue working
for messages sent before the current session.
"""

import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger("bridgemost.store")

# Default: keep mappings for 30 days
DEFAULT_TTL_DAYS = 30


class MessageStore:
    """SQLite-backed bidirectional TG↔MM message ID mapping.

    Schema:
        tg_msg_id  INTEGER  — Telegram message_id
        mm_post_id TEXT     — Mattermost post ID (26-char alphanumeric)
        tg_chat_id INTEGER  — Telegram chat ID (for multi-user support)
        created_at REAL     — Unix timestamp
    """

    def __init__(self, db_path: str | Path, ttl_days: int = DEFAULT_TTL_DAYS):
        self.db_path = str(db_path)
        self.ttl_days = ttl_days
        self._conn: sqlite3.Connection | None = None

    def open(self):
        """Open database and create table if needed."""
        self._conn = sqlite3.connect(self.db_path, timeout=5.0)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=3000")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS message_map (
                tg_msg_id   INTEGER NOT NULL,
                mm_post_id  TEXT    NOT NULL,
                tg_chat_id  INTEGER NOT NULL DEFAULT 0,
                created_at  REAL    NOT NULL,
                PRIMARY KEY (tg_msg_id, tg_chat_id)
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_mm_post_id
            ON message_map (mm_post_id)
        """)
        self._conn.commit()

        # Prune old entries
        self._prune()

        count = self._conn.execute("SELECT COUNT(*) FROM message_map").fetchone()[0]
        logger.info("MessageStore opened: %s (%d mappings)", self.db_path, count)

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def put(self, tg_msg_id: int, mm_post_id: str, tg_chat_id: int = 0):
        """Store a TG↔MM message pair."""
        if not self._conn:
            return
        self._conn.execute(
            "INSERT OR REPLACE INTO message_map (tg_msg_id, mm_post_id, tg_chat_id, created_at) "
            "VALUES (?, ?, ?, ?)",
            (tg_msg_id, mm_post_id, tg_chat_id, time.time()),
        )
        self._conn.commit()

    def get_mm(self, tg_msg_id: int, tg_chat_id: int = 0) -> str | None:
        """Get MM post_id from TG message_id."""
        if not self._conn:
            return None
        row = self._conn.execute(
            "SELECT mm_post_id FROM message_map WHERE tg_msg_id = ? AND tg_chat_id = ?",
            (tg_msg_id, tg_chat_id),
        ).fetchone()
        return row[0] if row else None

    def get_tg(self, mm_post_id: str) -> int | None:
        """Get TG message_id from MM post_id."""
        if not self._conn:
            return None
        row = self._conn.execute(
            "SELECT tg_msg_id FROM message_map WHERE mm_post_id = ?",
            (mm_post_id,),
        ).fetchone()
        return row[0] if row else None

    def has_tg(self, tg_msg_id: int) -> bool:
        """Check if a TG message exists in the store."""
        if not self._conn:
            return False
        row = self._conn.execute(
            "SELECT 1 FROM message_map WHERE tg_msg_id = ? LIMIT 1",
            (tg_msg_id,),
        ).fetchone()
        return row is not None

    def count(self) -> int:
        """Return number of stored mappings."""
        if not self._conn:
            return 0
        return self._conn.execute("SELECT COUNT(*) FROM message_map").fetchone()[0]

    def _prune(self):
        """Remove entries older than TTL."""
        if not self._conn:
            return
        cutoff = time.time() - (self.ttl_days * 86400)
        cursor = self._conn.execute(
            "DELETE FROM message_map WHERE created_at < ?", (cutoff,)
        )
        if cursor.rowcount > 0:
            self._conn.commit()
            logger.info("Pruned %d expired message mappings (>%dd old)", cursor.rowcount, self.ttl_days)
