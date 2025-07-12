import sqlite3
from pathlib import Path

class Memory:
    def __init__(self):
        self.db_path = Path(__file__).parent / "memory.db"
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""CREATE TABLE IF NOT EXISTS context_memory
                         (id TEXT PRIMARY KEY,
                         embedding BLOB,
                         metadata JSON)""")

