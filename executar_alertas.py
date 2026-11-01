from app import app, enviar_alertas_vencimento

with app.app_context():
    enviados = enviar_alertas_vencimento()
    print(f"Notificações enviadas: {enviados}")