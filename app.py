"""
Letz Driver Stats — точка входа.
Запуск Flask-сервера, маршруты, связь фронтенда с бэкендом.
"""
APP_NAME = "DRIVER STATS"
APP_VERSION = "1.2 Beta"

# ----------------------------------------------------------
# Импорты
# ----------------------------------------------------------

from flask import Flask, render_template, jsonify, request
from config import SERVER_HOST, SERVER_PORT, SERVER_DEBUG, LETZ_ACCESS_TOKEN, DATABASE_PATH
from backend.auth import LetzAuth, refresh_access_token
from backend.api_letz import LetzApi, TaxiDb
from backend.calculator import (
    is_order,
    extract_distance,
    extract_class,
    calculate_stats,
)
from backend.database import Database
from datetime import datetime
import json
import os
import time
import requests as req

# ----------------------------------------------------------
# Создание приложения
# ----------------------------------------------------------

app = Flask(
    __name__,
    template_folder="frontend/templates",
    static_folder="frontend/static",
)

START_DATE = "2026-05-09"
db = Database()
# ----------------------------------------------------------
# Настройки из БД (приоритет над config.py)
# ----------------------------------------------------------

def get_access_token():
    token = db.get_setting("access_token")
    if token:
        return token
    from config import LETZ_ACCESS_TOKEN
    db.set_setting("access_token", LETZ_ACCESS_TOKEN)
    return LETZ_ACCESS_TOKEN

def get_device_id():
    device = db.get_setting("device_id")
    if device:
        return device
    from config import LETZ_DEVICE_ID
    db.set_setting("device_id", LETZ_DEVICE_ID)
    return LETZ_DEVICE_ID

def init_settings():
    from config import LETZ_ACCESS_TOKEN, LETZ_DEVICE_ID
    defaults = {
        "access_token": LETZ_ACCESS_TOKEN,
        "device_id": LETZ_DEVICE_ID,
        "start_date": START_DATE,
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
    }
    for key, value in defaults.items():
        if not db.get_setting(key):
            db.set_setting(key, value)

# Загружаем сохранённые
saved_start = db.get_setting("start_date")
if saved_start:
    START_DATE = saved_start
saved_name = db.get_setting("app_name")
if saved_name:
    APP_NAME = saved_name
saved_version = db.get_setting("app_version")
if saved_version:
    APP_VERSION = saved_version

init_settings()

def get_current_shift_id():
    """Возвращает ID открытой смены или None."""
    shift = db.get_current_shift()
    return shift["id"] if shift else None


# ----------------------------------------------------------
# Главная
# ----------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", app_name=APP_NAME, app_version=APP_VERSION)


@app.route("/api/balance")
def api_balance():
    auth = LetzAuth(access_token=get_access_token(), device_id=get_device_id())
    session_id = auth.login()
    print(f"[DEBUG] Используем токен: {get_access_token()[:10]}...")
    if not session_id:
        return jsonify({"balance": 0})
    api = LetzApi(session_id)
    try:
        transactions_data = api.fetch_all_transactions()
        balance = transactions_data.get("CurrentBalance", 0)
        return jsonify({"balance": balance})
    except:
        return jsonify({"balance": 0})


# ----------------------------------------------------------
# Настройки
# ----------------------------------------------------------

@app.route("/settings")
def settings_page():
    return render_template("settings.html", app_name=APP_NAME, app_version=APP_VERSION)

@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "GET":
        return jsonify({
            "start_date": START_DATE,
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
            "access_token": get_access_token(),
            "device_id": get_device_id(),
            "login": db.get_setting("login"),
            "password": db.get_setting("password"),
        })

    data = request.get_json()
    if "access_token" in data:
        db.set_setting("access_token", data["access_token"])
    if "device_id" in data:
        db.set_setting("device_id", data["device_id"])
    if "start_date" in data:
        db.set_setting("start_date", data["start_date"])
        globals()["START_DATE"] = data["start_date"]
    if "app_name" in data:
        db.set_setting("app_name", data["app_name"])
        globals()["APP_NAME"] = data["app_name"]
    if "app_version" in data:
        db.set_setting("app_version", data["app_version"])
        globals()["APP_VERSION"] = data["app_version"]
    if "login" in data:
        db.set_setting("login", data["login"])
    if "password" in data:
        db.set_setting("password", data["password"])

    return jsonify({"ok": True})

