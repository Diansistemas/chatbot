# Reproduce el error del chat ("buenos dias" -> "Ha habido un error")
import requests

BASE = "http://localhost:8000"
CHAT = f"{BASE}/chat/"
s = requests.Session()

# 1) GET del widget para obtener el CSRF token
r = s.get(CHAT, timeout=30)
print("GET /chat/", r.status_code)
csrf = s.cookies.get("csrftoken")
print("csrf:", csrf)

# 2) POST usuario (crea conversacion)
r = s.post(CHAT, data={
    "accion": "usuario",
    "texto": "buenos dias",
    "conversacion": "",
    "csrfmiddlewaretoken": csrf,
}, headers={"Referer": CHAT}, timeout=60)
print("POST usuario:", r.status_code)
print(r.text[:500])
if r.status_code != 200:
    raise SystemExit("fallo en usuario")

data = r.json()
mid = data["mensaje_id"]
conv = data["conversacion"]

# 3) POST bot
r = s.post(CHAT, data={
    "accion": "bot",
    "mensaje_id": mid,
    "conversacion": conv,
    "csrfmiddlewaretoken": csrf,
}, headers={"Referer": CHAT}, timeout=300)
print("POST bot:", r.status_code)
print(r.text[:800])
