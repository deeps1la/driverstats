"""
Модуль авторизации в API Letz.
Получает SessionId по AccessToken.
"""

import requests
from config import LETZ_BASE_URL, LETZ_ACCESS_TOKEN, LETZ_DEVICE_ID, LETZ_APP_VERSION


class LetzAuth:
    """Управление входом в Letz API."""

    def __init__(self):
        self.base_url = LETZ_BASE_URL
        self.access_token = LETZ_ACCESS_TOKEN
        self.device_id = LETZ_DEVICE_ID
        self.app_version = LETZ_APP_VERSION

    def login(self) -> str | None:
        """Авторизация и получение SessionId."""
        try:
            response = requests.get(
                f"{self.base_url}/login",
                params={
                    "password": "",
                    "appVersion": self.app_version,
                    "AccessToken": self.access_token,
                    "deviceId": self.device_id,
                },
                headers={"Host": "letz99.from-md.com"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            status = data.get("Header", {}).get("Status")
            if status == 10:
                session_id = data.get("SessionId")
                print(f"[AUTH] ✅ Успешный вход")
                return session_id
            else:
                msg = data.get("Message", "Неизвестная ошибка")
                print(f"[AUTH] ❌ Ошибка: {msg}")
                return None
        except requests.RequestException as e:
            print(f"[AUTH] ❌ Сеть: {e}")
            return None
        except Exception as e:
            print(f"[AUTH] ❌ Ошибка: {e}")
            return None

    def get_driver_info(self) -> dict:
        """Получение информации о водителе."""
        try:
            response = requests.get(
                f"{self.base_url}/login",
                params={
                    "password": "",
                    "appVersion": self.app_version,
                    "AccessToken": self.access_token,
                    "deviceId": self.device_id,
                },
                headers={"Host": "letz99.from-md.com"},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[AUTH] ❌ Ошибка получения данных: {e}")
            return {}