def save_config(config_module):
    """Сохраняет текущие настройки в config.py."""
    config_path = os.path.join(os.path.dirname(__file__), "config.py")
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(f'''"""
Конфигурация приложения Letz Driver Stats.
Все секретные ключи и настройки в одном месте.
"""

# ============================================================
# API Letz
# ============================================================

LETZ_ACCESS_TOKEN = "{config_module.LETZ_ACCESS_TOKEN}"
LETZ_DEVICE_ID = "{config_module.LETZ_DEVICE_ID}"
LETZ_APP_VERSION = "{config_module.LETZ_APP_VERSION}"
LETZ_BASE_URL = "{config_module.LETZ_BASE_URL}"
ITS_API_URL = "{config_module.ITS_API_URL}"

# ============================================================
# Сервер Flask
# ============================================================

SERVER_HOST = "{config_module.SERVER_HOST}"
SERVER_PORT = {config_module.SERVER_PORT}
SERVER_DEBUG = {config_module.SERVER_DEBUG}

# ============================================================
# База данных
# ============================================================

DATABASE_PATH = "{config_module.DATABASE_PATH}"

# ============================================================
# API-ключ для внешних приложений
# ============================================================

EXTERNAL_API_KEY = "{config_module.EXTERNAL_API_KEY}"

# ============================================================
# Z-отчёт
# ============================================================

Z_LIMIT = {config_module.Z_LIMIT}
Z_PERCENT = {config_module.Z_PERCENT}
''')
    print("[CONFIG] ✅ Настройки сохранены в config.py")
@app.route("/api/system-info")
def api_system_info():
    info = {"letz_connected": False, "letz_ping": 0, "db_size": "0 KB", "app_size": "0 KB"}
    try:
        start = time.time()
        resp = req.get("http://letz99.from-md.com/ts.mobilerest/login", timeout=5)
        end = time.time()
        info["letz_ping"] = round((end - start) * 1000, 1)
        info["letz_connected"] = resp.status_code < 500
    except:
        pass
    if os.path.exists(DATABASE_PATH):
        size_bytes = os.path.getsize(DATABASE_PATH)
        if size_bytes < 1024 * 1024:
            info["db_size"] = f"{size_bytes / 1024:.1f} KB"
        else:
            info["db_size"] = f"{size_bytes / (1024 * 1024):.1f} MB"
    total_size = 0
    for dirpath, dirnames, filenames in os.walk("."):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    if total_size < 1024 * 1024:
        info["app_size"] = f"{total_size / 1024:.1f} KB"
    else:
        info["app_size"] = f"{total_size / (1024 * 1024):.1f} MB"
    return jsonify(info)


# ----------------------------------------------------------
# Заказы
# ----------------------------------------------------------

@app.route("/orders")
def orders_page():
    return render_template("orders.html", app_name=APP_NAME, app_version=APP_VERSION)


@app.route("/api/orders")
def api_orders():
    orders = db.get_orders()
    return jsonify({"orders": orders})


@app.route("/api/order/<int:order_id>")
def api_order_detail(order_id):
    orders = db.get_orders()
    for o in orders:
        if o["id"] == order_id:
            detail = json.loads(o.get("details_json", "{}"))
            taxi = TaxiDb()
            addr = detail.get("Order", {}).get("Address", {})
            street_name = taxi.get_street_name(addr.get("StreetId", 0))
            settlement_name = taxi.get_settlement_name(addr.get("SettlementId", 0))
            return jsonify({
                "id": o["id"],
                "date": o["date"],
                "amount": o["amount"],
                "commission": o["commission"],
                "distance": o["distance_km"],
                "class_type": o["class_type"],
                "payment_type": o["payment_type"],
                "address": f"{settlement_name}, {street_name}, {addr.get('House', '')}",
            })
    return jsonify({"error": "Заказ не найден"}), 404


# ----------------------------------------------------------
# Статистика
# ----------------------------------------------------------

