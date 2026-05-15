"""
Модуль авторизации в API Letz.
Получает SessionId по AccessToken.
Маскируется под Android-приложение.
"""

import requests
from config import LETZ_BASE_URL, LETZ_APP_VERSION


class LetzAuth:
    """Управление входом в Letz API."""

    def __init__(self, access_token: str = "", device_id: str = ""):
        self.base_url = LETZ_BASE_URL
        self.access_token = access_token
        self.device_id = device_id
        self.app_version = LETZ_APP_VERSION

    def login(self) -> str | None:
        try:
            response = requests.get(
                f"{self.base_url}/login",
                params={
                    "password": "",
                    "appVersion": self.app_version,
                    "AccessToken": self.access_token,
                    "deviceId": self.device_id,
                },
                headers={
                    "Host": "letz99.from-md.com",
                    "Connection": "Keep-Alive",
                    "Accept-Encoding": "gzip",
                    "User-Agent": "okhttp/4.12.0",
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            status = data.get("Header", {}).get("Status")

            if status == 10:
                session_id = data.get("SessionId")
                print(f"[AUTH] ✅ Успешный вход")
                
                # Маскируемся под устройство
                self._report_device(session_id)
                
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

    def _report_device(self, session_id):
        """Отправляет данные устройства для маскировки."""
        try:
            requests.get(
                f"{self.base_url}/ReportDeviceHardware",
                params={
                    "deviceScreenSize": "1080x2296",
                    "deviceModel": "MI_9T_Pro",
                    "sessionId": session_id,
                    "deviceOSVersion": "10.0",
                },
                headers={
                    "Host": "letz99.from-md.com",
                    "Connection": "Keep-Alive",
                    "Accept-Encoding": "gzip",
                    "User-Agent": "okhttp/4.12.0",
                },
                timeout=10,
            )
            print("[AUTH] 📱 Устройство зарегистрировано (MI 9T Pro / Android 10)")
        except Exception as e:
            print(f"[AUTH] ⚠️ Не удалось отправить данные устройства: {e}")

    def get_driver_info(self) -> dict:
        try:
            response = requests.get(
                f"{self.base_url}/login",
                params={
                    "password": "",
                    "appVersion": self.app_version,
                    "AccessToken": self.access_token,
                    "deviceId": self.device_id,
                },
                headers={
                    "Host": "letz99.from-md.com",
                    "Connection": "Keep-Alive",
                    "Accept-Encoding": "gzip",
                    "User-Agent": "okhttp/4.12.0",
                },
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[AUTH] ❌ Ошибка получения данных: {e}")
            return {}