import psycopg2
import bcrypt
from config import DATABASE_URL
from dateutil.relativedelta import relativedelta

def conectar():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as erro:
        print("Erro ao conectar ao banco", erro)
        return None
    
def criar_tabela():
    conn = conectar()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS usuariosap1 (
                       id SERIAL PRIMARY KEY,
                       usuario TEXT UNIQUE NOT NULL,
                       senha TEXT NOT NULL,
                       saldo NUMERIC(10,2) DEFAULT 0)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS dividas (
                       id SERIAL PRIMARY KEY,
                       usuario_id INTEGER REFERENCES usuariosap1(id),
                       tipo TEXT NOT NULL,
                       descricao TEXT NOT NULL,
                       valor NUMERIC(10,2) NOT NULL,
                       parcelas_total INTEGER,
                       parcelas_pagas INTEGER DEFAULT 0,
                       vencimento DATE NOT NULL,
                       status TEXT DEFAULT 'ativa')""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS gastos (
                       id SERIAL PRIMARY KEY,
                       usuario_id INTEGER REFERENCES usuariosap1(id),
                       nome TEXT NOT NULL,
                       descricao TEXT NOT NULL,
                       valor NUMERIC(10,2) NOT NULL,
                       data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS push_subscriptions (
                       id SERIAL PRIMARY KEY,
                       usuario_id INTEGER,
                       endpoint TEXT NOT NULL,
                       p256dh TEXT NOT NULL,
                       auth TEXT NOT NULL,
                       criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );""")
        cursor.execute("""
            ALTER TABLE push_subscriptions
            ADD COLUMN IF NOT EXISTS criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """)
        cursor.execute("""
            ALTER TABLE push_subscriptions
            ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """)
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_push_subscriptions_endpoint
            ON push_subscriptions(endpoint)
        """)
        cursor.execute("""CREATE TABLE IF NOT EXISTS push_notificacoes_enviadas (
                       id SERIAL PRIMARY KEY,
                       usuario_id INTEGER NOT NULL,
                       divida_id INTEGER NOT NULL,
                       data_envio DATE NOT NULL,
                       criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       UNIQUE(usuario_id, divida_id, data_envio)
                        );""")
        
        conn.commit()
    except Exception as erro:
        print("Erro ao criar tabela:", erro)
    finally:
        try:
            cursor.close()
        except:
            pass
        if conn:
            conn.close()

def cadastrar_usuario(usuario, senha):
    conn = conectar()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuariosap1 (usuario, senha) VALUES (%s, %s) RETURNING id", (usuario, senha))
        usuario_id = cursor.fetchone()[0]
        conn.commit()
        return usuario_id
    except Exception as erro:
        print("erro ao cadastrar", erro)

        return None
    finally:
        try:
           cursor.close()
        except:
           pass
        if conn:
           conn.close()

def login(usuario, senha):
    conn = conectar()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, senha FROM usuariosap1 WHERE usuario = %s", (usuario,))
        resultado = cursor.fetchone()
        if resultado and bcrypt.checkpw(senha.encode(),resultado[1].encode()):
            return resultado[0] 
        return None
    except Exception as erro:
        print("Erro no login", erro)
        return None
    finally:
        try:
            cursor.close()
        except:
            pass
        if conn:
            conn.close()

def adicionar_divida(usuario_id, descricao, tipo, valor, parcelas_total, vencimento):
    conn = conectar()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO dividas (usuario_id, tipo, descricao, valor, parcelas_total, vencimento) VALUES (%s, %s, %s, %s, %s, %s)",
                       (usuario_id, tipo, descricao, valor, parcelas_total, vencimento))
        conn.commit()
        return True
    except Exception as erro:
        print("falha no registro!", erro)
        return False
    finally:
        try:
            cursor.close()
        except:
            pass
        if conn:
            conn.close()

def listar(usuario_id):
    conn = conectar()
    if not conn:
        return []

    try:
        cursor = conn.cursor()

        cursor.execute(""" SELECT *,
           valor * parcelas_total AS total_divida,
           valor * parcelas_pagas AS valor_pago,
           valor * (parcelas_total - parcelas_pagas) AS valor_restante,
           parcelas_total - parcelas_pagas AS parcelas_restantes
           FROM dividas WHERE usuario_id = %s AND status = 'ativa' ORDER BY vencimento""", (usuario_id,))
        
        return cursor.fetchall()

    except Exception as erro:
        print("Erro ao listar", erro)
        return []

    finally:
        try:
            cursor.close()
        except:
            pass
        if conn:
            conn.close()

def buscar_divida(id, usuario_id):
    conn = conectar()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dividas WHERE id = %s AND usuario_id = %s", (id, usuario_id,))
        return cursor.fetchone()
    except Exception as erro:
        print("Erro ao buscar divida", erro)
        return None
    finally:
        try:
            cursor.close()
        except:
            pass
        if conn:
            conn.close()

