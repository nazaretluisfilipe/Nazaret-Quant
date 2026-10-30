"""Registro append-only local: tentativas pré-registradas, inclusive falhas."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)

class Registry:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, experiment_id TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL, previous_hash TEXT NOT NULL, hash TEXT NOT NULL)")
        self.db.executescript("CREATE TRIGGER IF NOT EXISTS no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'append-only'); END; CREATE TRIGGER IF NOT EXISTS no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'append-only'); END;")
        self.verify()

    def verify(self):
        previous = "0"*64
        for row in self.db.execute("SELECT timestamp, experiment_id, kind, payload, previous_hash, hash FROM events ORDER BY id"):
            ts, exp, kind, payload, prev, digest = row
            expected = hashlib.sha256(canonical([ts, exp, kind, payload, previous]).encode()).hexdigest()
            if prev != previous or digest != expected:
                raise ValueError("Cadeia de auditoria alterada")
            previous = digest
        return previous

    def append(self, experiment_id, kind, payload):
        if kind not in {"PREREGISTERED", "COMPLETED", "FAILED"}:
            raise ValueError("Evento inválido")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            prior = self.db.execute("SELECT kind FROM events WHERE experiment_id=? ORDER BY id", [experiment_id]).fetchall()
            if kind == "PREREGISTERED" and prior or kind != "PREREGISTERED" and prior != [("PREREGISTERED",)]:
                raise ValueError("Experimento duplicado, não registrado ou finalizado")
            previous = self.verify()
            ts = datetime.now(timezone.utc).isoformat()
            content = canonical(payload)
            digest = hashlib.sha256(canonical([ts, experiment_id, kind, content, previous]).encode()).hexdigest()
            self.db.execute("INSERT INTO events(timestamp, experiment_id, kind, payload, previous_hash, hash) VALUES(?,?,?,?,?,?)",
                            [ts, experiment_id, kind, content, previous, digest])
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def close(self):
        self.db.close()
