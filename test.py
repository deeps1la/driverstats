"""
Подключение к SignalR Letz и получение рейтинга
"""
from signalrcore.hub_connection_builder import HubConnectionBuilder
import json
import requests
import time

LOGIN = "N925"
PASSWORD = "68076"

print("=" * 60)
print("📡 Подключение к SignalR Letz")
print("=" * 60)

# postLogin
resp = requests.post(
    "https://driversauth.letz.md/api/driver/Login",
    json={"Login": LOGIN, "Password": PASSWORD, "MobileDeviceId": LOGIN, "AppVersion": "3.9.17"},
    headers={"Content-Type": "application/json", "User-Agent": "okhttp/4.12.0"},
    timeout=30
)
its_token = resp.json()["AccessToken"]

# Profiles
resp = requests.post(
    "https://driversauth.letz.md/api/driver/Profiles",
    json={"AccessToken": its_token},
    headers={"Content-Type": "application/json", "User-Agent": "okhttp/4.12.0"},
    timeout=30
)
identity = resp.json()["Items"][0]["Identity"].strip()

# NewSession
resp = requests.post(
    "https://driversauth.letz.md/api/driver/NewSession",
    json={"ProfileIdentity": identity, "MetaData": "", "AccessToken": its_token},
    headers={"Content-Type": "application/json", "User-Agent": "okhttp/4.12.0"},
    timeout=30
)
data = resp.json()
access_token = data["AccessToken"]
api_url = data.get("ApiUrl", "http://letz99.from-md.com:80").rstrip("/").replace(":80", "")
v_api_url = data.get("VApiUrl", "https://drivers.letz.md")

# Логин на старом API → получаем SessionId
resp = requests.get(
    f"{api_url}/ts.mobilerest/login",
    params={"password": "", "appVersion": "3.9.17", "AccessToken": access_token, "deviceId": "4340"},
    headers={"Host": "letz99.from-md.com", "User-Agent": "okhttp/4.12.0"},
    timeout=30
)
session_id = resp.json()["SessionId"]

print(f"🪪 SessionId: {session_id[:20]}...")
print(f"🌐 VApiUrl: {v_api_url}")

# ============================================================
# Подключаемся к SignalR
# ============================================================

hub_url = f"{v_api_url}/v1/driver?access_token={session_id}"

def on_profile(data):
    print("\n⭐ ПОЛУЧЕН ПРОФИЛЬ (РЕЙТИНГ):")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    if isinstance(data, list) and len(data) > 0:
        profile = data[0]
        rating = profile.get("RatingCalculated", "?")
        motivation = profile.get("Motivation", "?")
        print(f"\n★ Рейтинг: {rating}")
        print(f"👑 Корона: {motivation}")

def on_new_order(data):
    print("\n📦 Новый заказ:")
    print(json.dumps(data, indent=2, ensure_ascii=False)[:300])

def on_open():
    print("\n✅ Подключено к SignalR!")

def on_close():
    print("\n🔌 Соединение закрыто")

def on_error(data):
    print(f"\n❌ Ошибка SignalR: {data}")

hub = HubConnectionBuilder()\
    .with_url(hub_url, options={"verify_ssl": False})\
    .build()

hub.on("Profile", on_profile)
hub.on("NewOrder", on_new_order)
hub.on_open(on_open)
hub.on_close(on_close)
hub.on_error(on_error)

print("\n📡 Подключаюсь...")
hub.start()

print("⏳ Ожидаю события (30 сек)...")
time.sleep(30)

hub.stop()
print("\n✅ Готово")