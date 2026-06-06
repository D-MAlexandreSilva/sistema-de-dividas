"""
Reset do banco de dados - apaga todos os dados mantendo a estrutura das tabelas.
Execute: python reset_banco.py
"""

import psycopg2
from config import DATABASE_URL

def reset():
    print("Conectando ao banco...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    print("Apagando dados...")

    # Ordem importa por causa das foreign keys
    cursor.execute("DELETE FROM push_notificacoes_enviadas")
    print("  ✓ push_notificacoes_enviadas limpa")

    cursor.execute("DELETE FROM push_subscriptions")
    print("  ✓ push_subscriptions limpa")

    cursor.execute("DELETE FROM gastos")
    print("  ✓ gastos limpa")

    cursor.execute("DELETE FROM dividas")
    print("  ✓ dividas limpa")

    cursor.execute("DELETE FROM usuariosap1")
    print("  ✓ usuariosap1 limpa")

    # Reinicia os IDs (SERIAL) do zero
    cursor.execute("ALTER SEQUENCE usuariosap1_id_seq RESTART WITH 1")
    cursor.execute("ALTER SEQUENCE dividas_id_seq RESTART WITH 1")
    cursor.execute("ALTER SEQUENCE gastos_id_seq RESTART WITH 1")
    cursor.execute("ALTER SEQUENCE push_subscriptions_id_seq RESTART WITH 1")
    cursor.execute("ALTER SEQUENCE push_notificacoes_enviadas_id_seq RESTART WITH 1")
    print("  ✓ Sequências reiniciadas")

    conn.commit()
    cursor.close()
    conn.close()

    print("\nBanco limpo e pronto para o cliente!")

if __name__ == "__main__":
    confirmar = input("Tem certeza? Isso apaga TODOS os dados. Digite 'sim' para confirmar: ")
    if confirmar.strip().lower() == "sim":
        reset()
    else:
        print("Cancelado.")