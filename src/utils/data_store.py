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

    def close(self):
        """Закрывает соединение с базой данных."""
        if self.conn:
            self.conn.close()
            self.conn = None
