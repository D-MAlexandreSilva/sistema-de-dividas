from flask import Flask, render_template, request, redirect, session, flash
import banco as b
import bcrypt
import json
import threading
import time
from pywebpush import WebPushException
from config import SECRET_KEY, VAPID_PUBLIC_KEY
from push_service import enviar_push
import calendar
from datetime import datetime

app = Flask(__name__)
app.secret_key = SECRET_KEY

from datetime import datetime, timedelta

from flask import send_from_directory

@app.route('/sw.js')
def service_worker():
    return send_from_directory('.', 'sw.js')

def para_brasilia(data):
    if not data:
        return None

    # se vier string do banco
    if isinstance(data, str):
        data = datetime.strptime(data, "%Y-%m-%d %H:%M:%S")

    return data - timedelta(hours=3)

with app.app_context():
    b.criar_tabela()

_agendador_iniciado = False

def enviar_alertas_vencimento():
    alertas = b.listar_alertas_vencendo_hoje()
    enviados = 0

    for alerta in alertas:
        divida_id, usuario_id, descricao, valor, vencimento, endpoint, p256dh, auth = alerta
        titulo = "Divida vencendo hoje"
        mensagem = f"{descricao} vence hoje. Valor da parcela: R$ {float(valor):.2f}"

        try:
            enviar_push(endpoint, p256dh, auth, titulo, mensagem)
            b.registrar_notificacao_enviada(usuario_id, divida_id)
            enviados += 1
        except WebPushException as erro:
            status_code = getattr(getattr(erro, "response", None), "status_code", None)
            if status_code in (404, 410):
                b.remover_push_subscription(endpoint)
            print("Erro ao enviar push:", erro)
        except Exception as erro:
            print("Erro inesperado ao enviar push:", erro)

    return enviados

def _loop_alertas():
    with app.app_context():
        enviar_alertas_vencimento()

    while True:
        time.sleep(60 * 60)
        with app.app_context():
            enviar_alertas_vencimento()

def iniciar_agendador_push():
    global _agendador_iniciado

    if _agendador_iniciado:
        return

    _agendador_iniciado = True
    thread = threading.Thread(target=_loop_alertas, daemon=True)
    thread.start()

@app.route("/")
def home():
    return render_template("cadastro.html")

@app.route("/cadastro", methods=["POST"])
def cadastro():
    usuario = request.form['usuario'].strip()
    senha = request.form['senha'].strip()

    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode('utf-8')

    sucesso = b.cadastrar_usuario(usuario, senha_hash)

    if sucesso:
        flash("UsuÃ¡rio cadastrado com sucesso!", "success")
        return redirect("/login")
    else:
        flash("Erro ao cadastrar usuÃ¡rio jÃ¡ existe.", "error")
        return redirect(f"/")
    
@app.route("/login")
def logar():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def logando():
    usuario = request.form['usuario'].strip()
    senha = request.form['senha'].strip()

    resultado = b.login(usuario, senha)

    if resultado:
        session["usuario_id"] = resultado
        flash("Bem Vindo ao sistema de controle de dividas...!", "success")
        return redirect("/menu")
    else:
        flash("UsuÃ¡rio ou Senha, InvÃ¡lidos!", "success")
        return redirect("/login")
    
from datetime import date

@app.route("/menu")
def menu():
    if "usuario_id" not in session:
        return redirect("/login")

    return render_template("menu.html")

@app.route("/painel", methods=["GET", "POST"])
def painel():

    if "usuario_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        usuario_id = session["usuario_id"]
        tipo = request.form['tipo']
        descricao = request.form['descricao']
        valor = float(request.form['valor'])
        parcelas_total = int(request.form['parcelas_total'])
        vencimento = request.form['vencimento']

        sucesso = b.adicionar_divida(
            usuario_id,
            descricao,
            tipo,
            valor,
            parcelas_total,
            vencimento
        )

        if sucesso:
            flash("Dívida cadastrada com sucesso!", "success")
        else:
            flash("Erro no cadastro da Divida!", "error")

        return redirect("/painel")

    dividas = b.listar(session["usuario_id"])

    hoje = date.today()

    tem_vencimento_hoje = False

    for divida in dividas:

        vencimento = divida[7]  # ajuste se o Ã­ndice for outro

        if vencimento == hoje:
            tem_vencimento_hoje = True
            break

    return render_template(
        "painel.html",
        tem_vencimento_hoje=tem_vencimento_hoje,
        vapid_public_key=VAPID_PUBLIC_KEY
    )

@app.route("/dividas")
def listar_dividas():
    if "usuario_id" not in session:
        return redirect("/login")

    tipo = request.args.get("tipo")

    # 📋 lista
    if tipo:
        dividas = b.listar_por_tipo(session["usuario_id"], tipo)
    else:
        dividas = b.listar(session["usuario_id"])

    # 📊 gráfico
    grafico = b.grafico(session["usuario_id"]) or []

    total_mes = b.total_mes(session["usuario_id"])

    return render_template(
        "dividas.html",
        dividas=dividas,
        grafico=grafico,
        total_mes=total_mes,
        tipo_atual=tipo
    )

