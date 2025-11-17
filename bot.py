# bot.py
import os
import threading
import requests
from urllib.parse import quote_plus
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from datetime import datetime

# --- Configuração ---
# Este script deve estar na mesma pasta que o app.py
# Ele se conectará ao MESMO banco de dados
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_FOLDER = os.path.join(BASE_DIR, 'instance')

app = Flask(__name__)
# Usa o caminho absoluto para o DB
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(INSTANCE_FOLDER, 'workflow.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Configuração de Notificações (Copiado do app.py) ---
API_KEY = "9102015"
API_URL = "https://api.callmebot.com/whatsapp.php"

# --- NÚMEROS AUTORIZADOS ---
# ATENÇÃO: Adicione aqui os números que podem consultar o bot.
# Use o formato do CallMeBot (ex: "554199998888")
AUTHORIZED_BOT_NUMBERS = [
    "554188368319", # ADMIN (exemplo)
    "554100000000", # PAULO (exemplo)
    "554100000001", # RENATO (exemplo)
    # Adicione outros números de gerentes/colaboradores aqui
]

# --- Modelos do Banco de Dados (Copiados do app.py) ---
# Precisamos redefinir os modelos aqui para que este script possa
# entender a estrutura do banco de dados.

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    logs = db.relationship('ActivityLog', backref='user', lazy=True)
    orcamentos_atualizados = db.relationship('Orcamento', backref='last_update_user', lazy=True)

class ActivityLog(db.Model):
    __tablename__ = 'activity_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    orcamento_id = db.Column(db.Integer, nullable=True)
    orcamento_numero = db.Column(db.String(50))
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Grupo(db.Model):
    __tablename__ = 'grupo'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    orcamentos = db.relationship('Orcamento', backref='grupo', lazy=True)

class Orcamento(db.Model):
    __tablename__ = 'orcamento'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), nullable=False)
    cliente = db.Column(db.String(200), nullable=False)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo.id'), nullable=False)
    status_atual = db.Column(db.String(100), default='Orçamento Aprovado')
    data_entrada_producao = db.Column(db.DateTime)
    data_limite_producao = db.Column(db.DateTime)
    data_visita = db.Column(db.DateTime)
    responsavel_visita = db.Column(db.String(100))
    data_pronto = db.Column(db.DateTime)
    data_instalacao = db.Column(db.DateTime)
    responsavel_instalacao = db.Column(db.String(100))
    etapa_concluida = db.Column(db.Integer, default=0)
    last_updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    tarefas = db.relationship('TarefaProducao', backref='orcamento', lazy=True)

class TarefaProducao(db.Model):
    __tablename__ = 'tarefa_producao'
    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(db.Integer, db.ForeignKey('orcamento.id'), nullable=False)
    colaborador = db.Column(db.String(100), nullable=False)
    item_descricao = db.Column(db.String(500))
    status = db.Column(db.String(50), default='Não Iniciado')
    etapa = db.Column(db.Integer, default=1, nullable=False)


# --- Função de Envio (Copiada do app.py) ---
def send_whatsapp_notification(message, phone_numbers):
    def send_request_target(phone, encoded_message):
        try:
            full_url = f"{API_URL}?phone={phone}&text={encoded_message}&apikey={API_KEY}"
            response = requests.get(full_url, timeout=10)
            print(f"Notificação (BOT) enviada para {phone}. Status: {response.status_code}")
        except Exception as e:
            print(f"Erro ao enviar notificação (BOT) para {phone}: {e}")
    try:
        encoded_message = quote_plus(message)
        if not isinstance(phone_numbers, list):
            phone_numbers = [phone_numbers]
        for phone in phone_numbers:
            thread = threading.Thread(target=send_request_target, args=(phone, encoded_message))
            thread.start()
    except Exception as e:
        print(f"Erro ao preparar notificação (BOT): {e}")

# --- LÓGICA DO BOT (FUNÇÃO DE FORMATAÇÃO ATUALIZADA) ---

def formatar_data(data_obj):
    """Formata um objeto datetime para 'dd/mm/aaaa' ou 'dd/mm às HH:MM'."""
    if not data_obj:
        return ""
    if data_obj.hour == 0 and data_obj.minute == 0:
        return data_obj.strftime('%d/%m/%Y')
    return data_obj.strftime('%d/%m às %H:%M')

