"""
Letz Driver Stats — точка входа.
Запуск Flask-сервера, маршруты, связь фронтенда с бэкендом.
"""
APP_NAME = "Letz Driver Stats"
APP_VERSION = "1.0"

# ----------------------------------------------------------
# Импорты
# ----------------------------------------------------------

from flask import Flask, render_template, jsonify, request        # Flask: сервер, HTML, JSON-ответы
from config import SERVER_HOST, SERVER_PORT, SERVER_DEBUG  # Настройки из config.py
from backend.auth import LetzAuth                          # Авторизация в Letz
from backend.api_letz import LetzApi                       # Запросы к Letz API
from backend.calculator import (                           # Расчёты
    is_order,            # Проверка: это заказ или комиссия?
    extract_distance,    # Достаёт расстояние из деталей заказа
    extract_class,       # Достаёт класс авто (Стандарт/Комфорт/Премиум)
    calculate_stats,     # Суммирует заказы, доход, комиссию
)
from backend.database import Database                      # База данных SQLite
from datetime import datetime                              # Для даты последнего обновления
from config import LETZ_ACCESS_TOKEN
import json
from config import DATABASE_PATH


# ----------------------------------------------------------
# Создание приложения
# ----------------------------------------------------------

app = Flask(
    __name__,
    template_folder="frontend/templates",   # Где лежат HTML-шаблоны
    static_folder="frontend/static",        # Где лежат CSS и JS
)

# Дата, с которой начинаем собирать заказы (игнорируем всё, что раньше)
START_DATE = "2026-04-20"

# Экземпляр базы данных (один на всё приложение)
db = Database()

# ----------------------------------------------------------
# Маршруты
# ----------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", app_name=APP_NAME, app_version=APP_VERSION)

@app.route("/api/balance")
def api_balance():
    """Возвращает текущий баланс через прямой запрос к Letz API."""
    auth = LetzAuth()
    session_id = auth.login()
    if not session_id:
        return jsonify({"balance": 0})
    
    api = LetzApi(session_id)
    try:
        transactions_data = api.fetch_all_transactions()
        balance = transactions_data.get("CurrentBalance", 0)
        return jsonify({"balance": balance})
    except:
        return jsonify({"balance": 0})

@app.route("/settings")
def settings_page():
    """Страница настроек."""
    return render_template("settings.html")


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    global START_DATE, APP_NAME, APP_VERSION, LETZ_ACCESS_TOKEN

    if request.method == "GET":
        return jsonify({
            "start_date": START_DATE,
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
            "access_token": LETZ_ACCESS_TOKEN,
        })

    # POST
    data = request.get_json()
    if "start_date" in data:
        START_DATE = data["start_date"]
    if "app_name" in data:
        APP_NAME = data["app_name"]
    if "app_version" in data:
        APP_VERSION = data["app_version"]
    if "access_token" in data:
        LETZ_ACCESS_TOKEN = data["access_token"]
        auth = LetzAuth()
        auth.access_token = LETZ_ACCESS_TOKEN

    return jsonify({"ok": True})

import os
import time
import requests as req

