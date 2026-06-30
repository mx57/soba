import sqlite3
import time

class DataStore:
    def __init__(self, db_path="activity.db"):
        self.db_path = db_path
        self.conn = None
        self.init_db()

    def init_db(self):
        # Используем одно постоянное соединение для повышения производительности.
        # check_same_thread=False необходим, так как события могут логироваться из разных потоков (InputMonitor).
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)

        # Оптимизация SQLite для быстрой записи
        cursor = self.conn.cursor()
        cursor.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging
        cursor.execute('PRAGMA synchronous=NORMAL')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT,
                description TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                key TEXT PRIMARY KEY,
                value INTEGER
            )
        ''')
        # Инициализация очков привязанности
        cursor.execute('INSERT OR IGNORE INTO stats (key, value) VALUES ("bonding_points", 0)')
        cursor.execute('INSERT OR IGNORE INTO stats (key, value) VALUES ("total_clicks", 0)')
        cursor.execute('INSERT OR IGNORE INTO stats (key, value) VALUES ("total_feedings", 0)')
        cursor.execute('INSERT OR IGNORE INTO stats (key, value) VALUES ("work_seconds", 0)')
        cursor.execute('INSERT OR IGNORE INTO stats (key, value) VALUES ("max_kps", 0)')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id TEXT PRIMARY KEY,
                unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()

    def log_event(self, event_type, description=""):
        if not self.conn:
            self.init_db()

        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO activity_log (event_type, description) VALUES (?, ?)',
            (event_type, description)
        )
        self.conn.commit()

    def get_recent_activity(self, limit=10):
        if not self.conn:
            self.init_db()

        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?', (limit,))
        return cursor.fetchall()

    def add_affection_points(self, points):
        if not self.conn:
            self.init_db()
        cursor = self.conn.cursor()
        cursor.execute('UPDATE stats SET value = value + ? WHERE key = "bonding_points"', (points,))
        self.conn.commit()

    def get_affection_points(self):
        if not self.conn:
            self.init_db()
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM stats WHERE key = "bonding_points"')
        result = cursor.fetchone()
        return result[0] if result else 0

    def increment_stat(self, key, amount=1):
        if not self.conn:
            self.init_db()
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO stats (key, value) VALUES (?, 0)', (key,))
        cursor.execute('UPDATE stats SET value = value + ? WHERE key = ?', (amount, key))
        self.conn.commit()

    def get_stat(self, key):
        if not self.conn:
            self.init_db()
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM stats WHERE key = ?', (key,))
        result = cursor.fetchone()
        return result[0] if result else 0

    def set_stat(self, key, value):
        if not self.conn:
            self.init_db()
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO stats (key, value) VALUES (?, ?)', (key, value))
        self.conn.commit()

    def add_achievement(self, ach_id):
        if not self.conn:
            self.init_db()
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO achievements (id) VALUES (?)', (ach_id,))
        self.conn.commit()

    def get_unlocked_achievements(self):
        if not self.conn:
            self.init_db()
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM achievements')
        return [row[0] for row in cursor.fetchall()]

    def close(self):
        """Закрывает соединение с базой данных."""
        if self.conn:
            self.conn.close()
            self.conn = None
