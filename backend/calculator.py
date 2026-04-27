"""
Модуль расчётов.
Haversine, фильтрация транзакций, агрегация статистики.
"""

from math import radians, sin, cos, sqrt, atan2

# ----------------------------------------------------------
# Константы
# ----------------------------------------------------------

# Типы транзакций, которые считаются заказом (доход)
ORDER_DESCRIPTIONS = {"Numerar", "QR card", "Оплата заказа"}

# Классы автомобилей
CLASS_TYPES = {
    10: "STD",
    20: "UNIV",
    40: "CONF",
    100: "PREM",
}

# ----------------------------------------------------------
# Haversine (расстояние по прямой)
# ----------------------------------------------------------

def haversine_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """
    Расстояние между двумя точками в километрах.

    Args:
        lat1, lon1: координаты начала.
        lat2, lon2: координаты конца.

    Returns:
        Расстояние в км.
    """
    R = 6371.0

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c

# ----------------------------------------------------------
# Фильтрация транзакций
# ----------------------------------------------------------

def is_order(transaction: dict) -> bool:
    """
    Является ли транзакция оплаченным заказом.

    Args:
        transaction: одна транзакция из списка.

    Returns:
        True если это доходный заказ.
    """
    t = transaction.get("Type")
    desc = transaction.get("Description", "")

    if t == 10:
        return True
    if t is None and desc in ORDER_DESCRIPTIONS:
        return True
    return False

def is_commission(transaction: dict) -> bool:
    """
    Является ли транзакция комиссией.

    Args:
        transaction: одна транзакция из списка.

    Returns:
        True если это комиссия.
    """
    return transaction.get("Type") == 20

# ----------------------------------------------------------
# Извлечение расстояния из деталей заказа
# ----------------------------------------------------------

def extract_distance(detail: dict) -> float:
    """
    Вычисляет расстояние по координатам из деталей заказа.

    Args:
        detail: JSON от /TransactionDetails.

    Returns:
        Расстояние в км или 0.0.
    """
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
# Извлечение класса авто
# ----------------------------------------------------------

def extract_class(detail: dict) -> str:
    """
    Возвращает название класса автомобиля.

    Args:
        detail: JSON от /TransactionDetails.

    Returns:
        Название класса (Стандарт/Комфорт/Премиум).
    """
    ct = detail.get("Order", {}).get("ClassType", 0)
    return CLASS_TYPES.get(ct, f"Тип {ct}")

# ----------------------------------------------------------
# Агрегация статистики
# ----------------------------------------------------------

def calculate_stats(transactions: list) -> dict:
    """
    Подсчитывает сводку по списку транзакций.

    Args:
        transactions: плоский список всех транзакций.

    Returns:
        Словарь с ключами: orders, income, commission.
    """
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