@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    if "usuario_id" not in session:
        return redirect("/login")

    usuario_id = session["usuario_id"]

    if request.method == "POST":
        tipo = request.form['tipo']
        descricao = request.form['descricao']
        valor = float(request.form['valor'])
        parcelas_total = int(request.form['parcelas_total'])
        vencimento = request.form['vencimento']

        sucesso = b.editar_divida(
            id,
            usuario_id,
            tipo,
            descricao,
            valor,
            parcelas_total,
            vencimento
        )

        if sucesso:
            return redirect("/dividas")
        else:
            return "Erro ao editar dÃ­vida"

    divida = b.buscar_divida(id, usuario_id)

    if not divida:
        return "Dívida não encontrada"

    return render_template("editar_divida.html", divida=divida)

@app.route("/excluir/<int:id>", methods=["POST"])
def excluir(id):
    if "usuario_id" not in session:
        return redirect("/login")
    
    usuario_id = session["usuario_id"]

    sucesso = b.excluir_divida(id, usuario_id)

    if sucesso:
        flash("Divida excluida com sucesso!", "success")
    else:
        flash("Falha ao excluir a divida!", "error")

    return redirect("/dividas")

@app.route("/pagar/<int:id>", methods=["POST"])
def pagar(id):
    usuario_id = session["usuario_id"]

    sucesso = b.pagar_parcela(id, usuario_id)

    if sucesso:
        flash("Parcela paga com sucesso!", "success")
    else:
        flash("Erro ao pagar parcela!", "error")

    return redirect("/dividas")


@app.route("/gastos", methods=["GET", "POST"])
def gastos():

    if "usuario_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        acao = request.form.get("acao")

        if acao == "saldo":

            valor = float(request.form["valor_saldo"])

            sucesso = b.adicionar_saldo(
                session["usuario_id"],
                valor
            )

            if sucesso:
                flash("Saldo adicionado com sucesso!", "success")
            else:
                flash("Erro ao adicionar saldo!", "error")

            return redirect("/gastos")

        elif acao == "gasto":

            nome = request.form["nome"]
            descricao = request.form["descricao"]
            valor = float(request.form["valor"])

            sucesso = b.adicionar_gasto(
                session["usuario_id"],
                nome,
                descricao,
                valor
            )

            if sucesso:
                flash("Gasto cadastrado com sucesso!", "success")
            else:
                flash("Erro ao cadastrar gasto!", "error")

            return redirect("/gastos")

    lista_gastos = b.listar_gastos(session["usuario_id"])
    gasto_dia = b.total_gastos_dia(session["usuario_id"])
    gasto_semana = b.total_gastos_semana(session["usuario_id"])
    gasto_mes = b.total_gastos_mes(session["usuario_id"])
    saldo = b.buscar_saldo(session["usuario_id"])

    dados_grafico = b.grafico_gastos_mes(
        session["usuario_id"]
    )

    hoje = datetime.now()

    ano = hoje.year
    mes = hoje.month

    total_dias = calendar.monthrange(
        ano,
        mes
    )[1]

    gastos_por_dia = {
        int(dia): float(valor)
        for dia, valor in dados_grafico
    }

    dias = list(range(1, total_dias + 1))

    valores = [
        gastos_por_dia.get(dia, 0)
        for dia in dias
    ]

    lista_convertida = []

    for g in lista_gastos:
        try:
            g = list(g)

            data = g[3]

            if isinstance(data, str):
                data = datetime.strptime(
                    data,
                    "%Y-%m-%d %H:%M:%S"
                )

            if data:
                data = data - timedelta(hours=3)

            lista_convertida.append({
                "nome": g[0],
                "descricao": g[1],
                "valor": g[2],
                "data": data
            })

        except Exception as e:
            print("ERRO NO LOOP:", e)

    data_hoje = hoje.strftime("%d/%m/%Y")
    inicio_semana = (hoje - timedelta(days=6)).strftime("%d/%m/%Y")
    fim_semana = hoje.strftime("%d/%m/%Y")
    mes_atual = hoje.strftime("%m/%Y")

    return render_template(
        "gastos.html",
        gastos=lista_convertida,
        gasto_dia=gasto_dia,
        gasto_semana=gasto_semana,
        gasto_mes=gasto_mes,
        data_hoje=data_hoje,
        inicio_semana=inicio_semana,
        fim_semana=fim_semana,
        mes_atual=mes_atual,
        saldo=saldo,
        dias=dias,
        valores=valores
    )

@app.route("/save-subscription", methods=["POST"])
def save_subscription():

    if "usuario_id" not in session:
        return {"ok": False}, 401

    data = request.get_json()

    usuario_id = session["usuario_id"]
    endpoint = data["endpoint"]
    p256dh = data["keys"]["p256dh"]
    auth = data["keys"]["auth"]

    sucesso = b.salvar_push_subscription(usuario_id, endpoint, p256dh, auth)

    return {"ok": sucesso}



if __name__ == "__main__":
    iniciar_agendador_push()
    app.run(host="0.0.0.0", port=5000)

