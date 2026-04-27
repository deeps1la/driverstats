"""
Модуль базы данных SQLite.
Хранение истории заказов и статистики по дням.
"""

import sqlite3
from datetime import datetime
from config import DATABASE_PATH


class Database:
    """Работа с SQLite."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._create_tables()
        
    def order_exists(self, order_id: int) -> bool:
        """Проверяет, сохранён ли уже заказ с таким ID."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
            return row is not None        
    #-----------------------------------------------------------
    # Очистка базы
    #-----------------------------------------------------------
    def is_empty(self) -> bool:
        """Проверяет, есть ли хоть один заказ в базе."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM orders").fetchone()
            return row[0] == 0

    def clear_all(self):
        """Очищает все таблицы."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM orders")
            conn.execute("DELETE FROM daily_stats")
            conn.commit()
        print("[DB] 🗑️ База очищена")
    # ----------------------------------------------------------
    # Создание таблиц
    # ----------------------------------------------------------

    def add_details_column(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("ALTER TABLE orders ADD COLUMN details_json TEXT")
                conn.commit()
        except:
            pass    # Уже есть

    def _create_tables(self):
        """Создаёт таблицы, если их ещё нет."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY,
                    sync_id TEXT,
                    date TEXT,
                    amount REAL,
                    commission REAL,
                    distance_km REAL,
                    class_type TEXT,
                    payment_type TEXT,
                    start_address TEXT,
                    end_address TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    orders INTEGER,
                    income REAL,
                    commission REAL,
                    distance_km REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY,
                    sync_id TEXT,
                    date TEXT,
                    amount REAL,
                    commission REAL,
                    distance_km REAL,
                    class_type TEXT,
                    payment_type TEXT,
                    details_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    # ----------------------------------------------------------
    # Сохранение заказа
    # ----------------------------------------------------------

    def save_order(self, order_id, sync_id, date, amount, commission, distance_km, class_type, payment_type, details_json=""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO orders
                (id, sync_id, date, amount, commission, distance_km, class_type, payment_type, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (order_id, sync_id, date, amount, commission, distance_km, class_type, payment_type, details_json),
            )
            conn.commit()

    # ----------------------------------------------------------
    # Сохранение дневной статистики
    # ----------------------------------------------------------

    def save_daily_stats(
        self,
        date: str,
        orders: int,
        income: float,
        commission: float,
        distance_km: float,
    ):
        """Сохраняет сводку за день."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO daily_stats (date, orders, income, commission, distance_km)
                VALUES (?, ?, ?, ?, ?)
                """,
                (date, orders, income, commission, distance_km),
            )
            conn.commit()

    # ----------------------------------------------------------
    # Получение истории
    # ----------------------------------------------------------

    def get_orders(self, from_date: str = None, to_date: str = None) -> list:
        """
        Возвращает список заказов за период.

        Args:
            from_date: с какой даты (YYYY-MM-DD).
            to_date: по какую дату (YYYY-MM-DD).

        Returns:
            Список словарей с заказами.
        """
        query = "SELECT * FROM orders"
        params = []

        if from_date and to_date:
            query += " WHERE date BETWEEN ? AND ?"
            params = [from_date, to_date]
        elif from_date:
            query += " WHERE date >= ?"
            params = [from_date]

        query += " ORDER BY date DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_daily_stats(self, from_date: str = None, to_date: str = None) -> list:
        """
        Возвращает дневную статистику за период.

        Args:
            from_date: с какой даты (YYYY-MM-DD).
            to_date: по какую дату (YYYY-MM-DD).

        Returns:
            Список словарей с дневной статистикой.
        """
        query = "SELECT * FROM daily_stats"
        params = []

        if from_date and to_date:
            query += " WHERE date BETWEEN ? AND ?"
            params = [from_date, to_date]
        elif from_date:
            query += " WHERE date >= ?"
            params = [from_date]

        query += " ORDER BY date ASC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    # ----------------------------------------------------------
    # Статистика за период (агрегация из сохранённого)
    # ----------------------------------------------------------

    def get_total_stats(self, from_date: str = None, to_date: str = None) -> dict:
        """
        Возвращает общую статистику за период.

        Args:
            from_date: с какой даты.
            to_date: по какую дату.

        Returns:
            Словарь с суммарными показателями.
        """
        query = """
            SELECT 
                COUNT(*) as orders,
                COALESCE(SUM(amount), 0) as income,
                COALESCE(SUM(commission), 0) as commission,
                COALESCE(SUM(distance_km), 0) as distance_km
            FROM orders
        """
        params = []

        if from_date and to_date:
            query += " WHERE date BETWEEN ? AND ?"
            params = [from_date, to_date]
        elif from_date:
            query += " WHERE date >= ?"
            params = [from_date]

        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(query, params).fetchone()
            return {
                "orders": row[0],
                "income": round(row[1], 2),
                "commission": round(row[2], 2),
                "net_profit": round(row[1] - row[2], 2),
                "distance_km": round(row[3], 1),
            }