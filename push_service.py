import json
from pywebpush import webpush
from config import VAPID_CLAIMS, VAPID_PRIVATE_KEY

def enviar_push(endpoint, p256dh, auth, titulo, mensagem):

    return webpush(
        subscription_info={
            "endpoint": endpoint,
            "keys": {
                "p256dh": p256dh,
                "auth": auth
            }
        },
        data=json.dumps({
            "title": titulo,
            "body": mensagem
        }),
        vapid_private_key=VAPID_PRIVATE_KEY,
        vapid_claims=VAPID_CLAIMS
    )
