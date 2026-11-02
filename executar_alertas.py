from config import VAPID_PRIVATE_KEY
from py_vapid import Vapid

print("Chave privada carregada:", bool(VAPID_PRIVATE_KEY))
print("Começa com cabeçalho PEM:", VAPID_PRIVATE_KEY.startswith("-----BEGIN"))
print("Termina com rodapé PEM:", VAPID_PRIVATE_KEY.strip().endswith("-----END PRIVATE KEY-----"))

Vapid.from_pem(VAPID_PRIVATE_KEY.encode("utf-8"))
print("Chave PEM validada!")

from app import app, enviar_alertas_vencimento

with app.app_context():
    enviados = enviar_alertas_vencimento()
    print(f"Notificações enviadas: {enviados}")