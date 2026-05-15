import requests, json

resp = requests.get(
    "http://letz99.from-md.com/ts.mobilerest/login",
    params={
        "password": "",
        "appVersion": "3.9.17",
        "AccessToken": "4D32AA8B768B4572AB819076F5901E050746",
        "deviceId": "4340",
    },
    headers={"Host": "letz99.from-md.com", "User-Agent": "okhttp/4.12.0"},
    timeout=30,
)

data = resp.json()
print("🔑 Все ключи в ответе логина:")
for key in data:
    val = data[key]
    if isinstance(val, (dict, list)):
        print(f"   {key}: {type(val).__name__} (вложенный)")
    else:
        print(f"   {key}: {val}")