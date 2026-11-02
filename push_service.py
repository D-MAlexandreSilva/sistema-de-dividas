
import json
import os
from py_vapid import Vapid
from pywebpush import webpush
from config import VAPID_CLAIMS, VAPID_PRIVATE_KEY


def enviar_push(endpoint, p256dh, auth, titulo, mensagem):

    chave = VAPID_PRIVATE_KEY

    if os.path.isfile(chave):
        vapid = Vapid.from_file(chave)

    elif "-----BEGIN" in chave:
        vapid = Vapid.from_pem(chave.encode("utf-8"))

    else:
        vapid = chave

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
        vapid_private_key=vapid,
        vapid_claims=VAPID_CLAIMS
    )
