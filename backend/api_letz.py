"""
Модуль для работы с API Letz.
Получение транзакций, деталей заказов, настроек, сообщений.
"""

import requests
from datetime import datetime, timedelta
from config import LETZ_BASE_URL
import sqlite3
import os

class LetzApi:
    """Клиент для API Letz."""

    def __init__(self, session_id: str):
        self.base_url = LETZ_BASE_URL
        self.session_id = session_id
        self.headers = {"Host": "letz99.from-md.com"}

    # ----------------------------------------------------------
    # Транзакции
    # ----------------------------------------------------------
    def fetch_all_transactions(self) -> dict:
        """
        Загружает все доступные транзакции (максимально глубоко).
        Letz отдаёт только последние 7 дней, но запрашиваем с запасом в 30 дней.
        """
        from datetime import datetime, timedelta

        end = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000+03:00")
        start = (datetime.now() - timedelta(days=30)).strftime(
            "%Y-%m-%dT%H:%M:%S.000+03:00"
        )

        response = requests.post(
            f"{self.base_url}/transactions",
            json={
                "AffectsBalance": False,
                "EndDate": end,
                "SessionId": self.session_id,
                "StartDate": start,
            },
            headers={
                "Content-Type": "application/json; charset=UTF-8",
                **self.headers,
            },
            timeout=30,
        )
        return response.json()

    def fetch_transactions(self, days: int = 7) -> dict:
        """
        Получение списка транзакций за N дней.

        Args:
            days: за сколько дней (по умолчанию 7).

        Returns:
            JSON-ответ с транзакциями.
        """
        end = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000+03:00")
        start = (datetime.now() - timedelta(days=days)).strftime(
            "%Y-%m-%dT%H:%M:%S.000+03:00"
        )

        response = requests.post(
            f"{self.base_url}/transactions",
            json={
                "AffectsBalance": False,
                "EndDate": end,
                "SessionId": self.session_id,
                "StartDate": start,
            },
            headers={
                "Content-Type": "application/json; charset=UTF-8",
                **self.headers,
            },
            timeout=30,
        )
        return response.json()

    # ----------------------------------------------------------
    # Детали заказа
    # ----------------------------------------------------------

    def fetch_transaction_detail(self, transaction_id: int) -> dict:
        """
        Детали транзакции: координаты, маршрут, класс авто.

        Args:
            transaction_id: ID транзакции.

        Returns:
            JSON с координатами и маршрутом.
        """
        response = requests.get(
            f"{self.base_url}/TransactionDetails",
            params={
                "sessionId": self.session_id,
                "id": transaction_id,
            },
            headers=self.headers,
            timeout=30,
        )
        return response.json()

    # ----------------------------------------------------------
    # Настройки профиля
    # ----------------------------------------------------------

    def fetch_settings(self) -> dict:
        """
        Профиль водителя, тарифы, рейтинг, график.

        Returns:
            JSON с настройками.
        """
        response = requests.get(
            f"{self.base_url}/GetSettings",
            params={"sessionId": self.session_id},
            headers=self.headers,
            timeout=30,
        )
        return response.json()

    # ----------------------------------------------------------
    # Системные сообщения
    # ----------------------------------------------------------

    def fetch_messages(self) -> dict:
        """
        Системные уведомления от Letz.

        Returns:
            JSON с сообщениями.
        """
        response = requests.get(
            f"{self.base_url}/GetMessages",
            params={
                "sessionId": self.session_id,
                "ts": "",
            },
            headers=self.headers,
            timeout=30,
        )
        return response.json()

    def fetch_driver_info(self) -> dict:
        """Запрашивает данные водителя (как /login)."""
        response = requests.get(
            f"{self.base_url}/login",
            params={"password": "", "appVersion": "3.9.17"},
            headers=self.headers,
            timeout=30,
        )
        return response.json()
    # Баланс QR
    def fetch_car_nickname_overview(self) -> dict:
        """Запрашивает обзорную информацию: баланс QR, заказы за сутки и др."""
        response = requests.get(
            f"{self.base_url}/GetCarNicknameOverviewInfo",
            params={"sessionId": self.session_id},
            headers=self.headers,
            timeout=30,
        )
        return response.json()
    def report_device_hardware(self, device_model="MI_9T_Pro", screen_size="1080x2296", os_version="10.0"):
        """Отправляет данные устройства — маскировка под приложение Letz."""
        response = requests.get(
            f"{self.base_url}/ReportDeviceHardware",
            params={
                "deviceScreenSize": screen_size,
                "deviceModel": device_model,
                "sessionId": self.session_id,
                "deviceOSVersion": os_version,
            },
            headers={
                "Host": "letz99.from-md.com",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip",
                "User-Agent": "okhttp/4.12.0",
            },
            timeout=30,
        )
        return response.json()        

class TaxiDb:
    """Работа с локальной базой taxi.db (улицы, города)."""
    
    def __init__(self, path="data/taxi.db"):
        self.path = path
    
    def get_street_name(self, street_id):
        if not os.path.exists(self.path):
            return f"Улица #{street_id}"
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT Name FROM Street WHERE Id = ?", (street_id,)).fetchone()
            return row[0] if row else f"Улица #{street_id}"
    
    def get_settlement_name(self, settlement_id):
        if not os.path.exists(self.path):
            return f"Город #{settlement_id}"
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT Name FROM Settlement WHERE Id = ?", (settlement_id,)).fetchone()
            return row[0] if row else f"Город #{settlement_id}"
     