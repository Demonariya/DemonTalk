"""SQLite database manager."""
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from app.config import DB_PATH
from app.utils.logger import setup_logger

log = setup_logger('DB')


class Database:
    _instance = None
    _conn = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._conn is None:
            self._connect()
            self._migrate()

    def _connect(self):
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        log.info(f"Database connected: {DB_PATH}")

    def _migrate(self):
        cursor = self._conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                nickname TEXT DEFAULT '',
                ip_address TEXT NOT NULL,
                port INTEGER DEFAULT 37021,
                avatar TEXT DEFAULT '',
                is_favorite INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0,
                connection_type TEXT DEFAULT 'local',
                last_seen TEXT,
                first_seen TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS channels (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                password TEXT DEFAULT '',
                is_locked INTEGER DEFAULT 0,
                creator_id TEXT,
                member_count INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS channel_members (
                channel_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                role TEXT DEFAULT 'member',
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel_id, device_id),
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
                FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                sender_id TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                channel_id TEXT,
                recipient_id TEXT,
                content TEXT NOT NULL,
                message_type TEXT DEFAULT 'text',
                is_read INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS voice_messages (
                id TEXT PRIMARY KEY,
                sender_id TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                channel_id TEXT,
                recipient_id TEXT,
                file_path TEXT NOT NULL,
                duration REAL DEFAULT 0.0,
                file_size INTEGER DEFAULT 0,
                waveform_data TEXT DEFAULT '[]',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS calls (
                id TEXT PRIMARY KEY,
                caller_id TEXT NOT NULL,
                caller_name TEXT NOT NULL,
                receiver_id TEXT,
                channel_id TEXT,
                call_type TEXT DEFAULT 'push_to_talk',
                status TEXT DEFAULT 'completed',
                duration REAL DEFAULT 0.0,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_calls_caller ON calls(caller_id, started_at);
            CREATE INDEX IF NOT EXISTS idx_devices_ip ON devices(ip_address);
        """)
        self._conn.commit()
        log.info("Database migration complete")

    def execute(self, query, params=None):
        try:
            if params:
                result = self._conn.execute(query, params)
            else:
                result = self._conn.execute(query)
            self._conn.commit()
            return result
        except sqlite3.Error as e:
            log.error(f"DB error: {e} | query: {query[:100]}")
            raise

    def fetchone(self, query, params=None):
        row = self.execute(query, params).fetchone()
        return dict(row) if row else None

    def fetchall(self, query, params=None):
        rows = self.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    # --- Device operations ---
    def add_device(self, device_id, name, ip, port=37021, connection_type='local'):
        now = datetime.utcnow().isoformat()
        self.execute("""
            INSERT OR REPLACE INTO devices (id, name, ip_address, port, connection_type, last_seen, first_seen)
            VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT first_seen FROM devices WHERE id=?), ?))
        """, (device_id, name, ip, port, connection_type, now, now, device_id, now))

    def update_device_seen(self, device_id, ip=None):
        now = datetime.utcnow().isoformat()
        if ip:
            self.execute("UPDATE devices SET last_seen=?, ip_address=? WHERE id=?", (now, ip, device_id))
        else:
            self.execute("UPDATE devices SET last_seen=? WHERE id=?", (now, device_id))

    def get_device(self, device_id):
        return self.fetchone("SELECT * FROM devices WHERE id=?", (device_id,))

    def get_all_devices(self):
        return self.fetchall("SELECT * FROM devices ORDER BY is_favorite DESC, last_seen DESC")

    def get_online_devices(self, seconds=10):
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(seconds=seconds)).isoformat()
        return self.fetchall(
            "SELECT * FROM devices WHERE last_seen > ? AND is_blocked=0 ORDER BY is_favorite DESC",
            (cutoff,)
        )

    def set_favorite(self, device_id, is_favorite=True):
        self.execute("UPDATE devices SET is_favorite=? WHERE id=?", (int(is_favorite), device_id))

    def set_blocked(self, device_id, is_blocked=True):
        self.execute("UPDATE devices SET is_blocked=? WHERE id=?", (int(is_blocked), device_id))

    def delete_device(self, device_id):
        self.execute("DELETE FROM devices WHERE id=?", (device_id,))

    # --- Channel operations ---
    def create_channel(self, channel_id, name, password='', creator_id=''):
        now = datetime.utcnow().isoformat()
        self.execute("""
            INSERT INTO channels (id, name, password, creator_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (channel_id, name, password, creator_id, now, now))
        if creator_id:
            self.add_channel_member(channel_id, creator_id, 'admin')

    def get_channel(self, channel_id):
        return self.fetchone("SELECT * FROM channels WHERE id=?", (channel_id,))

    def get_all_channels(self):
        return self.fetchall("SELECT * FROM channels ORDER BY name")

    def update_channel(self, channel_id, **kwargs):
        allowed = {'name', 'description', 'password', 'is_locked'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        updates['updated_at'] = datetime.utcnow().isoformat()
        set_clause = ', '.join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [channel_id]
        self.execute(f"UPDATE channels SET {set_clause} WHERE id=?", values)

    def delete_channel(self, channel_id):
        self.execute("DELETE FROM channels WHERE id=?", (channel_id,))

    def add_channel_member(self, channel_id, device_id, role='member'):
        now = datetime.utcnow().isoformat()
        self.execute("""
            INSERT OR IGNORE INTO channel_members (channel_id, device_id, role, joined_at)
            VALUES (?, ?, ?, ?)
        """, (channel_id, device_id, role, now))
        self.execute(
            "UPDATE channels SET member_count = (SELECT COUNT(*) FROM channel_members WHERE channel_id=?) WHERE id=?",
            (channel_id, channel_id)
        )

    def remove_channel_member(self, channel_id, device_id):
        self.execute("DELETE FROM channel_members WHERE channel_id=? AND device_id=?", (channel_id, device_id))
        self.execute(
            "UPDATE channels SET member_count = (SELECT COUNT(*) FROM channel_members WHERE channel_id=?) WHERE id=?",
            (channel_id, channel_id)
        )

    def get_channel_members(self, channel_id):
        return self.fetchall("""
            SELECT d.*, cm.role, cm.joined_at FROM devices d
            JOIN channel_members cm ON d.id = cm.device_id
            WHERE cm.channel_id = ?
        """, (channel_id,))

    # --- Message operations ---
    def add_message(self, sender_id, sender_name, content, channel_id=None, recipient_id=None, msg_type='text'):
        msg_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        self.execute("""
            INSERT INTO messages (id, sender_id, sender_name, content, channel_id, recipient_id, message_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (msg_id, sender_id, sender_name, content, channel_id, recipient_id, msg_type, now))
        return msg_id

    def get_messages(self, channel_id=None, recipient_id=None, limit=100, offset=0):
        if channel_id:
            return self.fetchall(
                "SELECT * FROM messages WHERE channel_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (channel_id, limit, offset)
            )
        elif recipient_id:
            return self.fetchall(
                "SELECT * FROM messages WHERE recipient_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (recipient_id, limit, offset)
            )
        return []

    # --- Voice message operations ---
    def add_voice_message(self, sender_id, sender_name, file_path, duration=0, file_size=0,
                          waveform_data='[]', channel_id=None, recipient_id=None):
        vm_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        self.execute("""
            INSERT INTO voice_messages (id, sender_id, sender_name, file_path, duration, file_size,
                waveform_data, channel_id, recipient_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (vm_id, sender_id, sender_name, file_path, duration, file_size, waveform_data,
              channel_id, recipient_id, now))
        return vm_id

    def get_voice_messages(self, channel_id=None, limit=50):
        if channel_id:
            return self.fetchall(
                "SELECT * FROM voice_messages WHERE channel_id=? ORDER BY created_at DESC LIMIT ?",
                (channel_id, limit)
            )
        return self.fetchall(
            "SELECT * FROM voice_messages ORDER BY created_at DESC LIMIT ?", (limit,)
        )

    # --- Call operations ---
    def add_call(self, caller_id, caller_name, receiver_id=None, channel_id=None,
                 call_type='push_to_talk', status='completed', duration=0):
        call_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        self.execute("""
            INSERT INTO calls (id, caller_id, caller_name, receiver_id, channel_id,
                call_type, status, duration, started_at, ended_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (call_id, caller_id, caller_name, receiver_id, channel_id,
              call_type, status, duration, now, now))
        return call_id

    def get_calls(self, limit=50):
        return self.fetchall("SELECT * FROM calls ORDER BY started_at DESC LIMIT ?", (limit,))

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
