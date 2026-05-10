"""
Модуль расчётов.
Haversine, фильтрация транзакций, агрегация статистики.
"""

from math import radians, sin, cos, sqrt, atan2

# ----------------------------------------------------------
# Константы
# ----------------------------------------------------------

ORDER_DESCRIPTIONS = {"Numerar", "QR card", "Оплата заказа"}

CLASS_TYPES = {
    10: "STD",
    20: "UNIV",
    40: "CONF",
    100: "PREM",
}

# ----------------------------------------------------------
# Haversine
# ----------------------------------------------------------

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# ----------------------------------------------------------
# Фильтрация
# ----------------------------------------------------------

def is_order(transaction: dict) -> bool:
    t = transaction.get("Type")
    desc = transaction.get("Description", "")
    if t == 10:
        return True
    if t is None and desc in ORDER_DESCRIPTIONS:
        return True
    return False

def is_commission(transaction: dict) -> bool:
    t = transaction.get("Type")
    article = transaction.get("Article", "")
    if t == "Iesire":
        return False
    return t == 20

# ----------------------------------------------------------
# Извлечение расстояния
# ----------------------------------------------------------

def extract_distance(detail: dict) -> float:
    try:
        order = detail.get("Order", {})
        addr = order.get("Address", {})
        routes = order.get("Routes", [])
        if addr.get("Latitude") and routes and routes[0].get("Latitude"):
            return haversine_distance(
                addr["Latitude"], addr["Longitude"],
                routes[0]["Latitude"], routes[0]["Longitude"],
            )
    except Exception as e:
        print(f"[CALC] ⚠️ Ошибка расстояния: {e}")
    return 0.0

# ----------------------------------------------------------
# Класс авто
# ----------------------------------------------------------

def extract_class(detail: dict) -> str:
    ct = detail.get("Order", {}).get("ClassType", 0)
    return CLASS_TYPES.get(ct, f"Тип {ct}")

# ----------------------------------------------------------
# Статистика
# ----------------------------------------------------------

def calculate_stats(transactions: list) -> dict:
    orders = 0
    income = 0.0
    commission = 0.0
    for tx in transactions:
        if is_order(tx):
            orders += 1
            income += tx.get("Value", 0)
        elif is_commission(tx):
            commission += abs(tx.get("Value", 0))
    return {
        "orders": orders,
        "income": round(income, 2),
        "commission": round(commission, 2),
        "net_profit": round(income - commission, 2),
    }