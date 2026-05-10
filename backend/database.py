"""
Модуль базы данных SQLite.
Хранение истории заказов, смен, статистики и бухгалтерии.
"""

import sqlite3
from datetime import datetime
from config import DATABASE_PATH, Z_LIMIT, Z_PERCENT


class Database:
    """Работа с SQLite."""

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._create_tables()
        self._migrate()

    def _migrate(self):
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("ALTER TABLE orders ADD COLUMN shift_id INTEGER")
                conn.commit()
                conn.execute("ALTER TABLE shifts ADD COLUMN qr_balance TEXT DEFAULT '0'")
                conn.commit()
            except sqlite3.OperationalError:
                pass

    def _create_tables(self):
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
                    details_json TEXT,
                    shift_id INTEGER,
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
                CREATE TABLE IF NOT EXISTS shifts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opened_at TEXT NOT NULL,
                    closed_at TEXT,
                    plan_mdl REAL DEFAULT 0,
                    z_report_mdl REAL DEFAULT 0,
                    fuel_lei REAL DEFAULT 0,
                    total_km REAL DEFAULT 0,
                    qr_balance TEXT DEFAULT '0',
                    notes TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounting (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    shift_id INTEGER,
                    date TEXT NOT NULL,
                    plan_mdl REAL DEFAULT 0,
                    fuel_lei REAL DEFAULT 0,
                    z_percent REAL DEFAULT 0,
                    total_debt REAL DEFAULT 0,
                    paid_cash REAL DEFAULT 0,
                    paid_balance REAL DEFAULT 0,
                    paid_qr REAL DEFAULT 0,
                    total_paid REAL DEFAULT 0,
                    balance REAL DEFAULT 0,
                    notes TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    @staticmethod
    def calc_z_percent(z_report_mdl, plan_mdl=0):
        if plan_mdl and plan_mdl > 0 and z_report_mdl and z_report_mdl > Z_LIMIT:
            return round((z_report_mdl - Z_LIMIT) * Z_PERCENT / 100, 2)
        if (not plan_mdl or plan_mdl == 0) and z_report_mdl and z_report_mdl > 0:
            return round(z_report_mdl * Z_PERCENT / 100, 2)
        return 0.0

    # ----------------------------------------------------------
    # Смены
    # ----------------------------------------------------------

    def get_current_shift(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM shifts WHERE closed_at IS NULL ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def open_shift(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO shifts (opened_at) VALUES (?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)
            )
            conn.commit()
            return cursor.lastrowid

    def close_shift(self, shift_id, plan_mdl=0, z_report_mdl=0, fuel_lei=0, total_km=0, qr_balance="0", notes=""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE shifts 
                SET closed_at = ?, plan_mdl = ?, z_report_mdl = ?, 
                    fuel_lei = ?, total_km = ?, qr_balance = ?, notes = ?
                WHERE id = ?""",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                plan_mdl, z_report_mdl, fuel_lei, total_km, qr_balance, notes, shift_id)
            )
        conn.commit()

    def update_shift_data(self, shift_id, plan_mdl=None, z_report_mdl=None, fuel_lei=None, total_km=None, notes=None):
        fields = []
        values = []
        if plan_mdl is not None:
            fields.append("plan_mdl = ?")
            values.append(plan_mdl)
        if z_report_mdl is not None:
            fields.append("z_report_mdl = ?")
            values.append(z_report_mdl)
        if fuel_lei is not None:
            fields.append("fuel_lei = ?")
            values.append(fuel_lei)
        if total_km is not None:
            fields.append("total_km = ?")
            values.append(total_km)
        if notes is not None:
            fields.append("notes = ?")
            values.append(notes)
        if not fields:
            return
        values.append(shift_id)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"UPDATE shifts SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()

    def get_shifts(self, limit=50):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM shifts ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_shift(self, shift_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            shift = conn.execute(
                "SELECT * FROM shifts WHERE id = ?", (shift_id,)
            ).fetchone()
            if not shift:
                return None
            shift = dict(shift)
            shift["qr_balance"] = shift.get("qr_balance", "0")

            orders = conn.execute(
                "SELECT * FROM orders WHERE shift_id = ? ORDER BY date ASC",
                (shift_id,)
            ).fetchall()
            shift["orders"] = [dict(o) for o in orders]

            stats = conn.execute(
                """SELECT 
                       COUNT(*) as orders_count,
                       COALESCE(SUM(amount), 0) as income,
                       COALESCE(SUM(commission), 0) as commission,
                       COALESCE(SUM(distance_km), 0) as distance_km
                   FROM orders WHERE shift_id = ?""",
                (shift_id,)
            ).fetchone()
            shift["stats"] = dict(stats)

            z_report = shift.get("z_report_mdl", 0) or 0
            plan = shift.get("plan_mdl", 0) or 0
            z_percent = self.calc_z_percent(z_report, plan)
            shift["z_percent"] = z_percent
            shift["net_after_z"] = round(stats["income"] - stats["commission"] - z_percent, 2)
            shift["stats"]["net_profit"] = round(stats["income"] - stats["commission"], 2)
            shift["stats"]["percent_z"] = round((stats["commission"] / stats["income"]) * 100, 1) if stats["income"] > 0 else 0

            return shift

    def get_shift_stats(self, shift_id):
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """SELECT 
                    COUNT(*) as orders_count,
                    COALESCE(SUM(amount), 0) as income,
                    COALESCE(SUM(commission), 0) as commission,
                    COALESCE(SUM(distance_km), 0) as distance_km
                FROM orders WHERE shift_id = ?""",
                (shift_id,)
            ).fetchone()
            z_row = conn.execute(
                "SELECT z_report_mdl, plan_mdl, qr_balance FROM shifts WHERE id = ?", (shift_id,)
            ).fetchone()
            z_report = z_row[0] if z_row else 0
            plan = z_row[1] if z_row else 0
            qr = z_row[2] if z_row else "0"
            z_percent = self.calc_z_percent(z_report, plan)
            net = row[1] - row[2] - z_percent
            return {
                "orders": row[0],
                "income": round(row[1], 2),
                "commission": round(row[2], 2),
                "z_percent": z_percent,
                "net_profit": round(net, 2),
                "distance_km": round(row[3], 1),
                "qr_balance": qr,
            }

    # ----------------------------------------------------------
    # Бухгалтерия
    # ----------------------------------------------------------

    def save_accounting(self, shift_id, plan_mdl=0, fuel_lei=0, z_percent=0,
                         paid_cash=0, paid_balance=0, paid_qr=0, notes=""):
        total_debt = plan_mdl + fuel_lei + z_percent
        total_paid = paid_cash + paid_balance + paid_qr
        balance = total_paid - total_debt
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO accounting 
                (shift_id, date, plan_mdl, fuel_lei, z_percent, total_debt,
                 paid_cash, paid_balance, paid_qr, total_paid, balance, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (shift_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                 plan_mdl, fuel_lei, z_percent, total_debt,
                 paid_cash, paid_balance, paid_qr, total_paid, balance, notes)
            )
            conn.commit()

    def get_accounting(self, limit=50):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM accounting ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_accounting_total(self):
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(balance), 0) FROM accounting"
            ).fetchone()
            return round(row[0], 2)

    # ----------------------------------------------------------
    # Заказы
    # ----------------------------------------------------------

    def order_exists(self, order_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT 1 FROM orders WHERE id = ?", (order_id,)).fetchone()
            return row is not None

    def is_empty(self) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM orders").fetchone()
            return row[0] == 0

    def clear_all(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM orders")
            conn.execute("DELETE FROM daily_stats")
            conn.commit()
        print("[DB] 🗑️ База очищена")

    def save_order(self, order_id, sync_id, date, amount, commission, distance_km, class_type, payment_type, details_json="", shift_id=None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO orders
                (id, sync_id, date, amount, commission, distance_km, class_type, payment_type, details_json, shift_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (order_id, sync_id, date, amount, commission, distance_km, class_type, payment_type, details_json, shift_id),
            )
            conn.commit()

    def save_daily_stats(self, date, orders, income, commission, distance_km):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO daily_stats (date, orders, income, commission, distance_km)
                VALUES (?, ?, ?, ?, ?)""",
                (date, orders, income, commission, distance_km),
            )
            conn.commit()

    def get_orders(self, from_date=None, to_date=None, shift_id=None):
        query = "SELECT * FROM orders WHERE 1=1"
        params = []
        if from_date and to_date:
            query += " AND date BETWEEN ? AND ?"
            params = [from_date, to_date]
        elif from_date:
            query += " AND date >= ?"
            params = [from_date]
        if shift_id is not None:
            query += " AND shift_id = ?"
            params.append(shift_id)
        query += " ORDER BY date DESC"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_daily_stats(self, from_date=None, to_date=None):
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

    def get_total_stats(self, from_date=None, to_date=None):
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