def editar_divida(divida_id, usuario_id, tipo, descricao, valor, parcelas_total, vencimento):
    conn = conectar()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dividas
            SET tipo = %s,
                descricao = %s,
                valor = %s,
                parcelas_total = %s,
                vencimento = %s
            WHERE id = %s AND usuario_id = %s
        """, (tipo, descricao, valor, parcelas_total, vencimento, divida_id, usuario_id))

        conn.commit()
        return True

    except Exception as erro:
        print("Erro ao editar dívida:", erro)
        return False
    finally:
        try:
            cursor.close()
        except:
            pass
        if conn:
            conn.close()

def excluir_divida(id, usuario_id):
    conn = conectar()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dividas WHERE id = %s AND usuario_id = %s", (id, usuario_id))
        conn.commit()
        if cursor.rowcount > 0:
            return True
        return False
    except Exception as erro:
        print("falha na exclusão", erro)
        return False
    finally:
        try:
            cursor.close()
        except:
            pass
        if conn:
            conn.close()

def pagar_parcela(divida_id, usuario_id):
    conn = conectar()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        # 1. Buscar a dívida
        cursor.execute("""
    SELECT parcelas_pagas, parcelas_total, vencimento
    FROM dividas
    WHERE id = %s AND usuario_id = %s
""", (divida_id, usuario_id))

        resultado = cursor.fetchone()

        if not resultado:
            return False

        parcelas_pagas, parcelas_total, vencimento = resultado

        # 2. Evitar passar do limite
        if parcelas_pagas >= parcelas_total:
            return False

        # 3. Incrementa parcela paga
        parcelas_pagas += 1

        # 4. Se quitou, muda status
        if parcelas_pagas == parcelas_total:
            status = "quitada"
            novo_vencimento = vencimento
        else:
            status = "ativa"
            novo_vencimento = vencimento + relativedelta(months=1)

        # 5. Atualiza no banco
        cursor.execute("""
        UPDATE dividas
        SET parcelas_pagas = %s,
        status = %s,
        vencimento = %s
    WHERE id = %s AND usuario_id = %s
""", (
    parcelas_pagas,
    status,
    novo_vencimento,
    divida_id,
    usuario_id
))

        conn.commit()
        return True

    except Exception as erro:
        print("Erro ao pagar parcela:", erro)
        return False

    finally:
        try:
            cursor.close()
        except:
            pass
        if conn:
            conn.close()

def total_mes(usuario_id):
    conn = conectar()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(SUM(valor), 0)
            FROM dividas
            WHERE usuario_id = %s
            AND status = 'ativa'
            AND DATE_TRUNC('month', vencimento) =
                DATE_TRUNC('month', CURRENT_DATE)
        """, (usuario_id,))

        return float(cursor.fetchone()[0])

    except Exception as erro:
        print("Erro ao calcular total do mês:", erro)
        return 0

    finally:
        conn.close()

def adicionar_gasto(usuario_id, nome, descricao, valor):
    conn = conectar()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO gastos
            (usuario_id, nome, descricao, valor)
            VALUES (%s, %s, %s, %s)
        """, (usuario_id, nome, descricao, valor))

        cursor.execute("""
            UPDATE usuariosap1
            SET saldo = saldo - %s
            WHERE id = %s
        """, (valor, usuario_id))

        conn.commit()
        return True

    except Exception as erro:
        print("Erro ao adicionar gasto", erro)
        return False

    finally:
        cursor.close()
        conn.close()

def buscar_saldo(usuario_id):
    conn = conectar()
    if not conn:
        return 0

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT saldo
            FROM usuariosap1
            WHERE id = %s
        """, (usuario_id,))

        resultado = cursor.fetchone()

        return resultado[0] if resultado else 0

    except Exception as erro:
        print("Erro ao buscar saldo", erro)
        return 0

    finally:
        cursor.close()
        conn.close()

def listar_gastos(usuario_id):
    conn = conectar()
    if not conn:
        return []

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT nome, descricao, valor, data_hora
            FROM gastos
            WHERE usuario_id = %s
            ORDER BY data_hora DESC
        """, (usuario_id,))

        return cursor.fetchall()

    except Exception as erro:
        print("Erro ao listar gastos", erro)
        return []

    finally:
        cursor.close()
        conn.close()

def total_gastos_dia(usuario_id):
    conn = conectar()
    if not conn:
        return 0

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(SUM(valor), 0)
            FROM gastos
            WHERE usuario_id = %s
            AND DATE(data_hora) = CURRENT_DATE
        """, (usuario_id,))

        return cursor.fetchone()[0]

    except Exception as erro:
        print("Erro ao calcular gasto diário", erro)
        return 0

    finally:
        cursor.close()
        conn.close()