@app.route("/api/system-info")
def api_system_info():
    """Возвращает системную информацию."""
    info = {
        "letz_connected": False,
        "letz_ping": 0,
        "db_size": "0 KB",
        "app_size": "0 KB",
    }

    # Проверка связи с Letz
    try:
        start = time.time()
        resp = req.get("http://letz99.from-md.com/ts.mobilerest/login", timeout=5)
        end = time.time()
        info["letz_ping"] = round((end - start) * 1000, 1)  # мс
        info["letz_connected"] = resp.status_code < 500
    except:
        info["letz_connected"] = False
        info["letz_ping"] = 0

    # Размер БД
    db_path = DATABASE_PATH
    if os.path.exists(db_path):
        size_bytes = os.path.getsize(db_path)
        if size_bytes < 1024:
            info["db_size"] = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            info["db_size"] = f"{size_bytes / 1024:.1f} KB"
        else:
            info["db_size"] = f"{size_bytes / (1024 * 1024):.1f} MB"

    # Размер приложения (текущая папка)
    app_path = "."
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(app_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    if total_size < 1024 * 1024:
        info["app_size"] = f"{total_size / 1024:.1f} KB"
    else:
        info["app_size"] = f"{total_size / (1024 * 1024):.1f} MB"

    return jsonify(info)

@app.route("/orders")
def orders_page():
    """Страница со списком всех заказов."""
    return render_template("orders.html")


@app.route("/api/orders")
def api_orders():
    """API: отдаёт список всех заказов из БД."""
    orders = db.get_orders()
    return jsonify({"orders": orders})

@app.route("/api/order/<int:order_id>")
def api_order_detail(order_id):
    """Возвращает детали одного заказа."""
    orders = db.get_orders()
    for o in orders:
        if o["id"] == order_id:
            detail = json.loads(o.get("details_json", "{}"))
            
            # Расшифровываем SettlementId и StreetId через taxi.db
            from backend.api_letz import TaxiDb
            taxi = TaxiDb()
            
            addr = detail.get("Order", {}).get("Address", {})
            street_id = addr.get("StreetId", 0)
            settlement_id = addr.get("SettlementId", 0)
            
            street_name = taxi.get_street_name(street_id)
            settlement_name = taxi.get_settlement_name(settlement_id)
            
            return jsonify({
                "id": o["id"],
                "date": o["date"],
                "amount": o["amount"],
                "commission": o["commission"],
                "distance": o["distance_km"],
                "class_type": o["class_type"],
                "payment_type": o["payment_type"],
                "address": f"{settlement_name}, {street_name}, {addr.get('House', '')}",
                "routes": detail.get("Order", {}).get("Routes", []),
            })
    
    return jsonify({"error": "Заказ не найден"}), 404

@app.route("/api/stats")
def api_stats():
    today = datetime.now().strftime("%Y-%m-%d")

    auth = LetzAuth()
    session_id = auth.login()
    if not session_id:
        return jsonify({"error": "Ошибка авторизации"}), 500

    api = LetzApi(session_id)

    try:
        transactions_data = api.fetch_all_transactions()
    except:
        return jsonify({"error": "Ошибка API"}), 500

    balance = transactions_data.get("CurrentBalance", 0)

    # Сохраняем новые заказы в БД
    all_transactions = []
    for day in transactions_data.get("Data", []):
        day_str = day.get("Day", "")[:10]
        for tx in day.get("Transactions", []):
            tx["_day"] = day_str
            all_transactions.append(tx)

    all_transactions.sort(key=lambda x: x.get("Id", 0), reverse=True)

    new_count = 0
    for tx in all_transactions:
        tx_date = tx.get("Time", tx.get("_day", ""))[:10]
        if tx_date < START_DATE:
            continue
        if tx.get("Type") == 20:
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
            )
            new_count += 1
            print(f"  ✅ Новый заказ #{tx['Id']}: {dist:.1f} км, {tx['Value']} MDL")

        except Exception as e:
            print(f"  ⚠️ Ошибка заказа #{tx['Id']}: {e}")

    print(f"🆕 Загружено новых заказов: {new_count}")

    # Статистика за сегодня + сравнение
    all_days = {}
    for day in transactions_data.get("Data", []):
        day_str = day.get("Day", "")[:10]
        day_transactions = day.get("Transactions", [])
        day_stats = calculate_stats(day_transactions)
        all_days[day_str] = day_stats

    today_stats = all_days.get(today, {"orders": 0, "income": 0, "commission": 0, "net_profit": 0, "distance_km": 0})
    yesterday_stats = {"orders": 0, "income": 0, "commission": 0, "net_profit": 0, "distance_km": 0}
    sorted_days = sorted([d for d in all_days.keys() if d < today], reverse=True)
    for d in sorted_days:
        if all_days[d]["orders"] > 0:
            yesterday_stats = all_days[d]
            break

    today_db = db.get_total_stats(from_date=today, to_date=today)
    today_stats["distance_km"] = today_db["distance_km"]

    return jsonify({
        "today": today_stats,
        "yesterday": yesterday_stats,
        "balance": balance,
        "last_update": datetime.now().strftime("%d.%m.%Y %H:%M"),
    })
    """Статистика за сегодня + сравнение с предыдущим днём с заказами."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Авторизация и получение данных из Letz
    auth = LetzAuth()
    session_id = auth.login()
    if not session_id:
        return jsonify({"error": "Ошибка авторизации"}), 500

    api = LetzApi(session_id)

    try:
        transactions_data = api.fetch_all_transactions()
    except:
        return jsonify({"error": "Ошибка API"}), 500

    balance = transactions_data.get("CurrentBalance", 0)

    # Собираем статистику по всем дням из ответа Letz
    all_days = {}
    for day in transactions_data.get("Data", []):
        day_str = day.get("Day", "")[:10]
        day_transactions = day.get("Transactions", [])
        day_stats = calculate_stats(day_transactions)

        day_distance = 0.0
        for tx in day_transactions:
            if is_order(tx):
                pass  # расстояние уже в БД

        all_days[day_str] = {
            "orders": day_stats["orders"],
            "income": day_stats["income"],
            "commission": day_stats["commission"],
            "net_profit": day_stats["net_profit"],
            "distance_km": 0,  # Заполним из БД
        }

    # Статистика за сегодня
    today_stats = all_days.get(today, {"orders": 0, "income": 0, "commission": 0, "net_profit": 0, "distance_km": 0})

    # Ищем последний день с заказами ДО сегодня
    yesterday_stats = {"orders": 0, "income": 0, "commission": 0, "net_profit": 0, "distance_km": 0}
    sorted_days = sorted([d for d in all_days.keys() if d < today], reverse=True)

    for d in sorted_days:
        if all_days[d]["orders"] > 0:
            yesterday_stats = all_days[d]
            break

    # Километраж из БД
    today_db = db.get_total_stats(from_date=today, to_date=today)
    today_stats["distance_km"] = today_db["distance_km"]

    # Ищем последний день с заказами для сравнения
    last_active_day = today
    sorted_days = sorted([d for d in all_days.keys() if d < today], reverse=True)
    for d in sorted_days:
        if all_days[d]["orders"] > 0:
            last_active_day = d
            break

    yesterday_db = db.get_total_stats(from_date=last_active_day, to_date=last_active_day)
    yesterday_stats["distance_km"] = yesterday_db.get("distance_km", 0)

    return jsonify({
        "today": today_stats,
        "yesterday": yesterday_stats,
        "balance": balance,
        "last_update": datetime.now().strftime("%d.%m.%Y %H:%M"),
    })

@app.route("/reports")
def reports_page():
    """Страница отчётов."""
    return render_template("reports.html")


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
# Запуск сервера
# ----------------------------------------------------------

if __name__ == "__main__":
    print("=" * 40)
    print("🚖 Letz Driver Stats")
    print(f"   http://127.0.0.1:{SERVER_PORT}")
    print("=" * 40)
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=SERVER_DEBUG)