@app.route("/api/stats")
@app.route("/api/stats")
def api_stats():
    # Пробуем авторизоваться
    auth = LetzAuth(access_token=get_access_token(), device_id=get_device_id())
    session_id = auth.login()

    # Если токен умер — пробуем обновить
    if not session_id:
        login = db.get_setting("login")
        password = db.get_setting("password")
        
        if login and password:
            print("[STATS] 🔄 Токен умер, пробуем обновить...")
            new_token = refresh_access_token(login, password, get_device_id())
            
            if new_token:
                db.set_setting("access_token", new_token)
                print("[STATS] ✅ Токен обновлён, пробуем снова...")
                auth = LetzAuth(access_token=new_token, device_id=get_device_id())
                session_id = auth.login()

    # Если всё равно нет — отдаём данные из БД
    if not session_id:
        current = db.get_current_shift()
        current_stats = {"orders": 0, "income": 0, "commission": 0, "net_profit": 0, "distance_km": 0, "z_percent": 0}
        if current:
            cs = db.get_shift_stats(current["id"])
            current_stats = {
                "orders": cs["orders"],
                "income": cs["income"],
                "commission": cs["commission"],
                "net_profit": cs["net_profit"],
                "distance_km": cs["distance_km"],
                "z_percent": cs.get("z_percent", 0),
            }

        prev_stats = {"orders": 0, "income": 0, "commission": 0, "net_profit": 0, "distance_km": 0}
        all_shifts = db.get_shifts(limit=50)
        for s in all_shifts:
            if s["closed_at"] is not None:
                ps = db.get_shift_stats(s["id"])
                prev_stats = {
                    "orders": ps["orders"],
                    "income": ps["income"],
                    "commission": ps["commission"],
                    "net_profit": ps["net_profit"],
                    "distance_km": ps["distance_km"],
                }
                break

        return jsonify({
            "today": current_stats,
            "yesterday": prev_stats,
            "balance": 0,
            "shift_open": current is not None,
            "last_update": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "cached": True
        })

    # Работаем с Letz API
    api = LetzApi(session_id)

    try:
        transactions_data = api.fetch_all_transactions()
    except:
        # API не отвечает — отдаём БД
        current = db.get_current_shift()
        current_stats = {"orders": 0, "income": 0, "commission": 0, "net_profit": 0, "distance_km": 0, "z_percent": 0}
        if current:
            cs = db.get_shift_stats(current["id"])
            current_stats = {
                "orders": cs["orders"],
                "income": cs["income"],
                "commission": cs["commission"],
                "net_profit": cs["net_profit"],
                "distance_km": cs["distance_km"],
                "z_percent": cs.get("z_percent", 0),
            }

        prev_stats = {"orders": 0, "income": 0, "commission": 0, "net_profit": 0, "distance_km": 0}
        all_shifts = db.get_shifts(limit=50)
        for s in all_shifts:
            if s["closed_at"] is not None:
                ps = db.get_shift_stats(s["id"])
                prev_stats = {
                    "orders": ps["orders"],
                    "income": ps["income"],
                    "commission": ps["commission"],
                    "net_profit": ps["net_profit"],
                    "distance_km": ps["distance_km"],
                }
                break

        return jsonify({
            "today": current_stats,
            "yesterday": prev_stats,
            "balance": 0,
            "shift_open": current is not None,
            "last_update": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "cached": True
        })

    balance = transactions_data.get("CurrentBalance", 0)

    # Сохраняем новые заказы
    all_transactions = []
    for day in transactions_data.get("Data", []):
        day_str = day.get("Day", "")[:10]
        for tx in day.get("Transactions", []):
            tx["_day"] = day_str
            all_transactions.append(tx)

    all_transactions.sort(key=lambda x: x.get("Id", 0), reverse=True)

    current_shift_id = get_current_shift_id()
    for tx in all_transactions:
        tx_date = tx.get("Time", tx.get("_day", ""))[:10]
        if tx_date < START_DATE:
            continue
        if tx.get("Type") == 20 or tx.get("Type") == "Iesire":
            continue
        if not is_order(tx):
            continue
        if db.order_exists(tx["Id"]):
            continue
        try:
            detail = api.fetch_transaction_detail(tx["Id"])
            dist = extract_distance(detail)
            sync_id = tx.get("SyncOrderId", "")
            commission = 0.0
            for t in all_transactions:
                if t.get("Type") == 20 and t.get("SyncOrderId") == sync_id:
                    commission = abs(t.get("Value", 0))
                    break
            db.save_order(
                order_id=tx["Id"],
                sync_id=sync_id,
                date=tx.get("Time", tx.get("_day", "")),
                amount=tx.get("Value", 0),
                commission=commission,
                distance_km=dist,
                class_type=extract_class(detail),
                payment_type=detail.get("Data", {}).get("TypeOfCash", ""),
                details_json=json.dumps(detail),
                shift_id=current_shift_id,
            )
        except Exception as e:
            print(f"  ⚠️ Ошибка заказа #{tx['Id']}: {e}")

    # Статистика: текущая смена vs прошлая
    current = db.get_current_shift()
    current_stats = {"orders": 0, "income": 0, "commission": 0, "net_profit": 0, "distance_km": 0, "z_percent": 0}

    if current:
        cs = db.get_shift_stats(current["id"])
        current_stats = {
            "orders": cs["orders"],
            "income": cs["income"],
            "commission": cs["commission"],
            "net_profit": cs["net_profit"],
            "distance_km": cs["distance_km"],
            "z_percent": cs.get("z_percent", 0),
        }

    prev_stats = {"orders": 0, "income": 0, "commission": 0, "net_profit": 0, "distance_km": 0}
    all_shifts = db.get_shifts(limit=50)
    for s in all_shifts:
        if s["closed_at"] is not None:
            ps = db.get_shift_stats(s["id"])
            prev_stats = {
                "orders": ps["orders"],
                "income": ps["income"],
                "commission": ps["commission"],
                "net_profit": ps["net_profit"],
                "distance_km": ps["distance_km"],
            }
            break

    return jsonify({
        "today": current_stats,
        "yesterday": prev_stats,
        "balance": balance,
        "shift_open": current is not None,
        "last_update": datetime.now().strftime("%d.%m.%Y %H:%M"),
    })
