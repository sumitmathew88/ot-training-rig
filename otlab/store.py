"""
otlab.store  -  per-user persistence.

Everything a trainee configures (their tags and their connectivity settings) is
keyed by the username they logged in with and saved to SQLite, so it survives
across sessions: log out, come back days later, and your workspace is still
there.

Where the database lives is controlled by OTLAB_DATA_DIR. On an ordinary host
that defaults to the working directory. On Render the file is wiped on every
redeploy unless OTLAB_DATA_DIR points at a mounted persistent disk (for example
/data) - that is what makes the data durable across deploys.
"""

import json
import os
import sqlite3
import threading


class Store:
    def __init__(self, path=None):
        if path is None:
            d = os.environ.get("OTLAB_DATA_DIR", ".")
            os.makedirs(d, exist_ok=True)
            path = os.path.join(d, "otlab_state.db")
        self.path = path
        self._lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("""CREATE TABLE IF NOT EXISTS tags(
            user TEXT, tag_id TEXT, seq INTEGER, data TEXT,
            PRIMARY KEY(user, tag_id))""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS conn(
            user TEXT, layer TEXT, data TEXT, PRIMARY KEY(user, layer))""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS seqs(
            user TEXT PRIMARY KEY, n INTEGER)""")
        self.db.commit()

    # ---- tags ----
    def next_seq(self, user):
        with self._lock:
            row = self.db.execute("SELECT n FROM seqs WHERE user=?", (user,)).fetchone()
            n = (row[0] if row else 0) + 1
            self.db.execute(
                "INSERT INTO seqs(user,n) VALUES(?,?) "
                "ON CONFLICT(user) DO UPDATE SET n=excluded.n", (user, n))
            self.db.commit()
            return n

    def load_tags(self, user):
        with self._lock:
            rows = self.db.execute(
                "SELECT data FROM tags WHERE user=? ORDER BY seq", (user,)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def get_tag(self, user, tid):
        with self._lock:
            row = self.db.execute(
                "SELECT data FROM tags WHERE user=? AND tag_id=?", (user, tid)).fetchone()
        return json.loads(row[0]) if row else None

    def save_tag(self, user, tag):
        with self._lock:
            self.db.execute(
                "INSERT INTO tags(user,tag_id,seq,data) VALUES(?,?,?,?) "
                "ON CONFLICT(user,tag_id) DO UPDATE SET data=excluded.data",
                (user, tag["id"], tag.get("seq", 0), json.dumps(tag)))
            self.db.commit()

    def delete_tag(self, user, tid):
        with self._lock:
            cur = self.db.execute(
                "DELETE FROM tags WHERE user=? AND tag_id=?", (user, tid))
            self.db.commit()
            return cur.rowcount > 0

    # ---- connectivity ----
    def load_conn(self, user):
        with self._lock:
            rows = self.db.execute(
                "SELECT layer,data FROM conn WHERE user=?", (user,)).fetchall()
        return {layer: json.loads(data) for layer, data in rows}

    def save_conn(self, user, layer, vals):
        with self._lock:
            self.db.execute(
                "INSERT INTO conn(user,layer,data) VALUES(?,?,?) "
                "ON CONFLICT(user,layer) DO UPDATE SET data=excluded.data",
                (user, layer, json.dumps(vals)))
            self.db.commit()