def format_orcamento_status(orcamento):
    """
    Cria a string de resposta formatada com base no status do orçamento.
    (VERSÃO ATUALIZADA COM EMOJIS E FORMATAÇÃO)
    """
    try:
        # --- 1. Informações Básicas ---
        grupo_nome = orcamento.grupo.nome
        # 0 -> Etapa 1, 1 -> Etapa 2, 2 -> Concluído
        etapa_num = orcamento.etapa_concluida + 1
        etapa_str = f"Etapa {etapa_num}"
        
        cliente_info = f"👤 *Cliente:* {orcamento.numero} - {orcamento.cliente}"
        local_info = f"📍 *Localização:* {grupo_nome} ({etapa_str})"

        # --- 2. Data de Entrada (Log de Criação) ---
        log_criacao = ActivityLog.query.filter(
            ActivityLog.orcamento_id == orcamento.id,
            or_(ActivityLog.action == "Criação Manual", ActivityLog.action == "Upload ZIP")
        ).order_by(ActivityLog.timestamp.asc()).first()
        
        data_entrada_str = ""
        if log_criacao:
            data_entrada_str = f"🗓️ *Data de Entrada:* {log_criacao.timestamp.strftime('%d/%m/%Y')}"

        # --- 3. Montagem da Mensagem (Específica por Grupo) ---
        titulo = "📋 *Status do Pedido*"
        detalhes = f"ℹ️ *Status:* {orcamento.status_atual}"
        extras = data_entrada_str # Começa com a data de entrada

        # Lógica Específica por Grupo/Status
        if grupo_nome == "Entrada de Orçamento":
            titulo = "📥 *Orçamento na Entrada*"
            if orcamento.status_atual == "Agendar Visita":
                detalhes = "ℹ️ *Status:* Aguardando agendamento de visita."
            elif orcamento.status_atual == "Visita Agendada":
                detalhes = "ℹ️ *Status:* Visita já foi agendada (aguardando execução)."
            elif orcamento.status_atual in ['Desenhar', 'Produzir']:
                detalhes = "ℹ️ *Status:* Sendo preparado para engenharia/produção."
            else:
                detalhes = f"ℹ️ *Status:* {orcamento.status_atual}"
        
        elif grupo_nome == "Visitas e Medidas":
            titulo = "📅 *Visitas e Medidas*"
            if orcamento.status_atual == "Agendar Visita":
                detalhes = "ℹ️ *Status:* Aguardando definição de data para visita técnica."
            elif orcamento.status_atual == "Visita Agendada" and orcamento.data_visita:
                data_visita_fmt = formatar_data(orcamento.data_visita)
                responsavel = orcamento.responsavel_visita or "Equipe"
                detalhes = f"✅ *Visita Agendada:*\n  *Data:* {data_visita_fmt}\n  *Responsável:* {responsavel}"
            else:
                 detalhes = f"ℹ️ *Status:* {orcamento.status_atual}"

        elif grupo_nome == "Linha de Produção":
            titulo = "⚙️ *Em Produção*"
            if orcamento.data_limite_producao:
                extras = f"🏁 *Prazo Final:* {orcamento.data_limite_producao.strftime('%d/%m/%Y')}\n{data_entrada_str}"

            # Pega tarefas da etapa atual
            tarefas_atuais = [t for t in orcamento.tarefas if t.etapa == etapa_num]
            
            tarefas_iniciadas = [t.item_descricao for t in tarefas_atuais if t.status == "Iniciou a Produção"]
            tarefas_acabamento = [t.item_descricao for t in tarefas_atuais if t.status == "Fase de Acabamento"]

            detalhes = "⏳ *Status:* Aguardando início da produção."
            if tarefas_iniciadas or tarefas_acabamento:
                detalhes = "🚀 *Itens em Andamento:*"
                itens_unicos = set(tarefas_iniciadas + tarefas_acabamento)
                for item in sorted(list(itens_unicos)):
                    status_item = "Acabamento" if item in tarefas_acabamento else "Iniciado"
                    detalhes += f"\n  - {item} ({status_item})"
            elif any(t.status == 'Aguardando Vidro / Pedra' for t in tarefas_atuais):
                 detalhes = "📦 *Status:* Aguardando Vidro / Pedra."

        elif grupo_nome == "Prontos":
            titulo = "✅ *Pedido Pronto!*"
            if orcamento.data_limite_producao:
                extras = f"🏁 *Prazo Produção:* {orcamento.data_limite_producao.strftime('%d/%m/%Y')}\n{data_entrada_str}"

            etapa_pronta = 1 if orcamento.etapa_concluida == 0 else 2
            tarefas_prontas = [t.item_descricao for t in orcamento.tarefas if t.etapa == etapa_pronta and t.item_descricao]
            itens_str = ", ".join(sorted(list(set(tarefas_prontas)))) or f"Itens da Etapa {etapa_pronta}"
            
            detalhes = f"📦 *Itens Prontos:* {itens_str}"

            if orcamento.status_atual == "Agendar Instalação/Entrega":
                detalhes += "\n\n🚚 *Status:* Aguardando agendamento da instalação/entrega."
            elif orcamento.status_atual == "Instalação Agendada" and orcamento.data_instalacao:
                data_inst_fmt = formatar_data(orcamento.data_instalacao)
                resp_inst = orcamento.responsavel_instalacao or "Equipe"
                detalhes += f"\n\n🔧 *Instalação Agendada:*\n  *Data:* {data_inst_fmt}\n  *Responsável:* {resp_inst}"

        elif grupo_nome == "Instalados":
            titulo = "🎉 *Projeto Concluído!*"
            detalhes = "ℹ️ *Status:* O projeto foi instalado com sucesso."
            data_inst_fmt = ""
            if orcamento.data_instalacao:
                 data_inst_fmt = f"\n  *Data:* {formatar_data(orcamento.data_instalacao)}"
            
            resp_inst = orcamento.responsavel_instalacao or "Equipe"
            detalhes += f"\n\n🔧 *Instalação:*{data_inst_fmt}\n  *Responsável:* {resp_inst}"

        elif grupo_nome == "StandBy":
            titulo = "⏸️ *Pedido em Pausa*"
            detalhes = f"ℹ️ *Status:* {orcamento.status_atual}"
            detalhes += "\n\n✋ *Atenção:* O projeto está temporariamente em StandBy. Entre em contato para mais detalhes."

        # --- 4. Montagem Final ---
        # Adiciona quebras de linha extras se 'extras' tiver conteúdo
        extras_formatado = f"\n\n{extras}" if extras.strip() else ""
        
        msg = f"{titulo}\n\n{cliente_info}\n{local_info}\n\n{detalhes}{extras_formatado}"
        return msg

    except Exception as e:
        print(f"[ERRO no format_orcamento_status]: {e}")
        # Retorna uma mensagem de erro formatada
        return f"🚨 *Erro ao Processar Pedido*\n\nOcorreu um erro ao formatar o status para o orçamento *{orcamento.numero}*.\n\nPor favor, verifique os logs do *bot.py*."