# ----------------------------------------------------------
# Отчёты
# ----------------------------------------------------------

@app.route("/reports")
def reports_page():
    return render_template("reports.html", app_name=APP_NAME, app_version=APP_VERSION)


@app.route("/api/report")
def api_report():
    from_date = request.args.get("from", "")
    to_date = request.args.get("to", "")
    stats = db.get_total_stats(from_date=from_date, to_date=to_date)
    orders = db.get_orders(from_date=from_date, to_date=to_date)
    class_counts = {}
    for o in orders:
        cls = o.get("class_type", "?")
        class_counts[cls] = class_counts.get(cls, 0) + 1
    income = stats["income"]
    commission = stats["commission"]
    percent_z = round((commission / income) * 100, 1) if income > 0 else 0
    return jsonify({
        "orders": stats["orders"],
        "distance": stats["distance_km"],
        "income": income,
        "commission": commission,
        "percent_z": percent_z,
        "net_profit": stats["net_profit"],
        "class_counts": class_counts,
    })


# ----------------------------------------------------------
# Смены
# ----------------------------------------------------------

@app.route("/shift")
def shift_page():
    return render_template("shift.html", app_name=APP_NAME, app_version=APP_VERSION)


@app.route("/shifts")
def shifts_page():
    return render_template("shifts.html", app_name=APP_NAME, app_version=APP_VERSION)


@app.route("/shift/<int:shift_id>")
def shift_detail_page(shift_id):
    return render_template("shift_detail.html", shift_id=shift_id, app_name=APP_NAME, app_version=APP_VERSION)


@app.route("/api/shift", methods=["GET", "POST"])
def api_shift():
    if request.method == "GET":
        shift = db.get_current_shift()
        if shift:
            shift["stats"] = db.get_shift_stats(shift["id"])
            shift["open"] = True
            return jsonify(shift)
        return jsonify({"open": False})

    data = request.get_json()
    action = data.get("action", "")

    if action == "open":
        current = db.get_current_shift()
        if current:
            return jsonify({"error": "Уже есть открытая смена", "shift_id": current["id"]}), 409
        shift_id = db.open_shift()
        return jsonify({"ok": True, "shift_id": shift_id})

    elif action == "close":
        shift_id = data.get("shift_id")
        if not shift_id:
            return jsonify({"error": "Нет shift_id"}), 400

        # Получаем QR-баланс
        qr_balance = "0"
        try:
            auth = LetzAuth(access_token=get_access_token(), device_id=get_device_id())
            session_id = auth.login()
            if session_id:
                api = LetzApi(session_id)
                overview = api.fetch_car_nickname_overview()
                for r in overview.get("Info", {}).get("InfoRecords", []):
                    if r.get("Name") == "Баланс QR":
                        qr_balance = r.get("Value", "0")
                        break
        except:
            pass

        db.close_shift(
            shift_id=shift_id,
            plan_mdl=data.get("plan_mdl", 0),
            z_report_mdl=data.get("z_report_mdl", 0),
            fuel_lei=data.get("fuel_lei", 0),
            total_km=data.get("total_km", 0),
            qr_balance=qr_balance,
            notes=data.get("notes", ""),
        )
        return jsonify({"ok": True, "qr_balance": qr_balance})

    elif action == "update":
        shift = db.get_current_shift()
        if not shift:
            return jsonify({"error": "Нет открытой смены"}), 404
        db.update_shift_data(
            shift_id=shift["id"],
            plan_mdl=data.get("plan_mdl"),
            z_report_mdl=data.get("z_report_mdl"),
            fuel_lei=data.get("fuel_lei"),
            total_km=data.get("total_km"),
            notes=data.get("notes"),
        )
        return jsonify({"ok": True})

    return jsonify({"error": "Неизвестное действие"}), 400