def total_gastos_semana(usuario_id):
    conn = conectar()
    if not conn:
        return 0

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(SUM(valor), 0)
            FROM gastos
            WHERE usuario_id = %s
            AND data_hora >= CURRENT_DATE - INTERVAL '7 days'
        """, (usuario_id,))

        return cursor.fetchone()[0]

    except Exception as erro:
        print("Erro ao calcular gasto semanal", erro)
        return 0

    finally:
        cursor.close()
        conn.close()

def total_gastos_mes(usuario_id):
    conn = conectar()
    if not conn:
        return 0

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(SUM(valor), 0)
            FROM gastos
            WHERE usuario_id = %s
            AND DATE_TRUNC('month', data_hora)
                = DATE_TRUNC('month', CURRENT_DATE)
        """, (usuario_id,))

        return cursor.fetchone()[0]

    except Exception as erro:
        print("Erro ao calcular gasto mensal", erro)
        return 0

    finally:
        cursor.close()
        conn.close()

def grafico_gastos_mes(usuario_id):
    conn = conectar()
    if not conn:
        return []

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                EXTRACT(DAY FROM data_hora)::int AS dia,
                SUM(valor) AS total
            FROM gastos
            WHERE usuario_id = %s
              AND DATE_TRUNC('month', data_hora)
                  = DATE_TRUNC('month', CURRENT_DATE)
            GROUP BY dia
            ORDER BY dia
        """, (usuario_id,))

        return cursor.fetchall()

    except Exception as erro:
        print("Erro ao gerar gráfico:", erro)
        return []

    finally:
        cursor.close()
        conn.close()

def adicionar_saldo(usuario_id, valor):
    conn = conectar()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE usuariosap1
            SET saldo = saldo + %s
            WHERE id = %s
        """, (valor, usuario_id))

        conn.commit()
        return True

    except Exception as erro:
        print("Erro ao adicionar saldo", erro)
        return False

    finally:
        cursor.close()
        conn.close()

def salvar_push_subscription(usuario_id, endpoint, p256dh, auth):
    conn = conectar()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id
            FROM push_subscriptions
            WHERE endpoint = %s
        """, (endpoint,))

        existente = cursor.fetchone()

        if existente:
            cursor.execute("""
                UPDATE push_subscriptions
                SET usuario_id = %s,
                    p256dh = %s,
                    auth = %s,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE endpoint = %s
            """, (usuario_id, p256dh, auth, endpoint))
        else:
            cursor.execute("""
                INSERT INTO push_subscriptions (usuario_id, endpoint, p256dh, auth)
                VALUES (%s, %s, %s, %s)
            """, (usuario_id, endpoint, p256dh, auth))

        conn.commit()
        return True

    except Exception as erro:
        print("Erro ao salvar inscricao push", erro)
        return False

    finally:
        cursor.close()
        conn.close()

def listar_alertas_vencendo_hoje():
    conn = conectar()
    if not conn:
        return []

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                d.id,
                d.usuario_id,
                d.descricao,
                d.valor,
                d.vencimento,
                ps.endpoint,
                ps.p256dh,
                ps.auth
            FROM dividas d
            INNER JOIN push_subscriptions ps
                ON ps.usuario_id = d.usuario_id
            LEFT JOIN push_notificacoes_enviadas pne
                ON pne.usuario_id = d.usuario_id
               AND pne.divida_id = d.id
               AND pne.data_envio = CURRENT_DATE
            WHERE d.status = 'ativa'
              AND d.vencimento <= CURRENT_DATE + INTERVAL '1 day'
              AND pne.id IS NULL
            ORDER BY d.vencimento, d.id
        """)

        return cursor.fetchall()

    except Exception as erro:
        print("Erro ao listar alertas de vencimento:", erro)
        return []

    finally:
        try:
            cursor.close()
        except:
            pass

        if conn:
            conn.close()

def registrar_notificacao_enviada(usuario_id, divida_id):
    conn = conectar()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO push_notificacoes_enviadas (usuario_id, divida_id, data_envio)
            VALUES (%s, %s, CURRENT_DATE)
            ON CONFLICT (usuario_id, divida_id, data_envio) DO NOTHING
        """, (usuario_id, divida_id))

        conn.commit()
        return True

    except Exception as erro:
        print("Erro ao registrar notificacao enviada", erro)
        return False

    finally:
        cursor.close()
        conn.close()

def remover_push_subscription(endpoint):
    conn = conectar()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM push_subscriptions
            WHERE endpoint = %s
        """, (endpoint,))

        conn.commit()
        return True

    except Exception as erro:
        print("Erro ao remover inscricao push", erro)
        return False

    finally:
        cursor.close()
        conn.close()

def listar_por_tipo(usuario_id, tipo):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM dividas
        WHERE usuario_id = %s
        AND tipo = %s
        ORDER BY vencimento
    """, (usuario_id, tipo))

    dados = cursor.fetchall()

    conn.close()

    return dados

def grafico(usuario_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            tipo,
            SUM(valor) AS total
        FROM dividas
        WHERE usuario_id = %s
        AND status = 'ativa'
        AND DATE_TRUNC('month', vencimento) =
            DATE_TRUNC('month', CURRENT_DATE)
        GROUP BY tipo
    """, (usuario_id,))

    dados = cursor.fetchall()

    conn.close()

    return dados 