def process_bot_query(query):
    """
    Busca o orçamento no banco de dados e retorna a string formatada.
    """
    if not query:
        return "Por favor, envie um número ou nome de cliente para a consulta."

    try:
        # Busca por número OU por nome do cliente
        orcamento = Orcamento.query.filter(
            or_(
                Orcamento.numero == query,
                Orcamento.cliente.ilike(f"%{query}%")
            )
        ).first()

        if not orcamento:
            return f"Desculpe, não encontrei nenhum orçamento com o número ou cliente '{query}'."

        # Se encontrou, formata a resposta
        return format_orcamento_status(orcamento)

    except Exception as e:
        print(f"[ERRO no process_bot_query]: {e}")
        return "Ocorreu um erro interno ao consultar o banco de dados."


# --- Rota do Webhook ---
# Esta é a rota que você deve configurar no seu provedor de API do WhatsApp
# (ex: Twilio, Meta, etc.)
#
# Para TESTAR manualmente (via terminal):
# curl -X POST http://127.0.0.1:5002/api/bot/webhook -H "Content-Type: application/json" -d "{\"phone\": \"554188368319\", \"message\": \"1111\"}"
#
@app.route('/api/bot/webhook', methods=['POST'])
def whatsapp_bot_webhook():
    
    # Tenta extrair dados do payload
    # O formato do payload depende MUITO do seu provedor de API
    # Estou assumindo um JSON simples: {"phone": "NUMERO", "message": "TEXTO"}
    # Adapte esta seção para o formato que seu provedor enviar (ex: Twilio usa request.form)
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Payload JSON inválido"}), 400

    remetente_phone = data.get('phone')
    mensagem_texto = data.get('message')

    if not remetente_phone or not mensagem_texto:
        return jsonify({"error": "Campos 'phone' e 'message' são obrigatórios no JSON"}), 400

    print(f"Webhook recebido de {remetente_phone}: \"{mensagem_texto}\"")

    # 1. Verificar Autorização
    if remetente_phone not in AUTHORIZED_BOT_NUMBERS:
        print(f"Número não autorizado: {remetente_phone}. Ignorando.")
        return jsonify({"status": "Ignorado (Não autorizado)"}), 200 # Responde OK, mas não faz nada

    # 2. Processar a consulta
    # Usamos app.app_context() para garantir que temos acesso ao DB
    with app.app_context():
        response_message = process_bot_query(mensagem_texto.strip())

    # 3. Enviar a resposta de volta
    send_whatsapp_notification(response_message, [remetente_phone])

    return jsonify({"status": "Resposta enviada"}), 200


# --- Execução ---
if __name__ == '__main__':
    if not os.path.exists(INSTANCE_FOLDER):
        print(f"ERRO: Pasta 'instance' não encontrada em: {INSTANCE_FOLDER}")
        print("Certifique-se que o app.py principal já foi executado ao menos uma vez para criar a pasta e o banco.")
    else:
        # Executa o bot na porta 5002 (para não conflitar com o app.py na 5001)
        print("Iniciando Servidor do Bot (Webhook) na porta 5002...")
        print("Aponte sua API do WhatsApp (Ex: Twilio) para: http://<seu_ip_publico>:5002/api/bot/webhook")
        app.run(debug=True, port=5002, host='0.0.0.0')