@app.route("/api/shifts")
def api_shifts():
    shifts = db.get_shifts()
    for s in shifts:
        s["stats"] = db.get_shift_stats(s["id"])
        if s["closed_at"] is None and s["total_km"] == 0:
            s["total_km"] = s["stats"]["distance_km"]
    return jsonify({"shifts": shifts})


@app.route("/api/shift/<int:shift_id>")
def api_shift_detail(shift_id):
    shift = db.get_shift(shift_id)
    if not shift:
        return jsonify({"error": "Смена не найдена"}), 404

    taxi = TaxiDb()
    for o in shift.get("orders", []):
        try:
            detail = json.loads(o.get("details_json", "{}"))
            addr = detail.get("Order", {}).get("Address", {})
            street = taxi.get_street_name(addr.get("StreetId", 0))
            settlement = taxi.get_settlement_name(addr.get("SettlementId", 0))
            o["address"] = f"{settlement}, {street}, {addr.get('House', '')}"
        except:
            o["address"] = "—"

    return jsonify(shift)

@app.route("/api/shift/<int:shift_id>/delete", methods=["POST"])
def api_delete_shift(shift_id):
    shift = db.get_shift(shift_id)
    if not shift:
        return jsonify({"error": "Смена не найдена"}), 404
    db.delete_shift(shift_id)
    return jsonify({"ok": True})

#-----------------------------------------------------------
# Баланс QR
#-----------------------------------------------------------

@app.route("/api/qr-balance")
def api_qr_balance():
    """Возвращает Баланс QR из GetCarNicknameOverviewInfo."""
    auth = LetzAuth(access_token=get_access_token(), device_id=get_device_id())
    session_id = auth.login()
    if not session_id:
        return jsonify({"qr_balance": "0"})
    api = LetzApi(session_id)
    try:
        data = api.fetch_car_nickname_overview()
        records = data.get("Info", {}).get("InfoRecords", [])
        for r in records:
            if r.get("Name") == "Баланс QR":
                return jsonify({"qr_balance": r.get("Value", "0")})
        return jsonify({"qr_balance": "0"})
    except:
        return jsonify({"qr_balance": "0"})

# ----------------------------------------------------------
# Бухгалтерия
# ----------------------------------------------------------

@app.route("/accounting")
def accounting_page():
    return render_template("accounting.html", app_name=APP_NAME, app_version=APP_VERSION)


@app.route("/payment")
def payment_page():
    return render_template("payment.html", app_name=APP_NAME, app_version=APP_VERSION)


@app.route("/api/accounting", methods=["GET", "POST"])
def api_accounting():
    if request.method == "GET":
        rows = db.get_accounting()
        total = db.get_accounting_total()
        return jsonify({"rows": rows, "total_balance": total})

    data = request.get_json()
    db.save_accounting(
        shift_id=data.get("shift_id"),
        plan_mdl=data.get("plan_mdl", 0),
        fuel_lei=data.get("fuel_lei", 0),
        z_percent=data.get("z_percent", 0),
        paid_cash=data.get("paid_cash", 0),
        paid_balance=data.get("paid_balance", 0),
        paid_qr=data.get("paid_qr", 0),
        notes=data.get("notes", ""),
    )
    return jsonify({"ok": True})

# ----------------------------------------------------------
# Запуск сервера
# ----------------------------------------------------------

if __name__ == "__main__":
    print("=" * 40)
    print("🚖 Letz Driver Stats")
    print(f"   http://127.0.0.1:{SERVER_PORT}")
    print("=" * 40)
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=SERVER_DEBUG)