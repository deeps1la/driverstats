"""
Модуль авторизации в API Letz.
Получает SessionId по AccessToken.
Поддерживает автоматическое обновление токена через ITS API.
"""

import requests
from config import LETZ_BASE_URL, LETZ_APP_VERSION, ITS_API_URL


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
                self._report_device(session_id)
                return session_id
            else:
                msg = data.get("Header", {}).get("Msg", data.get("Message", "Неизвестная ошибка"))
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


def refresh_access_token(login: str, password: str, device_id: str = "4340") -> str | None:
    """
    Получает новый AccessToken через ITS API.
    Цепочка: postLogin → getDriverProfiles → getNewSession
    """
    print("[TOKEN] 🔄 Запуск обновления токена...")
    
    # Шаг 1: postLogin
    print("[TOKEN] Шаг 1: postLogin...")
    try:
        resp = requests.post(
            f"{ITS_API_URL}/Login",
            json={
                "Login": login,
                "Password": password,
                "MobileDeviceId": login,
                "AppVersion": LETZ_APP_VERSION,
            },
            headers={
                "Content-Type": "application/json",
                "User-Agent": "okhttp/4.12.0",
            },
            timeout=30,
        )
        data = resp.json()
        if data.get("Header", {}).get("Status") != 10:
            print(f"[TOKEN] ❌ postLogin failed: {data.get('Header', {}).get('Msg', '')}")
            return None
        its_token = data.get("AccessToken")
        print(f"[TOKEN] ✅ ITS токен получен")
    except Exception as e:
        print(f"[TOKEN] ❌ postLogin error: {e}")
        return None

    # Шаг 2: getDriverProfiles
    print("[TOKEN] Шаг 2: getDriverProfiles...")
    try:
        resp = requests.post(
            f"{ITS_API_URL}/Profiles",
            json={"AccessToken": its_token},
            headers={
                "Content-Type": "application/json",
                "User-Agent": "okhttp/4.12.0",
            },
            timeout=30,
        )
        data = resp.json()
        if data.get("Header", {}).get("Status") != 10:
            print(f"[TOKEN] ❌ Profiles failed")
            return None
        profiles = data.get("Items", [])
        if not profiles:
            print("[TOKEN] ❌ Нет профилей")
            return None
        identity = profiles[0].get("Identity", "").strip()
        print(f"[TOKEN] ✅ Профиль: {identity}")
    except Exception as e:
        print(f"[TOKEN] ❌ Profiles error: {e}")
        return None

    # Шаг 3: getNewSession
    print("[TOKEN] Шаг 3: getNewSession...")
    try:
        resp = requests.post(
            f"{ITS_API_URL}/NewSession",
            json={
                "ProfileIdentity": identity,
                "MetaData": "",
                "AccessToken": its_token,
            },
            headers={
                "Content-Type": "application/json",
                "User-Agent": "okhttp/4.12.0",
            },
            timeout=30,
        )
        data = resp.json()
        if data.get("Header", {}).get("Status") != 10:
            print(f"[TOKEN] ❌ NewSession failed")
            return None
        new_token = data.get("AccessToken")
        print(f"[TOKEN] ✅ Новый AccessToken получен: {new_token[:10]}...")
        return new_token
    except Exception as e:
        print(f"[TOKEN] ❌ NewSession error: {e}")
        return None