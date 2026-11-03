"""Durable inbox, cached classifications, and per-destination delivery records."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .domain import Classification, Post


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=5)
        if self.conn.execute("PRAGMA user_version").fetchone()[0] not in (0, 1):
            self.conn.close()
            raise RuntimeError("Unsupported database schema version")
        self.path.chmod(0o600)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS posts (
                key TEXT PRIMARY KEY, payload TEXT NOT NULL,
                result TEXT, classifier TEXT,
                attempts INTEGER NOT NULL DEFAULT 0, error TEXT,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
            );
            CREATE TABLE IF NOT EXISTS deliveries (
                post_key TEXT NOT NULL REFERENCES posts(key), destination TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('pending','delivered','suppressed')),
                attempts INTEGER NOT NULL DEFAULT 0, error TEXT,
                PRIMARY KEY(post_key, destination)
            );
            PRAGMA user_version=1;
        """)

    def close(self):
        self.conn.close()

    @contextmanager
    def lock(self):
        # Advisory OS lock is released automatically on process exit, including crashes.
        # Supported runtime is macOS/Linux; fail clearly on other platforms.
        try:
            import fcntl
        except ImportError:
            raise RuntimeError("Worker locking requires macOS or Linux") from None
        with self.path.with_suffix(self.path.suffix + ".lock").open("a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError("Another worker is using this database") from None
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def ingest(self, posts):
        count = 0
        # Commit the complete fetched batch before classification or notification starts.
        with self.conn:
            for post in posts:
                payload = json.dumps(post.to_dict(), sort_keys=True)
                old = self.conn.execute(
                    "SELECT payload FROM posts WHERE key=?", (post.key,)
                ).fetchone()
                if old and old["payload"] != payload:
                    raise ValueError("Source ID reused with different content; batch rolled back")
                cursor = self.conn.execute(
                    "INSERT OR IGNORE INTO posts(key,payload) VALUES (?,?)", (post.key, payload)
                )
                count += cursor.rowcount
        return count

    def pending(self, destination, limit=100):
        return self.conn.execute(
            """
            SELECT p.* FROM posts p LEFT JOIN deliveries d
            ON d.post_key=p.key AND d.destination=?
            WHERE d.state IS NULL OR d.state='pending'
            ORDER BY p.attempts+COALESCE(d.attempts,0),json_extract(p.payload,'$.published_at'),p.key LIMIT ?
        """,
            (destination, limit),
        ).fetchall()

    def save_result(self, key, result, classifier):
        with self.conn:
            self.conn.execute(
                "UPDATE posts SET result=?,classifier=?,attempts=attempts+1,error=NULL WHERE key=?",
                (json.dumps(result.to_dict()), classifier, key),
            )

    def classification_failed(self, key, error):
        with self.conn:
            self.conn.execute(
                "UPDATE posts SET attempts=attempts+1,error=? WHERE key=?", (error, key)
            )

    def delivery(self, key, destination, state, error=None, attempted=False):
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO deliveries(post_key,destination,state,attempts,error) VALUES (?,?,?,?,?)
                ON CONFLICT(post_key,destination) DO UPDATE SET
                    state=excluded.state, attempts=deliveries.attempts+excluded.attempts,
                    error=excluded.error
            """,
                (key, destination, state, int(attempted), error),
            )

    def records(self, destination):
        rows = self.conn.execute(
            """
            SELECT p.*,d.state,d.attempts AS delivery_attempts,d.error AS delivery_error
            FROM posts p LEFT JOIN deliveries d ON d.post_key=p.key AND d.destination=?
            ORDER BY json_extract(p.payload,'$.published_at') DESC,p.key
        """,
            (destination,),
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def decode(row):
        post = Post(**json.loads(row["payload"]))
        result = Classification.validate(json.loads(row["result"]), post) if row["result"] else None
        return post, result
