import time
from app import app, enviar_alertas_vencimento

while True:
    try:
        with app.app_context():
            print("Verificando dívidas para notificação...")
            enviar_alertas_vencimento()

    except Exception as erro:
        print("Erro no agendador:", erro)

    print("Próxima verificação em 1 hora.")
    time.sleep(3600)