import os
import zipfile
import json
import requests
import threading
import uuid
import re
from urllib.parse import quote_plus
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from flask_apscheduler import APScheduler

# --- Configuração (CAMINHOS ATUALIZADOS) ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_FOLDER = os.path.join(BASE_DIR, 'instance')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')


app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(INSTANCE_FOLDER, 'workflow.db')}"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'uma-chave-secreta-muito-forte-padrao')

app.config['GOOGLE_OAUTH_CLIENT_ID'] = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')

app.config['SCHEDULER_API_ENABLED'] = True

db = SQLAlchemy(app)
# --- Fim da Configuração Atualizada ---

# --- Configuração de Notificações (ATUALIZADO PARA BOT LOCAL) ---
# Agora aponta para o servidor node rodando o bot.js na porta 5000
API_URL = "http://127.0.0.1:5000/send_notification"

# Telefones mantidos para referência (a função de envio agora delega o destino ao bot.js)
PHONE_ADMIN = "554188368319"
PHONE_PAULO = "554100000000"
PHONE_RENATO = "554100000001"
LISTA_GERAL = [PHONE_ADMIN]

# --- NÚMEROS AUTORIZADOS PARA O BOT (CONSULTAS) ---
AUTHORIZED_BOT_NUMBERS = [
    "554188368319@c.us", # SEU NÚMERO
    "554100000000@c.us", # PAULO
    "554187831513@c.us", # RENATO
    "554192078542@c.us", # ADICIONADO
]

# --- Configuração do Login Manager ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para acessar esta página."

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --- Configuração do Google OAuth (Flask-Dance) ---
google_bp = make_google_blueprint(
    client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
    client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
    redirect_to='google_auth',
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
)
app.register_blueprint(google_bp, url_prefix="/login")

# --- Função Auxiliar de Notificação (ATUALIZADA) ---
def send_whatsapp_notification(message, phone_numbers=None):
    """
    Envia notificação para o Bot Local (bot.js).
    O parâmetro phone_numbers é mantido para compatibilidade de chamada, 
    mas o bot.js decidirá o destino (Grupo 120363404624474162@g.us).
    """
    def send_request_target(msg_content):
        try:
            payload = {"message": msg_content}
            headers = {'Content-Type': 'application/json'}
            # Envia POST para o bot.js
            response = requests.post(API_URL, json=payload, headers=headers, timeout=10)
            print(f"Notificação enviada para o Bot Local. Status: {response.status_code}")
        except Exception as e:
            print(f"Erro ao enviar notificação para o Bot Local: {e}")
            
    try:
        # Executa em thread para não bloquear a resposta da interface web
        thread = threading.Thread(target=send_request_target, args=(message,))
        thread.start()
    except Exception as e:
        print(f"Erro ao preparar notificação: {e}")

# --- INÍCIO: NOVOS MAPEAMENTOS (Criação Manual) ---

# Mapeia o ITEM para o COLABORADOR
MAP_ITEM_COLABORADOR = {
    # Hélio (Etapa 1 e 2)
    "Coifa": "Hélio",
    "Coifa Epoxi": "Hélio",
    "Exaustor": "Hélio",
    "Chaminé": "Hélio",
    "Chapéu Aletado": "Hélio",
    "Chapéu Canhão": "Hélio",
    "Revestimento": "Hélio", # E2
    "Gavetão Inox": "Hélio", # E2
    "Gavetão Epóxi": "Hélio", # E2
    "Caixa Braseiro": "Hélio", # E1

    # Edison (Etapa 1 e 2)
    "Porta Guilhotina Vidro L": "Edison",
    "Porta Guilhotina Vidro U": "Edison",
    "Porta Guilhotina Vidro F": "Edison",
    "Porta Guilhotina Inox F": "Edison",
    "Porta Guilhotina Pedra F": "Edison",
    "Tampa de vidro": "Edison", # E2

    # Renato (Etapa 1)
    "Revestimento Base": "Renato",
    "Placa cimenticia Porta": "Renato",
    "Isolamento Coifa": "Renato",

    # Luiz (Etapa 2)
    "Regulagem de balanço": "Luiz", # (Item antigo)
    "Sistema Giratório": "Luiz", # (Item antigo)
    "Moldura Área de fogo": "Luiz",
    "Bancada interna": "Luiz", # (Item antigo)
    "Bifeteira grill": "Luiz",
    "Cooktop + Bifeteira": "Luiz",
    "Cooktop": "Luiz",
    "Balanço 2": "Luiz",
    "Balanço 3": "Luiz",
    "Balanço 4": "Luiz",
    # Giratórios são tratados por lógica especial
    "Giratório 1L": "Luiz",
    "Giratório 2L": "Luiz",

    # José (Etapa 2)
    "Grelhas": "José", # (Item antigo)
    "Espetos": "José", # (Item antigo)
    "Sistema de elevar Manual": "José", # (Item antigo)
    "Grelha de descanso": "José",
    "Kit 6 Espetos": "José",
    "Regulagem Comum 2": "José",
    "Regulagem Comum 3": "José",
    "Regulagem Comum 4": "José",
    "Regulagem Comum 5": "José",
    # Espetos de Giratórios são tratados por lógica especial

    # Anderson (Etapa 2)
    "Tampa Inox": "Anderson",
    "Tampa Epoxi": "Anderson",
    "Tampa INOX": "Anderson", # (Duplicado por segurança)
    "Tampa Preto Epoxi": "Anderson", # (Duplicado por segurança)

    # Lareiras (Etapa 2)
    "KAM600": "Edison", "KAM700": "Edison", "KAM800": "Edison", "KAM900": "Edison",
    "KAM1000": "Edison", "KAM1100": "Edison", "KAM1200": "Edison",
    "KAM VITRO": "Edison", "LYON": "Edison", "ARGON": "Edison", "GAB1000": "Edison",
    "Chaminé inox": "Anderson",
    "Chaminé Aço Carbono": "Anderson",
    
    # Itens Elevar (Etapa 2)
    "Sistema de Elevar Manual 2 3/16": "José", 
    "Sistema de Elevar Manual 1/8 e 3/16": "José",
    "Sistema de Elevar Manual Arg. e 3/16": "José",
    "Sistema de Elevar Manual Arg. e 1/8": "José",
    "Sistema de Elevar Motor 2 3/16": "José",
    "Sistema de Elevar Motor 1/8 e 3/16": "José",
    "Sistema de Elevar Motor Arg e 3/16": "José",
    "Sistema de Elevar Motor Arg e 1/8": "José",
}

# Mapeia quais itens vão para a ETAPA 1
ITENS_ETAPA_1 = [
    "Coifa", "Coifa Epoxi", "Exaustor", "Chaminé", "Chapéu Aletado", "Chapéu Canhão", "Caixa Braseiro",
    "Porta Guilhotina Vidro L", "Porta Guilhotina Vidro U", "Porta Guilhotina Vidro F",
    "Porta Guilhotina Inox F", "Porta Guilhotina Pedra F",
    "Revestimento Base", "Placa cimenticia Porta", "Isolamento Coifa"
]
# --- FIM: NOVOS MAPEAMENTOS ---


# --- Modelos do Banco de Dados (ATUALIZADOS) ---

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=True)
    is_google_user = db.Column(db.Boolean, default=False)
    logs = db.relationship('ActivityLog', backref='user', lazy=True)
    orcamentos_atualizados = db.relationship('Orcamento', backref='last_update_user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_nome = db.Column(db.String(100))
    orcamento_id = db.Column(db.Integer, nullable=True)
    orcamento_numero = db.Column(db.String(50))
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Grupo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    ordem = db.Column(db.Integer, default=1)
    orcamentos = db.relationship('Orcamento', backref='grupo', lazy=True)

class Orcamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    numero = db.Column(db.String(50), nullable=False)
    cliente = db.Column(db.String(200), nullable=False)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo.id'), nullable=False)
    status_atual = db.Column(db.String(100), default='Orçamento Aprovado')
    
    data_entrada_producao = db.Column(db.DateTime)
    
    data_visita = db.Column(db.DateTime, name="data_visita_etapa1") 
    responsavel_visita = db.Column(db.String(100)) 
    
    data_pronto = db.Column(db.DateTime)
    
    data_instalacao = db.Column(db.DateTime) 
    responsavel_instalacao = db.Column(db.String(100)) 
    
    grupo_origem_standby = db.Column(db.Integer)
    standby_details = db.Column(db.Text, nullable=True)
    
    etapa1_descricao = db.Column(db.String(500))
    etapa2_descricao = db.Column(db.String(500))
    
    etapa_concluida = db.Column(db.Integer, default=0) # 0=Nenhuma, 1=Etapa 1, 2=Etapa 2
    
    tarefas = db.relationship('TarefaProducao', backref='orcamento', lazy=True, cascade="all, delete-orphan")
    arquivos = db.relationship('ArquivoAnexado', backref='orcamento', lazy=True, cascade="all, delete-orphan")

    last_updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    endereco = db.Column(db.String(500), nullable=True)
    data_limite_etapa1 = db.Column(db.DateTime)
    data_limite_etapa2 = db.Column(db.DateTime)
    
    data_visita_etapa2 = db.Column(db.DateTime)

    prazo_dias_etapa1 = db.Column(db.Integer, nullable=True)
    prazo_dias_etapa2 = db.Column(db.Integer, nullable=True)
    numero_cliente = db.Column(db.String(50), nullable=True)
    outro_numero = db.Column(db.String(50), nullable=True)
    

    def to_dict(self):
        current_etapa = 2 if self.etapa_concluida >= 1 else 1
        tarefas_filtradas = [t.to_dict() for t in self.tarefas if t.etapa == current_etapa]

        itens_prontos = ""
        if self.grupo.nome == 'Prontos':
            etapa_pronta = 1 if self.etapa_concluida == 0 else 2
            
            tarefas_da_etapa_pronta = [t.item_descricao for t in self.tarefas if t.etapa == etapa_pronta and t.item_descricao]
            
            if tarefas_da_etapa_pronta:
                itens_prontos_lista = sorted(list(set(tarefas_da_etapa_pronta)))
                itens_prontos = ", ".join(itens_prontos_lista)
            else:
                if etapa_pronta == 1:
                    itens_prontos = self.etapa1_descricao
                else:
                    itens_prontos = self.etapa2_descricao

        return {
            "id": self.id,
            "public_id": self.public_id,
            "numero": self.numero,
            "cliente": self.cliente,
            "grupo_id": self.grupo_id,
            "grupo_nome": self.grupo.nome,
            "status_atual": self.status_atual,
            "data_entrada_producao": self.data_entrada_producao.strftime('%Y-%m-%d') if self.data_entrada_producao else None,
            
            "data_limite_etapa1": self.data_limite_etapa1.strftime('%Y-%m-%d') if self.data_limite_etapa1 else None,
            "data_limite_etapa2": self.data_limite_etapa2.strftime('%Y-%m-%d') if self.data_limite_etapa2 else None,
            
            "data_visita_etapa1": self.data_visita.strftime('%Y-%m-%d') if self.data_visita else None,
            "data_visita_etapa2": self.data_visita_etapa2.strftime('%Y-%m-%d') if self.data_visita_etapa2 else None,
            "data_instalacao": self.data_instalacao.strftime('%Y-%m-%d') if self.data_instalacao else None,
            
            "data_visita_agendada": self.data_visita.strftime('%Y-%m-%d %H:%M') if self.data_visita else None,
            "responsavel_visita": self.responsavel_visita,
            "data_instalacao_agendada": self.data_instalacao.strftime('%Y-%m-%d %H:%M') if self.data_instalacao else None,
            "responsavel_instalacao": self.responsavel_instalacao,

            "data_pronto": self.data_pronto.strftime('%Y-%m-%d %H:%M') if self.data_pronto else None,
            "grupo_origem_standby": self.grupo_origem_standby,
            "standby_details": self.standby_details,
            "etapa1_descricao": self.etapa1_descricao,
            "etapa2_descricao": self.etapa2_descricao,
            "etapa_concluida": self.etapa_concluida,
            "itens_prontos": itens_prontos,
            "tarefas": sorted(tarefas_filtradas, key=lambda x: (x['colaborador'], x['item_descricao'])),
            "arquivos": [a.to_dict() for a in self.arquivos],
            "last_updated_at": self.last_updated_at.isoformat() if self.last_updated_at else None,
            "last_updated_by_nome": self.last_update_user.nome if self.last_update_user else "Sistema",
            
            "endereco": self.endereco
        }

class TarefaProducao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(db.Integer, db.ForeignKey('orcamento.id'), nullable=False)
    colaborador = db.Column(db.String(100), nullable=False)
    item_descricao = db.Column(db.String(500))
    status = db.Column(db.String(50), default='Não Iniciado')
    etapa = db.Column(db.Integer, default=1, nullable=False) # 1 ou 2
    
    def to_dict(self):
        return { 
            "id": self.id, 
            "colaborador": self.colaborador, 
            "item_descricao": self.item_descricao, 
            "status": self.status,
            "etapa": self.etapa
        }

class ArquivoAnexado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(db.Integer, db.ForeignKey('orcamento.id'), nullable=False)
    nome_arquivo = db.Column(db.String(300))
    caminho_arquivo = db.Column(db.String(500))

    def to_dict(self):
        return { "id": self.id, "nome_arquivo": self.nome_arquivo, "url": f"/{self.caminho_arquivo}" }

# --- Função Helper de Log ---
def log_activity(orcamento, action, details):
    if current_user.is_authenticated:
        log = ActivityLog(
            user_id=current_user.id,
            user_nome=current_user.nome,
            orcamento_id=orcamento.id,
            orcamento_numero=orcamento.numero,
            action=action,
            details=details
        )
        db.session.add(log)
        orcamento.last_updated_by_id = current_user.id
        orcamento.last_updated_at = datetime.utcnow()
        db.session.add(orcamento)
    else:
        orcamento.last_updated_by_id = None
        orcamento.last_updated_at = datetime.utcnow()
        db.session.add(orcamento)
        
        log = ActivityLog(
            user_id=1, 
            user_nome="Sistema",
            orcamento_id=orcamento.id,
            orcamento_numero=orcamento.numero,
            action=action,
            details=details
        )
        db.session.add(log)

# --- Rotas de Autenticação ---
@app.route('/login')
def login():
    error = request.args.get('error')
    return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/auth', methods=['POST'])
def auth():
    email = request.form.get('email')
    senha = request.form.get('senha')
    remember_me = True if request.form.get('remember_me') else False
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(senha):
        return redirect(url_for('login', error='Email ou senha inválidos.'))
    login_user(user, remember=remember_me)
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    nome = request.form.get('nome')
    email = request.form.get('email')
    senha = request.form.get('senha')
    if not nome or not email or not senha:
        return redirect(url_for('login', error='Todos os campos são obrigatórios para registro.'))
    user = User.query.filter_by(email=email).first()
    if user:
        return redirect(url_for('login', error='Este email já está registrado.'))
    new_user = User(nome=nome, email=email)
    new_user.set_password(senha)
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)
    return redirect(url_for('index'))

@app.route('/google-auth')
def google_auth():
    if not google.authorized:
        return redirect(url_for('login'))
    try:
        resp = google.get("/oauth2/v2/userinfo")
        if not resp.ok:
            return redirect(url_for('login', error='Falha ao autenticar com Google.'))
        info = resp.json()
        email = info['email']
        nome = info['name']
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(nome=nome, email=email, is_google_user=True)
            db.session.add(user)
            db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Erro na autenticação Google: {e}")
        return redirect(url_for('login', error='Ocorreu um erro inesperado.'))

# --- Rota Principal (Frontend) ---
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# --- Rota do Painel de Logs ---
@app.route('/logs')
@login_required
def logs_page():
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    logs = ActivityLog.query.filter(ActivityLog.timestamp >= cutoff_date).order_by(ActivityLog.timestamp.desc()).all()
    return render_template('logs.html', logs=logs)

# --- Rotas de Calendário ---

@app.route('/calendario')
@login_required
def calendario_page():
    return render_template('calendario.html')

@app.route('/api/calendario/eventos')
@login_required
def get_calendario_eventos():
    tipo = request.args.get('tipo', 'todos')
    eventos = []
    
    try:
        base_query_fields = [
            Orcamento.numero, 
            Orcamento.cliente,
            Orcamento.etapa_concluida,
            Orcamento.etapa1_descricao,
            Orcamento.etapa2_descricao,
            User.nome.label('quem_agendou'),
            Orcamento.id.label('orcamento_id'),
            Orcamento.endereco
        ]

        if tipo == 'visitas' or tipo == 'todos':
            # Query para Visita Etapa 1
            query_visitas1 = db.session.query(
                Orcamento.data_visita, 
                Orcamento.responsavel_visita,
                *base_query_fields
            ).outerjoin(User, Orcamento.last_updated_by_id == User.id) \
             .filter(Orcamento.data_visita != None).all()
            
            for (data, responsavel, numero, cliente, etapa_concluida, 
                 et1_desc, et2_desc, quem_agendou, orcamento_id, endereco) in query_visitas1:
                
                itens = et1_desc if et1_desc else "Itens não especificados"
                eventos.append({
                    "title": f"Visita E1: {numero} {cliente}",
                    "start": data.isoformat(),
                    "color": "#fbbc05",
                    "textColor": "#333",
                    "extendedProps": {
                        "tipo": "Visita Técnica (Etapa 1)", "numero": numero, "cliente": cliente,
                        "etapa": "Etapa 1", "itens": itens,
                        "quem_vai": responsavel or "A definir",
                        "quem_agendou": quem_agendou or "Sistema",
                        "data_hora": data.strftime('%d/%m/%Y às %H:%M'),
                        "orcamento_id": orcamento_id, "endereco": endereco or "Curitiba"
                    }
                })

            # Query para Visita Etapa 2
            query_visitas2 = db.session.query(
                Orcamento.data_visita_etapa2, 
                Orcamento.responsavel_visita, # Reutilizando campo responsavel
                *base_query_fields
            ).outerjoin(User, Orcamento.last_updated_by_id == User.id) \
             .filter(Orcamento.data_visita_etapa2 != None).all()
            
            for (data, responsavel, numero, cliente, etapa_concluida, 
                 et1_desc, et2_desc, quem_agendou, orcamento_id, endereco) in query_visitas2:
                
                itens = et2_desc if et2_desc else "Itens não especificados"
                eventos.append({
                    "title": f"Visita E2: {numero} {cliente}",
                    "start": data.isoformat(),
                    "color": "#E67E22", # Laranja mais escuro
                    "textColor": "#fff",
                    "extendedProps": {
                        "tipo": "Visita Técnica (Etapa 2)", "numero": numero, "cliente": cliente,
                        "etapa": "Etapa 2", "itens": itens,
                        "quem_vai": responsavel or "A definir",
                        "quem_agendou": quem_agendou or "Sistema",
                        "data_hora": data.strftime('%d/%m/%Y às %H:%M'),
                        "orcamento_id": orcamento_id, "endereco": endereco or "Curitiba"
                    }
                })
                
        if tipo == 'instalacoes' or tipo == 'todos':
            query_instalacoes = db.session.query(
                Orcamento.data_instalacao, 
                Orcamento.responsavel_instalacao, 
                *base_query_fields
            ).outerjoin(User, Orcamento.last_updated_by_id == User.id) \
             .filter(Orcamento.data_instalacao != None).all()
            
            for (data, responsavel, numero, cliente, etapa_concluida, 
                 et1_desc, et2_desc, quem_agendou, orcamento_id, endereco) in query_instalacoes:
                
                etapa_num = etapa_concluida + 1
                itens = et2_desc if etapa_num == 2 else et1_desc
                if not itens:
                    itens = "Itens não especificados"

                eventos.append({
                    "title": f"Instal: {numero} {cliente}",
                    "start": data.isoformat(),
                    "color": "#34a853",
                    "textColor": "#fff",
                     "extendedProps": {
                        "tipo": "Instalação / Entrega",
                        "numero": numero,
                        "cliente": cliente,
                        "etapa": f"Etapa {etapa_num}",
                        "itens": itens,
                        "quem_vai": responsavel or "A definir",
                        "quem_agendou": quem_agendou or "Sistema",
                        "data_hora": data.strftime('%d/%m/%Y às %H:%M'),
                        "orcamento_id": orcamento_id,
                        "endereco": endereco or "Curitiba"
                    }
                })

        return jsonify(eventos)

    except Exception as e:
        print(f"Erro ao buscar eventos do calendário: {e}")
        return jsonify({"error": str(e)}), 500

# --- Lógica de Acompanhamento Público ---

def get_public_status_info(orcamento):
    step_definitions = [
        {"name": "Pedido Aprovado", "details": "Recebemos a aprovação do seu orçamento."}, # 0
        {"name": "Agendamento da Visita", "details": "Nossa equipe entrará em contato para agendar a visita técnica."}, # 1
        {"name": "Visita Agendada", "details": ""}, # 2
        {"name": "Enviado para a Engenharia", "details": "Seu projeto está sendo desenhado por nossos especialistas."}, # 3
        {"name": "Em Produção", "details": ""}, # 4
        {"name": "Produção Concluída", "details": "Seu pedido está pronto! Estamos verificando a agenda de instalação."}, # 5
        {"name": "Instalação Agendada", "details": ""}, # 6
        {"name": "Instalação Concluída", "details": "Seu projeto foi finalizado. Aproveite!"} # 7
    ]
    
    output_steps = []
    etapa_concluida = orcamento.etapa_concluida
    grupo_nome = orcamento.grupo.nome
    status_atual = orcamento.status_atual
    
    current_step_name = ""
    
    if etapa_concluida >= 1:
        phase1_steps = []
        for i, step_def in enumerate(step_definitions[:7]):
            s = step_def.copy()
            s['status'] = 'completed'
            if s["name"] == "Visita Agendada": s["details"] = "Visita da 1ª Etapa concluída."
            if s["name"] == "Instalação Agendada": s["details"] = "Instalação da 1ª Etapa concluída."
            phase1_steps.append(s)
            
        output_steps.append({
            "name": "Instalação 1ª Etapa Concluída", 
            "details": "A primeira fase do seu projeto foi finalizada. Iniciando a segunda fase.", 
            "status": "completed",
            "is_phase_divider": True,
            "phase1_steps": phase1_steps
        })
        current_step_name = "Agendamento da Visita"

    if grupo_nome == 'StandBy':
        current_step_name = "Pedido em Pausa"
        details = orcamento.standby_details or "Aguardando definição ou liberação. Entre em contato conosco para mais detalhes."
        output_steps.append({"name": "Pedido em Pausa", "details": details})

    elif grupo_nome == 'Entrada de Orçamento' and etapa_concluida == 0:
        if status_atual == 'Orçamento Aprovado': current_step_name = "Pedido Aprovado"
        elif status_atual == 'Agendar Visita': current_step_name = "Agendamento da Visita"
        elif status_atual in ['Desenhar', 'Produzir', 'Mandar para Produção']: current_step_name = "Enviado para a Engenharia"

    elif grupo_nome == 'Visitas e Medidas':
        if status_atual == 'Agendar Visita':
            current_step_name = "Agendamento da Visita"
        elif status_atual == 'Visita Agendada':
            current_step_name = "Visita Agendada"
            data_fmt = "data a definir"
            # ATUALIZAÇÃO: Puxa a data correta da visita (E1 ou E2)
            data_visita_usada = orcamento.data_visita_etapa2 if etapa_concluida >= 1 else orcamento.data_visita
            if data_visita_usada:
                data_fmt = data_visita_usada.strftime('%d/%m/%Y às %H:%M')
            step_definitions[2]["details"] = f"Visita agendada para {data_fmt}."
        elif status_atual in ['Mandar para Produção', 'Em Produção']:
             current_step_name = "Enviado para a Engenharia"

    elif grupo_nome == 'Projetar':
        current_step_name = "Enviado para a Engenharia"
        if status_atual == 'Aprovado para Produção':
             current_step_name = "Em Produção"

    elif grupo_nome == 'Linha de Produção':
        current_step_name = "Em Produção"
        current_etapa = 2 if orcamento.etapa_concluida >= 1 else 1
        tarefas_filtradas = [t for t in orcamento.tarefas if t.etapa == current_etapa]
        
        itens = [t.item_descricao for t in tarefas_filtradas]
        itens_str = ", ".join(itens) if itens else "componentes"
        
        desc_etapa = orcamento.etapa2_descricao if current_etapa == 2 else orcamento.etapa1_descricao
        if desc_etapa:
             step_definitions[4]["details"] = f"Seu projeto ({desc_etapa}) está em fabricação."
        else:
             step_definitions[4]["details"] = f"Seu projeto (Itens: {itens_str}) está em fabricação."

    elif grupo_nome == 'Prontos':
        if status_atual == 'Agendar Instalação/Entrega' or status_atual == 'Entregue':
            current_step_name = "Produção Concluída"
        elif status_atual == 'Instalação Agendada':
            current_step_name = "Instalação Agendada"
            data_fmt = "data a definir"
            if orcamento.data_instalacao:
                 data_fmt = orcamento.data_instalacao.strftime('%d/%m/%Y às %H:%M')
            step_definitions[6]["details"] = f"Instalação agendada para {data_fmt}."

    elif grupo_nome == 'Instalados':
        current_step_name = "Instalação Concluída"
        if etapa_concluida == 0:
             etapa_concluida = 1 
        
    found_current = False
    start_index = 0
    if etapa_concluida >= 1:
        start_index = 1
    
    if current_step_name == "Pedido em Pausa":
        for i, step in enumerate(step_definitions):
            if i < start_index: continue
            s = step.copy()
            s['status'] = 'pending'
            output_steps.append(s)
        output_steps[-1]['status'] = 'current'
    
    else:
        for i, step in enumerate(step_definitions):
            if i < start_index: continue
            
            s = step.copy()
            step_name = s["name"]
            
            if not found_current:
                if step_name == current_step_name:
                    s['status'] = 'current'
                    found_current = True
                else:
                    s['status'] = 'completed'
            else:
                s['status'] = 'pending'
                
            output_steps.append(s)
            
    return output_steps


@app.route('/track/<string:public_id>')
def track_page(public_id):
    orcamento = Orcamento.query.filter_by(public_id=public_id).first()
    if not orcamento:
        abort(404)
    status_steps = get_public_status_info(orcamento)
    return render_template('track.html', orcamento=orcamento, status_steps=status_steps)

# --- FIM: Lógica de Acompanhamento Público ---


# --- Rotas da API (RESTO) ---
@app.route('/api/workflow', methods=['GET'])
@login_required
def get_workflow():
    grupos = Grupo.query.order_by(Grupo.ordem).all()
    workflow_data = []
    for grupo in grupos:
        orcamentos_data = [o.to_dict() for o in grupo.orcamentos]
        workflow_data.append({
            "id": grupo.id,
            "nome": grupo.nome,
            "orcamentos": orcamentos_data
        })
    return jsonify(workflow_data)

# --- Rota de Criação Manual (REESCRITA E ATUALIZADA) ---
@app.route('/api/orcamento/create_manual', methods=['POST'])
@login_required
def create_orcamento_manual():
    try:
        # 1. Validação de Arquivo e Campos Principais
        if 'arquivo' not in request.files or not request.files['arquivo'].filename:
            return jsonify({"error": "O anexo de arquivo é obrigatório."}), 400
        
        numero = request.form.get('numero_orcamento')
        cliente = request.form.get('nome_cliente')
        prazo_dias_etapa1_str = request.form.get('prazo_dias_etapa1')
        prazo_dias_etapa2_str = request.form.get('prazo_dias_etapa2')
        etapa1_finalizada_str = request.form.get('etapa1_finalizada')
        
        if not all([numero, cliente, prazo_dias_etapa1_str, prazo_dias_etapa2_str, etapa1_finalizada_str]):
             return jsonify({"error": "Todos os campos obrigatórios devem ser preenchidos (Número, Cliente, Prazos, Status Etapa 1)."}), 400

        # 2. Coleta de Dados Adicionais
        endereco = request.form.get('endereco')
        numero_cliente = request.form.get('numero_cliente')
        outro_numero = request.form.get('outro_numero')

        items_etapa1_list = json.loads(request.form.get('items_etapa1_json', '[]'))
        items_etapa2_list = json.loads(request.form.get('items_etapa2_json', '[]'))
        
        # 3. Define Grupo e Status Inicial
        etapa_concluida_int = 1 if etapa1_finalizada_str == 'Sim' else 0
        grupo_inicial_id = 1 # Padrão: Entrada de Orçamento
        status_inicial = 'Orçamento Aprovado'
        
        if etapa_concluida_int == 1:
            grupo_inicial_id = 2 # Visitas e Medidas
            status_inicial = 'Agendar Visita'

        # 4. Cria o Orçamento (sem tarefas ainda)
        novo_orcamento = Orcamento(
            numero=numero,
            cliente=cliente,
            etapa1_descricao=", ".join(items_etapa1_list), # Salva a descrição
            etapa2_descricao=", ".join(items_etapa2_list), # Salva a descrição
            grupo_id=grupo_inicial_id, 
            status_atual=status_inicial, 
            last_updated_by_id=current_user.id,
            
            endereco=endereco,
            numero_cliente=numero_cliente,
            outro_numero=outro_numero,
            prazo_dias_etapa1=int(prazo_dias_etapa1_str),
            prazo_dias_etapa2=int(prazo_dias_etapa2_str),
            etapa_concluida=etapa_concluida_int
        )
        db.session.add(novo_orcamento)
        db.session.commit() # Commit para obter o ID

        # 5. Salva o Arquivo
        file = request.files['arquivo']
        safe_filename = secure_filename(file.filename)
        target_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(target_path)
        anexo = ArquivoAnexado( orcamento_id=novo_orcamento.id, nome_arquivo=safe_filename, caminho_arquivo=f"uploads/{safe_filename}")
        db.session.add(anexo)

        # 6. Processa e Cria as Tarefas (Etapa 1 e 2)
        giratorio_regex = re.compile(r"Giratório (\dL) (\d)E", re.IGNORECASE)
        
        todos_itens_para_processar = [
            (item, 1) for item in items_etapa1_list
        ] + [
            (item, 2) for item in items_etapa2_list
        ]

        for item_desc, etapa_num in todos_itens_para_processar:
            
            # --- Lógica Especial do Giratório ---
            match = giratorio_regex.match(item_desc)
            if match:
                linhas = match.group(1) # "1L" ou "2L"
                num_espetos = match.group(2) # "4", "5", etc.
                
                # Tarefa 1: Espetos (José)
                tarefa_espetos = TarefaProducao(
                    orcamento_id=novo_orcamento.id,
                    colaborador="José",
                    item_descricao=f"{num_espetos} Espetos Giratórios",
                    status='Não Iniciado',
                    etapa=2 # Giratório é sempre Etapa 2
                )
                db.session.add(tarefa_espetos)
                
                # Tarefa 2: Sistema (Luiz)
                tarefa_sistema = TarefaProducao(
                    orcamento_id=novo_orcamento.id,
                    colaborador="Luiz",
                    item_descricao=f"Giratório {linhas}",
                    status='Não Iniciado',
                    etapa=2
                )
                db.session.add(tarefa_sistema)
                
            else:
                # --- Lógica Padrão de Tarefas ---
                
                # Tenta achar o item exato no mapa
                colaborador = MAP_ITEM_COLABORADOR.get(item_desc)
                
                # Se não achou (ex: "KAM800 Dupla Face"), tenta achar a base
                if not colaborador:
                    for base_item, colab_mapeado in MAP_ITEM_COLABORADOR.items():
                        if item_desc.startswith(base_item):
                            colaborador = colab_mapeado
                            break
                
                # Se ainda não achou, é "Indefinido"
                if not colaborador:
                    colaborador = "Indefinido"
                    
                tarefa = TarefaProducao(
                    orcamento_id=novo_orcamento.id,
                    colaborador=colaborador,
                    item_descricao=item_desc,
                    status='Não Iniciado',
                    etapa=etapa_num
                )
                db.session.add(tarefa)

        # 7. Log e Notificação
        details = f"Usuário '{current_user.nome}' criou o orçamento manual '{novo_orcamento.numero}' para o cliente '{novo_orcamento.cliente}'."
        log_activity(novo_orcamento, "Criação Manual", details)
        db.session.commit()
        
        itens_str = novo_orcamento.etapa1_descricao if etapa_concluida_int == 0 else novo_orcamento.etapa2_descricao
        if not itens_str: itens_str = "Nenhum"
        
        message = f"📥 Novo Orçamento\n👤 Cliente: {numero} {cliente}\n\n📦 Itens ({'Etapa 1' if etapa_concluida_int == 0 else 'Etapa 2'}): {itens_str}"
        send_whatsapp_notification(message, [PHONE_ADMIN])
        
        return jsonify(novo_orcamento.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        print(f"Erro em create_orcamento_manual: {e}")
        return jsonify({"error": str(e)}), 500
# --- FIM da Rota de Criação Manual ---


# --- Rota de Upload ZIP (Lógica de Tarefas Removida, pois agora é manual) ---
@app.route('/api/upload', methods=['POST'])
@login_required
def upload_orcamento():
    if 'file' not in request.files: return jsonify({"error": "Nenhum arquivo enviado"}), 400
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.zip'): return jsonify({"error": "Arquivo inválido, envie um .zip"}), 400
    
    json_data = None
    pdf_files = []
    
    try:
        with zipfile.ZipFile(file, 'r') as zf:
            for filename in zf.namelist():
                if filename.endswith('.json'):
                    with zf.open(filename) as f: json_data = json.load(f)
                elif filename.endswith('.pdf'):
                    safe_filename = secure_filename(os.path.basename(filename))
                    target_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
                    with open(target_path, 'wb') as f: f.write(zf.read(filename))
                    pdf_files.append({"nome": safe_filename, "caminho": f"uploads/{safe_filename}"})
        
        if not json_data: return jsonify({"error": "Arquivo .json não encontrado no .zip"}), 400
        
        # Uploads ZIP não têm os novos campos de prazo, então ficam nulos
        novo_orcamento = Orcamento(
            numero=json_data.get('numero_orcamento', 'N/A'),
            cliente=json_data.get('nome_cliente', 'N/A'),
            grupo_id=1, 
            status_atual='Orçamento Aprovado',
            etapa1_descricao=json_data.get('itens_etapa_1', ''), # Mantido para referência
            etapa2_descricao=json_data.get('itens_etapa_2', ''), # Mantido para referência
            last_updated_by_id=current_user.id,
            etapa_concluida=0,
            # Prazos e telefones ficam nulos
        )
        db.session.add(novo_orcamento)
        db.session.commit()
        
        for pdf in pdf_files:
            anexo = ArquivoAnexado(orcamento_id=novo_orcamento.id, nome_arquivo=pdf['nome'], caminho_arquivo=pdf['caminho'])
            db.session.add(anexo)
        
        # A lógica de criar tarefas a partir do ZIP foi REMOVIDA
        # O usuário deve agora entrar manualmente e adicionar as tarefas
        
        details = f"Usuário '{current_user.nome}' fez upload do orçamento '{novo_orcamento.numero}' (Cliente: {novo_orcamento.cliente}) via .zip."
        log_activity(novo_orcamento, "Upload ZIP", details)
        db.session.commit()
        
        itens_str = novo_orcamento.etapa1_descricao or "Nenhum"
        message = f"📥 Novo Orçamento (ZIP)\n👤 Cliente: {novo_orcamento.numero} {novo_orcamento.cliente}\n\n📦 Itens (Etapa 1): {itens_str}\n\n(Tarefas devem ser adicionadas manualmente)"
        send_whatsapp_notification(message, [PHONE_ADMIN])
        
        return jsonify(novo_orcamento.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
# --- FIM da Rota de Upload ZIP ---


@app.route('/api/orcamento/<int:orc_id>/add_file', methods=['POST'])
@login_required
def add_file_to_orcamento(orc_id):
    orcamento = Orcamento.query.get(orc_id)
    if not orcamento: return jsonify({"error": "Orçamento não encontrado"}), 404
    if 'file' not in request.files: return jsonify({"error": "Nenhum arquivo enviado"}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({"error": "Nome de arquivo inválido"}), 400
    try:
        safe_filename = secure_filename(file.filename)
        target_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(target_path)
        anexo = ArquivoAnexado(orcamento_id=orcamento.id, nome_arquivo=safe_filename, caminho_arquivo=f"uploads/{safe_filename}")
        db.session.add(anexo)
        details = f"Usuário '{current_user.nome}' anexou o arquivo '{safe_filename}' ao orçamento '{orcamento.numero}'."
        log_activity(orcamento, "Anexo de Arquivo", details)
        db.session.commit()
        return jsonify(anexo.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/orcamento/<int:orc_id>/delete_file/<int:arquivo_id>', methods=['DELETE'])
@login_required
def delete_file_from_orcamento(orc_id, arquivo_id):
    orcamento = Orcamento.query.get(orc_id)
    if not orcamento:
        return jsonify({"error": "Orçamento não encontrado"}), 404
        
    arquivo = ArquivoAnexado.query.get(arquivo_id)
    if not arquivo or arquivo.orcamento_id != orc_id:
        return jsonify({"error": "Arquivo não encontrado ou não pertence a este orçamento"}), 404

    try:
        if arquivo.caminho_arquivo:
            caminho_abs = os.path.join(BASE_DIR, arquivo.caminho_arquivo)
            if os.path.exists(caminho_abs):
                os.remove(caminho_abs)
                print(f"Arquivo físico removido: {caminho_abs}")
            else:
                print(f"Aviso: Arquivo físico não encontrado em {caminho_abs}, mas a entrada do DB será removida.")

        nome_arquivo = arquivo.nome_arquivo
        db.session.delete(arquivo)
        
        details = f"Usuário '{current_user.nome}' excluiu o arquivo '{nome_arquivo}' do orçamento '{orcamento.numero}'."
        log_activity(orcamento, "Exclusão de Arquivo", details)
        
        db.session.commit()
        
        return jsonify({"success": True, "message": f"Arquivo '{nome_arquivo}' excluído com sucesso."})
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao deletar arquivo: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/uploads/<path:filename>')
@login_required
def get_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/static/<path:filename>')
def get_static_file(filename):
    return send_from_directory(STATIC_FOLDER, filename)


def parse_datetime(date_str):
    if not date_str: return None
    try: 
        # Tenta formatar datetime completo primeiro (para agendamentos)
        return datetime.fromisoformat(date_str)
    except ValueError:
        try: 
            # Tenta formatar apenas data (para datas limite, etc.)
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError: 
            return None

# --- ROTA DE STATUS ATUALIZADA ---
@app.route('/api/orcamento/<int:orc_id>/status', methods=['PUT'])
@login_required
def update_orcamento_status(orc_id):
    orcamento = Orcamento.query.get(orc_id)
    if not orcamento: return jsonify({"error": "Orçamento não encontrado"}), 404
    data = request.json
    novo_status = data.get('novo_status')
    dados_adicionais = data.get('dados_adicionais', {})
    status_antigo = orcamento.status_atual
    grupo_atual_id = orcamento.grupo_id
    orcamento.status_atual = novo_status
    grupos = {g.nome: g.id for g in Grupo.query.all()}
    g_entrada = grupos.get('Entrada de Orçamento')
    g_visitas = grupos.get('Visitas e Medidas')
    g_projetar = grupos.get('Projetar')
    g_producao = grupos.get('Linha de Produção')
    g_prontos = grupos.get('Prontos')
    g_standby = grupos.get('StandBy')
    g_instalados = grupos.get('Instalados')
    moveu_para_producao = False
    notification_message = None
    notification_recipients = []
    
    # Lógica de movimentação de grupo baseada na mudança de status
    
    if grupo_atual_id == g_entrada:
        notification_recipients = LISTA_GERAL
        notification_message = f"📋 Atualização de Orçamento\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n🔄 Mudou o status de: {status_antigo}\n➡️ Para: {novo_status}"
        
        if novo_status == 'Agendar Visita':
            orcamento.grupo_id = g_visitas
            orcamento.status_atual = 'Agendar Visita'
        elif novo_status == 'Mandar para Produção':
            orcamento.grupo_id = g_projetar
            orcamento.status_atual = 'Desenhar'
        elif novo_status == 'Standby':
            orcamento.grupo_id = g_standby
            orcamento.status_atual = 'Standby'
            orcamento.grupo_origem_standby = grupo_atual_id
            if dados_adicionais.get('standby_details'):
                orcamento.standby_details = dados_adicionais.get('standby_details')
            
    elif grupo_atual_id == g_visitas:
        if status_antigo == 'Visita Agendada' and novo_status != 'Visita Agendada':
            orcamento.data_visita = None
            orcamento.responsavel_visita = None
            
        if novo_status == 'Agendar Visita':
            if 'data_visita' in dados_adicionais and dados_adicionais.get('data_visita') is None:
                orcamento.data_visita = None
                orcamento.responsavel_visita = None
                details = f"Usuário '{current_user.nome}' cancelou o agendamento da visita para '{orcamento.numero}'."
                log_activity(orcamento, "Cancelamento de Visita", details)
        elif novo_status == 'Visita Agendada':
            orcamento.data_visita = parse_datetime(dados_adicionais.get('data_visita'))
            orcamento.responsavel_visita = dados_adicionais.get('responsavel_visita')
        elif novo_status == 'Mandar para Produção':
            orcamento.grupo_id = g_projetar
            orcamento.status_atual = 'Desenhar'
        elif novo_status == 'Standby':
            orcamento.grupo_id = g_standby
            orcamento.status_atual = 'Standby'
            orcamento.grupo_origem_standby = grupo_atual_id
            if dados_adicionais.get('standby_details'):
                orcamento.standby_details = dados_adicionais.get('standby_details')
                
    elif grupo_atual_id == g_projetar:
        if novo_status == 'Aprovado para Produção':
            orcamento.grupo_id = g_producao
            moveu_para_producao = True
        elif novo_status == 'StandBy':
            orcamento.grupo_id = g_standby
            orcamento.status_atual = 'Standby'
            orcamento.grupo_origem_standby = grupo_atual_id
            if dados_adicionais.get('standby_details'):
                orcamento.standby_details = dados_adicionais.get('standby_details')
            
    elif grupo_atual_id == g_producao:
        if novo_status == 'StandBy':
            orcamento.grupo_id = g_standby
            orcamento.status_atual = 'Standby'
            orcamento.grupo_origem_standby = grupo_atual_id
            if dados_adicionais.get('standby_details'):
                orcamento.standby_details = dados_adicionais.get('standby_details')
            
    elif grupo_atual_id == g_prontos:
        if status_antigo == 'Instalação Agendada' and novo_status != 'Instalação Agendada':
            orcamento.data_instalacao = None
            orcamento.responsavel_instalacao = None
            
        if novo_status == 'Instalação Agendada':
            orcamento.data_instalacao = parse_datetime(dados_adicionais.get('data_instalacao'))
            orcamento.responsavel_instalacao = dados_adicionais.get('responsavel_instalacao')
        
        elif novo_status == 'Agendar Instalação/Entrega':
            if 'data_instalacao' in dados_adicionais and dados_adicionais.get('data_instalacao') is None:
                orcamento.data_instalacao = None
                orcamento.responsavel_instalacao = None
                details = f"Usuário '{current_user.nome}' cancelou o agendamento da instalação para '{orcamento.numero}'."
                log_activity(orcamento, "Cancelamento de Instalação", details)
        
        elif novo_status == 'Entregue':
            orcamento.grupo_id = g_instalados
            orcamento.status_atual = 'Instalado'
            orcamento.etapa_concluida = 2
            notification_message = f"🚚 Entrega Concluída!\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n📦 O pedido foi marcado como 'Entregue' e movido para 'Instalados' (Etapa Final)."
            notification_recipients = LISTA_GERAL

        elif novo_status == 'StandBy':
            orcamento.grupo_id = g_standby
            orcamento.status_atual = 'Standby'
            orcamento.grupo_origem_standby = grupo_atual_id
            if dados_adicionais.get('standby_details'):
                orcamento.standby_details = dados_adicionais.get('standby_details')
            
        elif novo_status == 'Instalado':
            etapa = dados_adicionais.get('etapa_instalada')
            if etapa == 'Etapa 1':
                orcamento.grupo_id = g_visitas
                orcamento.status_atual = 'Agendar Visita'
                orcamento.etapa_concluida = 1
            elif etapa == 'Etapa 2':
                orcamento.grupo_id = g_instalados
                orcamento.status_atual = 'Instalado'
                orcamento.etapa_concluida = 2
                
    elif grupo_atual_id == g_standby:
        notification_recipients = LISTA_GERAL
        
        if novo_status == 'Agendar visita':
            notification_message = f"🔄 Orçamento Liberado (Standby)\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n➡️ Movido para: Visitas e Medidas (Agendar Visita)"
            orcamento.grupo_id = g_visitas
            orcamento.status_atual = 'Agendar Visita'
            orcamento.grupo_origem_standby = None
            orcamento.standby_details = None
        elif novo_status == 'Mandar para Produção':
            notification_message = f"🔄 Orçamento Liberado (Standby)\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n➡️ Movido para: Projetar (Desenhar)"
            orcamento.grupo_id = g_projetar
            orcamento.status_atual = 'Desenhar'
            orcamento.grupo_origem_standby = None
            orcamento.standby_details = None
        elif novo_status == 'Instalar':
            notification_message = f"🔄 Orçamento Liberado (Standby)\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n➡️ Movido para: Prontos (Agendar Instalação)"
            orcamento.grupo_id = g_prontos
            orcamento.status_atual = 'Agendar Instalação/Entrega'
            orcamento.grupo_origem_standby = None
            orcamento.standby_details = None
        
        elif novo_status == 'Liberado':
            notification_message = f"🔄 Atualização de Status\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n📍 Mudou o status de: {status_antigo}\n➡️ Para: {novo_status}"
            if orcamento.grupo_origem_standby: orcamento.grupo_id = orcamento.grupo_origem_standby
            else: orcamento.grupo_id = g_entrada
            orcamento.grupo_origem_standby = None
            orcamento.standby_details = None
        
        elif novo_status != 'Standby':
             notification_message = f"🔄 Atualização de Status\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n📍 Mudou o status de: {status_antigo}\n➡️ Para: {novo_status}"
            
    elif grupo_atual_id == g_instalados:
        notification_recipients = LISTA_GERAL
        notification_message = f"🔄 Atualização de Status\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n📍 Mudou o status de: {status_antigo}\n➡️ Para: {novo_status}"
    
    if moveu_para_producao:
        data_visita_str = dados_adicionais.get('data_visita')
        if data_visita_str:
            data_visita_obj = parse_datetime(data_visita_str)
            orcamento.data_entrada_producao = data_visita_obj
            
            current_etapa_num = orcamento.etapa_concluida + 1
            if current_etapa_num == 1:
                orcamento.data_visita = data_visita_obj 
            else:
                orcamento.data_visita_etapa2 = data_visita_obj
            
            try:
                if orcamento.prazo_dias_etapa1:
                    orcamento.data_limite_etapa1 = data_visita_obj + timedelta(days=int(orcamento.prazo_dias_etapa1))
                if orcamento.prazo_dias_etapa2:
                    orcamento.data_limite_etapa2 = data_visita_obj + timedelta(days=int(orcamento.prazo_dias_etapa2))
            except Exception as e:
                print(f"Erro ao calcular datas limite: {e}")
        
        current_etapa = 2 if orcamento.etapa_concluida >= 1 else 1
        for tarefa in orcamento.tarefas:
            if tarefa.etapa == current_etapa:
                tarefa.status = 'Não Iniciado'
                
    try:
        log_cancelamento = (
            (grupo_atual_id == g_visitas and novo_status == 'Agendar Visita' and 'data_visita' in dados_adicionais) or
            (grupo_atual_id == g_prontos and novo_status == 'Agendar Instalação/Entrega' and 'data_instalacao' in dados_adicionais)
        )
        if not log_cancelamento:
            details = f"Usuário '{current_user.nome}' alterou o status do orçamento '{orcamento.numero}' de '{status_antigo}' para '{novo_status}'."
            if 'standby_details' in dados_adicionais and dados_adicionais.get('standby_details'):
                details += f" Motivo: {dados_adicionais.get('standby_details')}"
            log_activity(orcamento, "Mudança de Status (Orçamento)", details)
        
        db.session.commit()
        
        if notification_message and (grupo_atual_id == g_entrada or grupo_atual_id == g_standby) and orcamento.grupo_id != grupo_atual_id:
            grupo_novo_nome = orcamento.grupo.nome
            if "Movido para" not in notification_message:
                notification_message = f"📋 Atualização de Orçamento\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n🔄 Mudou o status de: {status_antigo}\n➡️ Para: {novo_status}\n📁 E foi movido para o grupo: {grupo_novo_nome}"
        if novo_status == 'Visita Agendada':
            data_visita_fmt = orcamento.data_visita.strftime('%d/%m %H:%M') if orcamento.data_visita else 'N/A'
            notification_message = f"📆 Visita Agendada!\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n📍 Data: {data_visita_fmt}\n👷 Responsável: {orcamento.responsavel_visita}"
            notification_recipients = LISTA_GERAL
        elif novo_status == 'Instalação Agendada':
            data_inst_fmt = orcamento.data_instalacao.strftime('%d/%m %H:%M') if orcamento.data_instalacao else 'N/A'
            notification_message = f"🔧 Instalação Agendada!\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n📍 Data: {data_inst_fmt}\n👷 Responsável: {orcamento.responsavel_instalacao}"
            notification_recipients = LISTA_GERAL
        elif novo_status == 'Instalado' and (grupo_atual_id == g_visitas or grupo_atual_id == g_prontos):
            etapa = dados_adicionais.get('etapa_instalada', 'N/A')
            etapa_num = "1ª" if etapa == 'Etapa 1' else "2ª"
            resp_inst = orcamento.responsavel_instalacao or 'N/A'
            notification_message = f"🎉 Instalação Concluída!\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n🔧 Etapa: {etapa_num} Etapa\n👷 Responsável: {resp_inst}"
            if etapa == 'Etapa 1': notification_message += "\n\n📁 Movido para Visitas e Medidas — agendar a visita para medidas da segunda etapa."
            notification_recipients = LISTA_GERAL
            
        if notification_message and notification_recipients:
            send_whatsapp_notification(notification_message, notification_recipients)
            
        return jsonify(orcamento.to_dict())
    except Exception as e:
        db.session.rollback()
        print(f"Erro em update_orcamento_status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tarefa/<int:tarefa_id>/status', methods=['PUT'])
@login_required
def update_tarefa_status(tarefa_id):
    tarefa = TarefaProducao.query.get(tarefa_id)
    if not tarefa: return jsonify({"error": "Tarefa não encontrada"}), 404
    
    novo_status = request.json.get('status')
    orcamento = tarefa.orcamento
    notification_message = None

    colaborador_alvo = tarefa.colaborador
    etapa_alvo = tarefa.etapa
    
    tarefas_do_colaborador_na_etapa = TarefaProducao.query.filter_by(
        orcamento_id=orcamento.id,
        colaborador=colaborador_alvo,
        etapa=etapa_alvo
    ).all()
    
    details = f"Usuário '{current_user.nome}' alterou o status das tarefas de '{colaborador_alvo}' (Etapa {etapa_alvo}) para '{novo_status}' no orçamento '{orcamento.numero}'."
    log_activity(orcamento, "Mudança de Status (Tarefa Agrupada)", details)

    for t in tarefas_do_colaborador_na_etapa:
        t.status = novo_status
    
    db.session.commit()

    tarefas_da_etapa_atual = [t for t in orcamento.tarefas if t.etapa == etapa_alvo]
    
    todas_prontas = True
    if not tarefas_da_etapa_atual: 
        todas_prontas = False
    else:
        for t in tarefas_da_etapa_atual:
            if t.status != 'Produção Finalizada':
                todas_prontas = False
                break
                
    if todas_prontas:
        grupo_prontos = Grupo.query.filter_by(nome='Prontos').first()
        if grupo_prontos and orcamento.grupo_id != grupo_prontos.id:
            orcamento.grupo_id = grupo_prontos.id
            orcamento.data_pronto = datetime.utcnow()
            orcamento.status_atual = 'Agendar Instalação/Entrega' 
            details_auto = f"Sistema moveu o orçamento '{orcamento.numero}' para 'Prontos' pois todas as tarefas da Etapa {etapa_alvo} foram finalizadas."
            log_activity(orcamento, "Movimentação Automática", details_auto)
            db.session.commit()
            
    itens_desc_agrupados = ", ".join(list(set([t.item_descricao for t in tarefas_do_colaborador_na_etapa if t.item_descricao])))
    
    if novo_status == 'Iniciou a Produção': notification_message = f"⚙️ Início de Produção\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n🧑‍🏭 Responsável: {colaborador_alvo}\n🚀 Itens iniciados: {itens_desc_agrupados}"
    elif novo_status == 'Fase de Acabamento': notification_message = f"🛠️ Atualização de Produção\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n🧑‍🏭 Responsável: {colaborador_alvo}\n🎨 Itens em fase de acabamento: {itens_desc_agrupados}"
    elif novo_status == 'Produção Finalizada':
        notification_message = f"✅ Produção Concluída!\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n🧑‍🏭 Responsável: {colaborador_alvo}\n📦 Itens finalizados: {itens_desc_agrupados}"
        if todas_prontas: notification_message += f"\n\n📁 Todas as tarefas da Etapa {etapa_alvo} concluídas. Movido para 'Prontos'.\n📅 Agende uma data de instalação ou entrega."
    elif novo_status == 'Aguardando Vidro / Pedra': notification_message = f"📦 Aguardando Materiais\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n🧑‍🏭 Responsável: {colaborador_alvo}\n🪟 Situação: Aguardando vidro/pedra para iniciar a produçã."
    elif novo_status == 'Reforma em Andamento': notification_message = f"🔨 Reforma em Andamento\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n🧑‍🏭 Responsável: {colaborador_alvo}\n🔁 Situação: Reforma em andamento na linha de produçã."
    elif novo_status == 'StandBy': notification_message = f"⏸️ Produção em StandBy\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n🧑‍🏭 Responsável: {colaborador_alvo}\n📦 Situação: Projeto pausado temporariamente."
    
    if notification_message:
        send_whatsapp_notification(notification_message, LISTA_GERAL)
        
    return jsonify(orcamento.to_dict())

@app.route('/api/orcamento/<int:orc_id>/move', methods=['PUT'])
@login_required
def move_orcamento(orc_id):
    orcamento = Orcamento.query.get(orc_id)
    if not orcamento: return jsonify({"error": "Orçamento não encontrado"}), 404
    data = request.json
    novo_grupo_id = int(data.get('novo_grupo_id'))
    if orcamento.grupo_id == novo_grupo_id: return jsonify(orcamento.to_dict())
    grupo_antigo_nome = orcamento.grupo.nome
    grupo_destino = Grupo.query.get(novo_grupo_id)
    if not grupo_destino: return jsonify({"error": "Grupo de destino não encontrado"}), 404
    grupo_novo_nome = grupo_destino.nome
    orcamento.grupo_id = novo_grupo_id

    if data.get('cancel_existing_dates'):
        orcamento.data_visita = None
        orcamento.responsavel_visita = None
        orcamento.data_instalacao = None
        orcamento.responsavel_instalacao = None

    if grupo_destino.nome == 'Entrada de Orçamento': orcamento.status_atual = 'Orçamento Aprovado'
    elif grupo_destino.nome == 'Visitas e Medidas': orcamento.status_atual = 'Agendar Visita'
    elif grupo_destino.nome == 'Projetar':
        orcamento.status_atual = 'Desenhar'
    
    elif grupo_destino.nome == 'Linha de Produção':
        orcamento.status_atual = 'Não Iniciado'
        data_visita_str = data.get('data_visita')
        if data_visita_str:
            data_visita_obj = parse_datetime(data_visita_str)
            orcamento.data_entrada_producao = data_visita_obj
            
            current_etapa_num = orcamento.etapa_concluida + 1
            if current_etapa_num == 1:
                orcamento.data_visita = data_visita_obj 
            else:
                orcamento.data_visita_etapa2 = data_visita_obj
            
            try:
                if orcamento.prazo_dias_etapa1:
                    orcamento.data_limite_etapa1 = data_visita_obj + timedelta(days=int(orcamento.prazo_dias_etapa1))
                if orcamento.prazo_dias_etapa2:
                    orcamento.data_limite_etapa2 = data_visita_obj + timedelta(days=int(orcamento.prazo_dias_etapa2))
            except Exception as e:
                print(f"Erro ao calcular datas limite (move): {e}")

        current_etapa = 2 if orcamento.etapa_concluida >= 1 else 1
        for tarefa in orcamento.tarefas:
            if tarefa.etapa == current_etapa:
                tarefa.status = 'Não Iniciado'
                
    elif grupo_destino.nome == 'Prontos':
        orcamento.status_atual = 'Agendar Instalação/Entrega' 
        if not orcamento.data_pronto: orcamento.data_pronto = datetime.utcnow()
    elif grupo_destino.nome == 'StandBy':
        orcamento.status_atual = 'Standby'
        if orcamento.grupo_origem_standby is None:
            grupo_antigo_id = Grupo.query.filter_by(nome=grupo_antigo_nome).first().id
            orcamento.grupo_origem_standby = grupo_antigo_id
        if data.get('standby_details'):
            orcamento.standby_details = data.get('standby_details')
            
    elif grupo_destino.nome == 'Instalados': orcamento.status_atual = 'Instalado'
    
    details = f"Usuário '{current_user.nome}' moveu o orçamento '{orcamento.numero}' do grupo '{grupo_antigo_nome}' para '{grupo_novo_nome}'."
    log_activity(orcamento, "Movimentação de Grupo", details)
    db.session.commit()
    message = f"↔️ Item Movido Manualmente\n👤 Cliente: {orcamento.numero} {orcamento.cliente}\n\n📁 Movido de: {grupo_antigo_nome}\n➡️ Para: {grupo_novo_nome}"
    send_whatsapp_notification(message, LISTA_GERAL)
    return jsonify(orcamento.to_dict())

@app.route('/api/orcamento/<int:orc_id>/add_tarefa', methods=['POST'])
@login_required
def add_tarefa_to_orcamento(orc_id):
    orcamento = Orcamento.query.get(orc_id)
    if not orcamento: return jsonify({"error": "Orçamento não encontrado"}), 404
    data = request.json
    colaborador = data.get('colaborador')
    item_descricao = data.get('item_descricao')
    if not colaborador or not item_descricao: return jsonify({"error": "Colaborador e Item são obrigatórios"}), 400
    try:
        current_etapa = 2 if orcamento.etapa_concluida >= 1 else 1
        
        nova_tarefa = TarefaProducao(
            orcamento_id=orc_id, 
            colaborador=colaborador, 
            item_descricao=item_descricao, 
            status='Não Iniciado',
            etapa=current_etapa
        )
        db.session.add(nova_tarefa)
        details = f"Usuário '{current_user.nome}' adicionou a tarefa '{item_descricao}' (Colab: {colaborador}, Etapa: {current_etapa}) ao orçamento '{orcamento.numero}'."
        log_activity(orcamento, "Adição de Tarefa", details)
        db.session.commit()
        return jsonify(nova_tarefa.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- Scheduler para Limpeza de Logs ---
scheduler = APScheduler()
@scheduler.task('cron', id='delete_old_logs', day_of_week='*', hour=3)
def delete_old_logs():
    with app.app_context():
        try:
            cutoff = datetime.utcnow() - timedelta(days=30)
            logs_deleted = ActivityLog.query.filter(ActivityLog.timestamp < cutoff).delete()
            db.session.commit()
            print(f"Limpeza de logs: {logs_deleted} logs antigos foram removidos.")
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao limpar logs antigos: {e}")

# --- Comandos de CLI ---
@app.cli.command('init-db')
def init_db_command():
    if not os.path.exists(INSTANCE_FOLDER):
        os.makedirs(INSTANCE_FOLDER)
        print(f"Pasta 'instance' criada em: {INSTANCE_FOLDER}")
    db.drop_all()
    db.create_all()
    g1 = Grupo(nome='Entrada de Orçamento', ordem=1)
    g2 = Grupo(nome='Visitas e Medidas', ordem=2)
    g3 = Grupo(nome='Projetar', ordem=3)
    g4 = Grupo(nome='Linha de Produção', ordem=4)
    g5 = Grupo(nome='Prontos', ordem=5)
    g6 = Grupo(nome='StandBy', ordem=6)
    g7 = Grupo(nome='Instalados', ordem=7)
    db.session.add_all([g1, g2, g3, g4, g5, g6, g7])
    if not User.query.filter_by(email='admin@admin.com').first():
        admin = User(nome='Admin', email='admin@admin.com')
        admin.set_password('admin')
        db.session.add(admin)
    db.session.commit()
    print('Banco de dados inicializado, grupos (7) criados e usuário admin (admin@admin.com / admin) criado.')

def setup_database(app_context):
    with app_context.app_context():
        if not os.path.exists(INSTANCE_FOLDER):
            os.makedirs(INSTANCE_FOLDER)
            print(f"Pasta 'instance' criada em: {INSTANCE_FOLDER}")
        db.create_all() 
        if not Grupo.query.first():
            g1 = Grupo(nome='Entrada de Orçamento', ordem=1)
            g2 = Grupo(nome='Visitas e Medidas', ordem=2)
            g3 = Grupo(nome='Projetar', ordem=3)
            g4 = Grupo(nome='Linha de Produção', ordem=4)
            g5 = Grupo(nome='Prontos', ordem=5)
            g6 = Grupo(nome='StandBy', ordem=6)
            g7 = Grupo(nome='Instalados', ordem=7)
            db.session.add_all([g1, g2, g3, g4, g5, g6, g7])
            if not User.query.filter_by(email='admin@admin.com').first():
                admin = User(nome='Admin', email='admin@admin.com')
                admin.set_password('admin')
                db.session.add(admin)
            db.session.commit()
            print("DB, Grupos e Admin User criados.")

# --- Lógica do Bot ---

def formatar_data_bot(data_obj):
    if not data_obj:
        return ""
    if data_obj.hour == 0 and data_obj.minute == 0:
        return data_obj.strftime('%d/%m/%Y')
    return data_obj.strftime('%d/%m às %H:%M')

def format_orcamento_status_bot(orcamento):
    try:
        etapa_str = f"Etapa {orcamento.etapa_concluida + 1}"
        grupo_nome = orcamento.grupo.nome
        
        log_criacao = ActivityLog.query.filter(
            ActivityLog.orcamento_id == orcamento.id,
            or_(ActivityLog.action == "Criação Manual", ActivityLog.action == "Upload ZIP")
        ).order_by(ActivityLog.timestamp.asc()).first()
        
        data_entrada = "Não encontrada"
        if log_criacao:
            data_entrada = log_criacao.timestamp.strftime('%d/%m/%Y')
        
        header = f"Status Orçamento 📋\n\n👤 *Cliente:* {orcamento.numero} - {orcamento.cliente}\n🗓️ *Entrada:* {data_entrada}\n🏁 *Etapa:* {etapa_str}\n📍 *Status:* {grupo_nome}"
        
        detalhes = []

        if grupo_nome == "Entrada de Orçamento":
            detalhes.append(f"ℹ️ *Info:* Aguardando definição da próxima fase (visita ou projeto).")
        
        elif grupo_nome == "Visitas e Medidas":
            if orcamento.status_atual == "Agendar Visita":
                detalhes.append(f"⏳ *Ação:* Aguardando agendamento da visita técnica.")
            elif orcamento.status_atual == "Visita Agendada":
                # Lógica de data de visita E1 ou E2
                data_visita_usada = orcamento.data_visita_etapa2 if orcamento.etapa_concluida >= 1 else orcamento.data_visita
                if data_visita_usada:
                    data_visita_fmt = formatar_data_bot(data_visita_usada)
                    detalhes.append(f"✅ *Agendado:* Visita marcada para {data_visita_fmt}.")
                else:
                    detalhes.append(f"ℹ️ *Info:* Em processo de medição e visita (data não registrada).")
            else:
                detalhes.append(f"ℹ️ *Info:* Em processo de medição e visita.")

        elif grupo_nome == "Projetar":
            detalhes.append(f"✍️ *Info:* Orçamento em fase de desenho e projeto técnico.")

        elif grupo_nome == "Linha de Produção":
            data_limite_prod = orcamento.data_limite_etapa2 if orcamento.etapa_concluida >= 1 else orcamento.data_limite_etapa1
                
            if data_limite_prod:
                detalhes.append(f"🚩 *Prazo Final:* {data_limite_prod.strftime('%d/%m/%Y')}")
            
            current_etapa_num = orcamento.etapa_concluida + 1
            tarefas_iniciadas = [t.item_descricao for t in orcamento.tarefas if t.etapa == current_etapa_num and t.status == "Iniciou a Produção" and t.item_descricao]
            tarefas_nao_iniciadas = [t.item_descricao for t in orcamento.tarefas if t.etapa == current_etapa_num and t.status == "Não Iniciado" and t.item_descricao]
            
            if tarefas_iniciadas:
                itens_str = ", ".join(tarefas_iniciadas)
                detalhes.append(f"⚙️ *Em Produção:* {itens_str}")
            
            if tarefas_nao_iniciadas:
                itens_str = ", ".join(tarefas_nao_iniciadas)
                detalhes.append(f"⏳ *Aguardando Início:* {itens_str}")
            
            if not tarefas_iniciadas and not tarefas_nao_iniciadas:
                outras_tarefas = [t for t in orcamento.tarefas if t.etapa == current_etapa_num and t.item_descricao]
                if not outras_tarefas:
                    detalhes.append(f"⏳ *Aguardando:* Nenhuma tarefa cadastrada para esta etapa.")
                else:
                    detalhes.append(f"ℹ️ *Info:* Itens em outras fases (Ex: Acabamento, StandBy).")


        elif grupo_nome == "Prontos":
            data_limite_prod = orcamento.data_limite_etapa1 if orcamento.etapa_concluida == 0 else orcamento.data_limite_etapa2
                
            if data_limite_prod:
                detalhes.append(f"🚩 *Prazo Final:* {data_limite_prod.strftime('%d/%m/%Y')}")
            
            etapa_pronta = 1 if orcamento.etapa_concluida == 0 else 2
            tarefas_prontas = [t.item_descricao for t in orcamento.tarefas if t.etapa == etapa_pronta and t.item_descricao]
            itens_str = ", ".join(sorted(list(set(tarefas_prontas)))) or "Itens"
            
            detalhes.append(f"📦 *Itens Prontos:* {itens_str}")
            
            if orcamento.status_atual == "Agendar Instalação/Entrega":
                detalhes.append(f"🗓️ *Ação:* Aguardando agendamento da instalação.")
            
            elif orcamento.status_atual == "Instalação Agendada" and orcamento.data_instalacao:
                data_inst_fmt = formatar_data_bot(orcamento.data_instalacao)
                resp_inst = orcamento.responsavel_instalacao or "Equipe"
                detalhes.append(f"✅ *Instalação:* Marcada para {data_inst_fmt} por {resp_inst}.")
                
            elif orcamento.status_atual == "Entregue":
                detalhes.append(f"🚚 *Ação:* Pedido sendo movido para Instalados.")

        elif grupo_nome == "Instalados":
            detalhes.append(f"🎉 *Finalizado!* O projeto foi concluído e instalado.")

        elif grupo_nome == "StandBy":
            detalhes.append(f"⏸️ *Pausado:* Projeto em StandBy (Status: {orcamento.status_atual})")
            if orcamento.standby_details:
                detalhes.append(f"📝 *Motivo:* {orcamento.standby_details}")

        final_message = header
        if detalhes:
            final_message += "\n\n*Detalhes:*\n" + "\n".join(detalhes)
        
        update_info = "\n\n_Nenhuma atualização registrada._"
        if orcamento.last_updated_at:
            data_att = orcamento.last_updated_at.strftime('%d/%m/%Y às %H:%M')
            user_nome = "Sistema"
            if orcamento.last_update_user:
                user_nome = orcamento.last_update_user.nome
            elif orcamento.last_updated_by_id:
                user = db.session.get(User, orcamento.last_updated_by_id)
                if user:
                    user_nome = user.nome
            
            update_info = f"\n\n_Última atualização: {data_att} Por: {user_nome}_"
        
        final_message += update_info
        
        return final_message

    except Exception as e:
        print(f"[ERRO no format_orcamento_status_bot]: {e}")
        return f"Erro ao processar o orçamento {orcamento.numero}. Verifique os logs do app."

@app.route('/api/bot/query', methods=['GET'])
def bot_query_endpoint():
    query = request.args.get('texto')
    remetente_id = request.args.get('remetente')

    if not query:
        return jsonify({"respostas": []})

    if remetente_id not in AUTHORIZED_BOT_NUMBERS:
        print(f"Bot Query: Número não autorizado: {remetente_id}. Ignorando.")
        return jsonify({"respostas": ["Desculpe, seu número não está autorizado a fazer consultas."]})

    try:
        orcamentos = Orcamento.query.filter(
            or_(
                Orcamento.numero.ilike(f"%{query}%"),
                Orcamento.cliente.ilike(f"%{query}%")
            )
        ).all()

        response_messages = []
        if not orcamentos:
            pass
        else:
            for orc in orcamentos:
                response_messages.append(format_orcamento_status_bot(orc))
        
        return jsonify({"respostas": response_messages})

    except Exception as e:
        print(f"[ERRO no /api/bot/query]: {e}")
        return jsonify({"respostas": ["Ocorreu um erro interno ao consultar o banco de dados."]}), 500


@app.route('/api/bot/prontos', methods=['GET'])
def bot_prontos_query():
    remetente_id = request.args.get('remetente')
    if remetente_id not in AUTHORIZED_BOT_NUMBERS:
        return jsonify({"resposta": "Desculpe, seu número não está autorizado a fazer consultas."})

    try:
        grupo_prontos = Grupo.query.filter_by(nome='Prontos').first()
        if not grupo_prontos:
            return jsonify({"resposta": "Grupo 'Prontos' não encontrado no sistema."})

        orcamentos = Orcamento.query.filter_by(grupo_id=grupo_prontos.id).order_by(Orcamento.data_pronto.asc()).all()

        if not orcamentos:
            return jsonify({"resposta": "Nenhum orçamento no grupo 'Prontos' no momento."})

        resposta = "📦 *Orçamentos Prontos*\n"
        for orc in orcamentos:
            data_entrada_str = "N/D"
            if orc.data_entrada_producao:
                data_entrada_str = orc.data_entrada_producao.strftime('%d/%m')
            else:
                log_criacao = ActivityLog.query.filter(
                    ActivityLog.orcamento_id == orc.id,
                    or_(ActivityLog.action == "Criação Manual", ActivityLog.action == "Upload ZIP")
                ).order_by(ActivityLog.timestamp.asc()).first()
                if log_criacao:
                    data_entrada_str = log_criacao.timestamp.strftime('%d/%m')
            
            status_str = "aguardando agendar a data de instalação."
            if orc.status_atual == 'Instalação Agendada' and orc.data_instalacao:
                status_str = f"com instalação agendada para {formatar_data_bot(orc.data_instalacao)}."
            elif orc.status_atual == 'Entregue':
                status_str = "marcado como 'Entregue'."

            resposta += f"\n• *{orc.numero}-{orc.cliente}* (entrou {data_entrada_str}) - {status_str}"

        return jsonify({"resposta": resposta})
    except Exception as e:
        print(f"[ERRO no /api/bot/prontos]: {e}")
        return jsonify({"resposta": "Ocorreu um erro interno ao consultar orçamentos prontos."}), 500

@app.route('/api/bot/atrasados', methods=['GET'])
def bot_atrasados_query():
    remetente_id = request.args.get('remetente')
    if remetente_id not in AUTHORIZED_BOT_NUMBERS:
        return jsonify({"resposta": "Desculpe, seu número não está autorizado a fazer consultas."})

    try:
        dias_str = request.args.get('dias', '7')
        dias = int(dias_str)
        
        grupo_prod = Grupo.query.filter_by(nome='Linha de Produção').first()
        if not grupo_prod:
            return jsonify({"resposta": "Grupo 'Linha de Produção' não encontrado."})

        hoje = datetime.utcnow().date()
        target_date = hoje + timedelta(days=dias)

        orcamentos = Orcamento.query.filter(
            Orcamento.grupo_id == grupo_prod.id,
            or_(
                (Orcamento.etapa_concluida == 0) & (Orcamento.data_limite_etapa1 != None) & (func.date(Orcamento.data_limite_etapa1) <= target_date),
                (Orcamento.etapa_concluida == 1) & (Orcamento.data_limite_etapa2 != None) & (func.date(Orcamento.data_limite_etapa2) <= target_date)
            )
        ).all()
        
        def get_sort_date(o):
            return o.data_limite_etapa2 if o.etapa_concluida >= 1 else o.data_limite_etapa1
        
        orcamentos_ordenados = sorted(orcamentos, key=get_sort_date)

        if not orcamentos_ordenados:
            return jsonify({"resposta": f"Nenhum orçamento em produção com data limite nos próximos {dias} dias (ou já atrasado)."})

        resposta = f"🚨 *Orçamentos Atrasados ou Vencendo (Próximos {dias} dias)*\n"
        
        for orc in orcamentos_ordenados:
            prazo_dt = get_sort_date(orc)
            prazo_fmt = prazo_dt.strftime('%d/%m/%Y')
            etapa_num = orc.etapa_concluida + 1
            
            status_prazo = "(Atrasado)" if prazo_dt.date() < hoje else "(Vence em breve)"
            
            resposta += f"\n\n---"
            resposta += f"\n👤 *{orc.numero}-{orc.cliente}* (Etapa {etapa_num})"
            resposta += f"\n🚩 *Prazo:* {prazo_fmt} {status_prazo}"

            tarefas_finalizadas = [t.item_descricao for t in orc.tarefas if t.etapa == etapa_num and t.status == 'Produção Finalizada' and t.item_descricao]
            tarefas_pendentes = [f"{t.item_descricao} ({t.status})" for t in orc.tarefas if t.etapa == etapa_num and t.status != 'Produção Finalizada' and t.item_descricao]

            if tarefas_finalizadas:
                resposta += "\n✅ *Finalizados:* " + ", ".join(sorted(list(set(tarefas_finalizadas))))
            if tarefas_pendentes:
                resposta += "\n⏳ *Pendentes:* " + ", ".join(sorted(list(set(tarefas_pendentes))))
            if not tarefas_finalizadas and not tarefas_pendentes:
                resposta += "\nℹ️ _Nenhuma tarefa registrada para esta etapa._"
        
        return jsonify({"resposta": resposta})
    except Exception as e:
        print(f"[ERRO no /api/bot/atrasados]: {e}")
        return jsonify({"resposta": "Ocorreu um erro interno ao consultar orçamentos atrasados."}), 500

@app.route('/api/bot/agenda', methods=['GET'])
def bot_agenda_query():
    remetente_id = request.args.get('remetente')
    if remetente_id not in AUTHORIZED_BOT_NUMBERS:
        return jsonify({"resposta": "Desculpe, seu número não está autorizado a fazer consultas."})

    try:
        hoje_data = datetime.utcnow().date()
        
        visitas = Orcamento.query.filter(
            Orcamento.data_visita != None,
            func.date(Orcamento.data_visita) >= hoje_data,
            Orcamento.grupo.has(Grupo.nome != 'Instalados')
        ).order_by(Orcamento.data_visita.asc()).all()
        
        # ATUALIZAÇÃO: Adiciona busca por visita etapa 2
        visitas_e2 = Orcamento.query.filter(
            Orcamento.data_visita_etapa2 != None,
            func.date(Orcamento.data_visita_etapa2) >= hoje_data,
            Orcamento.grupo.has(Grupo.nome != 'Instalados')
        ).order_by(Orcamento.data_visita_etapa2.asc()).all()
        
        instalacoes = Orcamento.query.filter(
            Orcamento.data_instalacao != None,
            func.date(Orcamento.data_instalacao) >= hoje_data,
            Orcamento.grupo.has(Grupo.nome != 'Instalados')
        ).order_by(Orcamento.data_instalacao.asc()).all()

        if not visitas and not instalacoes and not visitas_e2:
            return jsonify({"resposta": "Nenhum evento (visita ou instalação) agendado para os próximos dias."})

        resposta = "🗓️ *Agenda de Eventos Futuros*\n"
        
        if visitas:
            resposta += "\n\n*--- 📅 Visitas Agendadas (Etapa 1) ---*"
            for v in visitas:
                data_fmt = formatar_data_bot(v.data_visita)
                resp = v.responsavel_visita or "N/D"
                resposta += f"\n• *{v.numero}-{v.cliente}* (Etapa 1)\n  └ Visita: {data_fmt} (Resp: {resp})"
        
        if visitas_e2:
            resposta += "\n\n*--- 📅 Visitas Agendadas (Etapa 2) ---*"
            for v in visitas_e2:
                data_fmt = formatar_data_bot(v.data_visita_etapa2)
                resp = v.responsavel_visita or "N/D" # Reutiliza o campo
                resposta += f"\n• *{v.numero}-{v.cliente}* (Etapa 2)\n  └ Visita: {data_fmt} (Resp: {resp})"

        if instalacoes:
             resposta += "\n\n*--- 🔧 Instalações Agendadas ---*"
             for i in instalacoes:
                data_fmt = formatar_data_bot(i.data_instalacao)
                resp = i.responsavel_instalacao or "N/D"
                etapa = i.etapa_concluida + 1
                resposta += f"\n• *{i.numero}-{i.cliente}* (Etapa {etapa})\n  └ Instalação: {data_fmt} (Resp: {resp})"
        
        return jsonify({"resposta": resposta})
    except Exception as e:
        print(f"[ERRO no /api/bot/agenda]: {e}")
        return jsonify({"resposta": "Ocorreu um erro interno ao consultar a agenda."}), 500

def format_orcamentos_por_grupo(grupo_nome):
    try:
        grupo = Grupo.query.filter_by(nome=grupo_nome).first()
        if not grupo:
            return f"Erro: O grupo '{grupo_nome}' não foi encontrado no sistema."

        orcamentos = Orcamento.query.options(
            joinedload(Orcamento.tarefas)
        ).filter_by(grupo_id=grupo.id).order_by(Orcamento.last_updated_at.desc()).all()


        if not orcamentos:
            return f"Nenhum orçamento encontrado no grupo *{grupo_nome}* no momento."

        emoji_map = {
            "Entrada de Orçamento": "📥",
            "Visitas e Medidas": "📅",
            "Projetar": "✍️",
            "Linha de Produção": "⚙️",
            "StandBy": "⏸️"
        }
        emoji = emoji_map.get(grupo_nome, "📁")
        
        resposta = f"{emoji} *Orçamentos em: {grupo_nome}*\n"
        
        for orc in orcamentos:
            etapa_num = orc.etapa_concluida + 1
            
            if grupo_nome == "Linha de Produção":
                data_limite_prod = orc.data_limite_etapa2 if orc.etapa_concluida >= 1 else orc.data_limite_etapa1
                prazo_str = f"(Prazo: {data_limite_prod.strftime('%d/%m/%Y')})" if data_limite_prod else ""
                resposta += f"\n\n• *{orc.numero}-{orc.cliente}* {prazo_str}"
                
                tarefas_atuais = [t for t in orc.tarefas if t.etapa == etapa_num and t.status != 'StandBy' and t.item_descricao]
                
                finalizadas = sorted(list(set([t.item_descricao for t in tarefas_atuais if t.status == 'Produção Finalizada'])))
                iniciadas = sorted(list(set([t.item_descricao for t in tarefas_atuais if t.status in ('Iniciou a Produção', 'Fase de Acabamento', 'Aguardando Vidro / Pedra', 'Reforma em Andamento')])))
                nao_iniciadas = sorted(list(set([t.item_descricao for t in tarefas_atuais if t.status == 'Não Iniciado'])))

                if not finalizadas and not iniciadas and not nao_iniciadas:
                    resposta += "\n  └ _Nenhuma tarefa de produção registrada para esta etapa._"
                else:
                    if finalizadas:
                        resposta += f"\n  ✅ *Finalizados:* {', '.join(finalizadas)}"
                    if iniciadas:
                        resposta += f"\n  ⚙️ *Iniciados:* {', '.join(iniciadas)}"
                    if nao_iniciadas:
                        resposta += f"\n  ⏳ *Não Iniciados:* {', '.join(nao_iniciadas)}"
            else:
                status_str = f"(Etapa {etapa_num} - Status: {orc.status_atual})"
                if grupo_nome == "StandBy" and orc.standby_details:
                    status_str = f"(Motivo: {orc.standby_details})"
                
                resposta += f"\n• *{orc.numero}-{orc.cliente}* {status_str}"

        return resposta
    except Exception as e:
        print(f"[ERRO no format_orcamentos_por_grupo]: {e}")
        return f"Ocorreu um erro interno ao consultar o grupo '{grupo_nome}'."


@app.route('/api/bot/grupo', methods=['GET'])
def bot_grupo_query():
    remetente_id = request.args.get('remetente')
    if remetente_id not in AUTHORIZED_BOT_NUMBERS:
        return jsonify({"resposta": "Desculpe, seu número não está autorizado a fazer consultas."})

    nome_grupo = request.args.get('nome_grupo')
    if not nome_grupo:
         return jsonify({"resposta": "Nome do grupo não fornecido."})

    resposta_formatada = format_orcamentos_por_grupo(nome_grupo)
    
    return jsonify({"resposta": resposta_formatada})

@app.route('/api/bot/fila_producao', methods=['GET'])
def bot_fila_producao_query():
    remetente_id = request.args.get('remetente')
    if remetente_id not in AUTHORIZED_BOT_NUMBERS:
        return jsonify({"resposta": "Desculpe, seu número não está autorizado a fazer consultas."})

    try:
        grupo_prod = Grupo.query.filter_by(nome='Linha de Produção').first()
        if not grupo_prod:
            return jsonify({"resposta": "Erro: Grupo 'Linha de Produção' não encontrado."})

        def get_sort_date(o):
            return o.data_limite_etapa2 if o.etapa_concluida >= 1 else o.data_limite_etapa1
        
        orcamentos_na_fila = Orcamento.query.options(
            joinedload(Orcamento.tarefas)
        ).filter_by(grupo_id=grupo_prod.id).all()
        
        orcamentos_fila_mestra = sorted(
            [o for o in orcamentos_na_fila if get_sort_date(o)], 
            key=get_sort_date
        )
        orcamentos_fila_mestra.extend([o for o in orcamentos_na_fila if not get_sort_date(o)])

        if not orcamentos_fila_mestra:
            return jsonify({"resposta": "Nenhum orçamento em 'Linha de Produção' no momento."})

        colaborador_posicao_fila = {}
        emoji_colaborador = {
            "Anderson": "👨‍🦲", "Edison": "👨‍🏭", "Hélio": "👴",
            "José": "🧓", "Luiz": "👷‍♂️", "Renato": "👨‍🔧"
        }

        for i, orcamento in enumerate(orcamentos_fila_mestra, 1):
            current_etapa_num = orcamento.etapa_concluida + 1
            tarefas_da_etapa = [t for t in orcamento.tarefas if t.etapa == current_etapa_num]

            for tarefa in tarefas_da_etapa:
                colab = tarefa.colaborador
                if colab not in colaborador_posicao_fila and tarefa.status == 'Não Iniciado':
                    colaborador_posicao_fila[colab] = i

        resposta = "⚙️ *Orçamentos em: Linha de Produção*\n"

        for i, orcamento in enumerate(orcamentos_fila_mestra, 1):
            
            prazo_dt = get_sort_date(orcamento)
            prazo_str = f"(Prazo: {prazo_dt.strftime('%d/%m/%Y')})" if prazo_dt else "(Sem Prazo)"
            
            etapa_num = orcamento.etapa_concluida + 1
            
            resposta += f"\n*{orcamento.numero}-{orcamento.cliente}* (Etapa {etapa_num}) {prazo_str}\n"

            itens_prontos = []
            itens_iniciados = []
            itens_acabamento = []
            itens_nao_iniciados = {}

            tarefas_da_etapa = [t for t in orcamento.tarefas if t.etapa == etapa_num and t.item_descricao]
            
            for t in tarefas_da_etapa:
                if t.status == 'Produção Finalizada':
                    itens_prontos.append(t.item_descricao)
                elif t.status == 'Iniciou a Produção':
                    itens_iniciados.append(t.item_descricao)
                elif t.status == 'Fase de Acabamento':
                    itens_acabamento.append(t.item_descricao)
                elif t.status == 'Não Iniciado':
                    if t.colaborador not in itens_nao_iniciados:
                        itens_nao_iniciados[t.colaborador] = []
                    itens_nao_iniciados[t.colaborador].append(t.item_descricao)
            
            if itens_prontos:
                resposta += f"✅ *Itens prontos:* {', '.join(sorted(list(set(itens_prontos))))}\n"
            if itens_iniciados:
                resposta += f"❗ *Itens iniciados:* {', '.join(sorted(list(set(itens_iniciados))))}\n"
            if itens_acabamento:
                resposta += f"👨‍🏭 *Fase de Acabamento:* {', '.join(sorted(list(set(itens_acabamento))))}\n"
            
            if itens_nao_iniciados:
                linhas_nao_iniciadas = []
                for colab in sorted(itens_nao_iniciados.keys()):
                    itens_str = ", ".join(sorted(list(set(itens_nao_iniciados[colab]))))
                    posicao = colaborador_posicao_fila.get(colab)
                    posicao_str = "N/A"
                    if posicao:
                        sufixos = {1: "º", 2: "º", 3: "º"}
                        sufixo = sufixos.get(posicao, "º")
                        posicao_str = f"{posicao}{sufixo}"
                    
                    emoji = emoji_colaborador.get(colab, "🧑‍🏭")
                    
                    linhas_nao_iniciadas.append(
                        f"{emoji} *{colab}:* {itens_str}. *Posição na Fila:* {posicao_str}"
                    )
                
                if linhas_nao_iniciadas:
                    resposta += f"❌ *Itens não iniciados:*\n" + "\n".join(linhas_nao_iniciadas) + "\n"

            if i < len(orcamentos_fila_mestra):
                resposta += "\n"

        return jsonify({"resposta": resposta})

    except Exception as e:
        print(f"[ERRO no /api/bot/fila_producao]: {e}")
        return jsonify({"resposta": f"Ocorreu um erro interno ao calcular a fila de produção: {e}"}), 500

# --- FIM DAS NOVAS ROTAS DO BOT ---


# --- ROTA DE BUSCA GLOBAL ---
@app.route('/api/search', methods=['GET'])
@login_required
def global_search():
    search_term = request.args.get('q', '')
    
    if len(search_term) < 2:
        return jsonify([])
    
    try:
        search_pattern = f"%{search_term}%"
        
        orcamentos = Orcamento.query.filter(
            or_(
                Orcamento.numero.ilike(search_pattern),
                Orcamento.cliente.ilike(search_pattern)
            )
        ).order_by(Orcamento.last_updated_at.desc()).limit(10).all()

        resultados = [
            {
                "id": o.id,
                "numero": o.numero,
                "cliente": o.cliente,
                "grupo_nome": o.grupo.nome
            } for o in orcamentos
        ]
        
        return jsonify(resultados)
        
    except Exception as e:
        print(f"Erro na busca global: {e}")
        return jsonify({"error": str(e)}), 500
# --- FIM: NOVA ROTA DE BUSCA GLOBAL ---


# --- INÍCIO: NOVAS ROTAS DE PREVISÃO DO TEMPO ---

NOMINATIM_USER_AGENT = os.environ.get('NOMINATIM_USER_AGENT', 'WorkflowApp/1.0 (seuemail@provedor.com)')
NOMINATIM_API_URL = "https://nominatim.openstreetmap.org/search"
OPEN_METEO_API_URL = "https://api.open-meteo.com/v1/forecast"

def get_coords_from_address(endereco_query):
    """Busca coordenadas (lat, lon) E NOME DO LOCAL de um endereço usando Nominatim."""
    try:
        headers = {'User-Agent': NOMINATIM_USER_AGENT}
        params = {'q': endereco_query, 'format': 'json', 'limit': 1, 'addressdetails': 1} 
        
        response = requests.get(NOMINATIM_API_URL, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data and isinstance(data, list) and data[0].get('lat') and data[0].get('lon'):
            lat = data[0]['lat']
            lon = data[0]['lon']
            address = data[0].get('address', {})
            location_name = address.get('suburb',
                            address.get('city_district',
                            address.get('city',
                            address.get('town', "Local não encontrado"))))
            location_name = location_name.split(',')[0] 
            return (lat, lon, location_name)
        else:
            return None
            
    except Exception as e:
        print(f"Erro no Nominatim (geocodificação) para '{endereco_query}': {e}")
        return None

@app.route('/api/previsao/orcamento/<int:orc_id>')
@login_required
def get_previsao_orcamento(orc_id):
    orcamento = db.session.get(Orcamento, orc_id)
    if not orcamento:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    
    endereco_query = "Curitiba, BR"
    coords_data = None
    
    if orcamento.endereco and len(orcamento.endereco.strip()) > 5:
        coords_data = get_coords_from_address(orcamento.endereco)
        if coords_data:
            endereco_query = orcamento.endereco
        else:
            print(f"Aviso: Endereço '{orcamento.endereco}' não encontrado pelo Nominatim. Usando 'Curitiba'.")
            
    if not coords_data:
        coords_data = get_coords_from_address("Curitiba, BR")
        
    if not coords_data:
        return jsonify({"error": "Não foi possível obter coordenadas de geocodificação."}), 500
        
    lat, lon, location_name = coords_data

    try:
        params = {
            'latitude': lat,
            'longitude': lon,
            'hourly': 'precipitation_probability,weather_code',
            'forecast_days': 7,
            'timezone': 'America/Sao_Paulo'
        }
        response = requests.get(OPEN_METEO_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        hourly_data_openmeteo = data.get('hourly', {})
        times = hourly_data_openmeteo.get('time', [])
        probs = hourly_data_openmeteo.get('precipitation_probability', [])
        codes = hourly_data_openmeteo.get('weather_code', [])

        day_map = {}
        for i in range(len(times)):
            try:
                timestamp_str = times[i]
                date_part = timestamp_str.split('T')[0]
                prob_chuva = probs[i]
                code = codes[i]
                vai_chover = 1 if (prob_chuva is not None and prob_chuva > 15) or (code >= 51) else 0
                if date_part not in day_map:
                    day_map[date_part] = []
                day_map[date_part].append({
                    "time": timestamp_str,
                    "chance_of_rain": prob_chuva,
                    "will_it_rain": vai_chover,
                    "weather_code": code
                })
            except Exception as e_loop:
                print(f"Erro no loop de processamento do Open-Meteo: {e_loop}")
        
        horly_data_structured = [{"date": d, "hour": h} for d, h in day_map.items()]
        
        return jsonify({
            "location_name": location_name,
            "forecast_days": horly_data_structured
        })

    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar previsão do tempo (Open-Meteo) para '{endereco_query}': {e}")
        return jsonify({"error": "Não foi possível obter a previsão para este endereço."}), 500
    except Exception as e:
        print(f"Erro ao processar previsão: {e}")
        return jsonify({"error": "Erro interno ao processar previsão."}), 500

@app.route('/api/previsao/curitiba')
@login_required
def get_previsao_curitiba():
    try:
        params = {
            'latitude': -25.4284,
            'longitude': -49.2733,
            'daily': 'weather_code',
            'forecast_days': 10,
            'timezone': 'America/Sao_Paulo'
        }
        response = requests.get(OPEN_METEO_API_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        daily_data = data.get('daily', {})
        times = daily_data.get('time', [])
        codes = daily_data.get('weather_code', [])
        
        simplified_forecast = []
        for i in range(len(times)):
            simplified_forecast.append({
                "date": times[i],
                "condition_code": codes[i]
            })
        
        return jsonify(simplified_forecast)

    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar previsão de Curitiba: {e}")
        return jsonify({"error": f"Erro ao contatar a API de previsão: {e}"}), 500
    except Exception as e:
        print(f"Erro ao processar previsão de Curitiba: {e}")
        return jsonify({"error": f"Erro interno ao processar previsão: {e}"}), 500

# --- FIM: NOVAS ROTAS DE PREVISÃO DO TEMPO ---


# --- ==== NOVAS ROTAS DE EDIÇÃO ==== ---

@app.route('/api/orcamento/<int:orc_id>/detalhes', methods=['GET'])
@login_required
def get_orcamento_detalhes(orc_id):
    """ Retorna todos os dados de um orçamento para o modal mestre """
    orcamento = db.session.get(Orcamento, orc_id)
    if not orcamento:
        return jsonify({"error": "Orçamento não encontrado"}), 404
        
    return jsonify(orcamento.to_dict())


# REQ 4: Função helper para atualizar tarefas a partir da descrição
def atualizar_tarefas_from_descricao(orcamento, nova_descricao, etapa, map_colaboradores):
    # 1. Pega tarefas existentes no DB para esta etapa
    tarefas_existentes = db.session.query(TarefaProducao).filter_by(
        orcamento_id=orcamento.id, 
        etapa=etapa
    ).all()
    itens_existentes = {t.item_descricao: t for t in tarefas_existentes}
    
    # 2. Pega novos itens da textarea (limpos e únicos)
    novos_itens_lista = [item.strip() for item in nova_descricao.split(',') if item.strip()]
    novos_itens_set = set(novos_itens_lista)

    # --- Lógica de Divisão do Giratório ---
    giratorio_regex = re.compile(r"Giratório (\dL) (\d)E", re.IGNORECASE)
    itens_processados = set() # Para evitar adicionar o item base "Giratório X Y"

    for item_desc in novos_itens_set:
        match = giratorio_regex.match(item_desc)
        if match and etapa == 2:
            itens_processados.add(item_desc) # Marca o item "Giratório..." como processado
            
            linhas = match.group(1) # "1L" ou "2L"
            num_espetos = match.group(2) # "4", "5", etc.
            
            # Item 1: Espetos
            item_espetos = f"{num_espetos} Espetos Giratórios"
            if item_espetos not in itens_existentes:
                tarefa_espetos = TarefaProducao(
                    orcamento_id=orcamento.id, colaborador="José",
                    item_descricao=item_espetos, status='Não Iniciado', etapa=2
                )
                db.session.add(tarefa_espetos)
            else:
                # Remove da lista de existentes para não ser deletado
                itens_existentes.pop(item_espetos) 
            
            # Item 2: Sistema
            item_sistema = f"Giratório {linhas}"
            if item_sistema not in itens_existentes:
                 tarefa_sistema = TarefaProducao(
                    orcamento_id=orcamento.id, colaborador="Luiz",
                    item_descricao=item_sistema, status='Não Iniciado', etapa=2
                )
                 db.session.add(tarefa_sistema)
            else:
                itens_existentes.pop(item_sistema)

    # 3. Adiciona tarefas que estão na textarea mas não no DB (e não são giratórios)
    for item_desc in novos_itens_set:
        if item_desc in itens_processados: # Pula o item "Giratório..."
            continue
            
        if item_desc not in itens_existentes:
            # Item novo, precisa ser criado
            colaborador = "Indefinido"
            colaborador = map_colaboradores.get(item_desc, "Indefinido")
            
            if colaborador == "Indefinido":
                for base_item, colab_mapeado in map_colaboradores.items():
                    if item_desc.startswith(base_item):
                        colaborador = colab_mapeado
                        break
            
            nova_tarefa = TarefaProducao(
                orcamento_id=orcamento.id,
                colaborador=colaborador,
                item_descricao=item_desc,
                status='Não Iniciado',
                etapa=etapa
            )
            db.session.add(nova_tarefa)
            print(f"Modal Mestre: Adicionando tarefa '{item_desc}' (Etapa {etapa})")

    # 4. Deleta tarefas que estão no DB mas não mais na textarea
    for item_existente, tarefa_obj in itens_existentes.items():
        if item_existente not in novos_itens_set:
            # Verifica se o item a ser deletado não é parte de um giratório
            # (Ex: "4 Espetos Giratórios" não deve ser deletado se "Giratório 1L 4E" ainda existir)
            e_parte_de_giratorio_novo = False
            if item_existente.endswith("Espetos Giratórios") or item_existente.startswith("Giratório "):
                for novo_item in novos_itens_set:
                    if giratorio_regex.match(novo_item):
                        e_parte_de_giratorio_novo = True
                        break
            
            if not e_parte_de_giratorio_novo:
                db.session.delete(tarefa_obj)
                print(f"Modal Mestre: Deletando tarefa '{item_existente}' (Etapa {etapa})")


@app.route('/api/orcamento/<int:orc_id>/update_detalhes', methods=['PUT'])
@login_required
def update_orcamento_detalhes(orc_id):
    """ Salva os dados do modal mestre """
    orcamento = db.session.get(Orcamento, orc_id)
    if not orcamento:
        return jsonify({"error": "Orçamento não encontrado"}), 404
    
    data = request.json
    try:
        # --- Coleta dados ---
        orcamento.numero = data.get('numero', orcamento.numero)
        orcamento.cliente = data.get('cliente', orcamento.cliente)
        orcamento.endereco = data.get('endereco', orcamento.endereco)
        orcamento.etapa_concluida = int(data.get('etapa_concluida', orcamento.etapa_concluida))
        
        orcamento.data_limite_etapa1 = parse_datetime(data.get('data_limite_etapa1'))
        orcamento.data_limite_etapa2 = parse_datetime(data.get('data_limite_etapa2'))
        
        orcamento.data_visita = parse_datetime(data.get('data_visita_etapa1'))
        orcamento.data_visita_etapa2 = parse_datetime(data.get('data_visita_etapa2'))
        orcamento.data_instalacao = parse_datetime(data.get('data_instalacao'))
        
        nova_desc_etapa1 = data.get('etapa1_descricao', orcamento.etapa1_descricao)
        nova_desc_etapa2 = data.get('etapa2_descricao', orcamento.etapa2_descricao)

        # Atualizar tarefas se a descrição mudou
        if nova_desc_etapa1 != orcamento.etapa1_descricao:
            # Combina os mapas de colaborador
            mapa_etapa1 = {**MAP_ITEM_COLABORADOR, **ITENS_ETAPA_1_COMO_MAPA} 
            atualizar_tarefas_from_descricao(orcamento, nova_desc_etapa1, 1, mapa_etapa1)
            orcamento.etapa1_descricao = nova_desc_etapa1

        if nova_desc_etapa2 != orcamento.etapa2_descricao:
            mapa_etapa2 = {**MAP_ITEM_COLABORADOR}
            atualizar_tarefas_from_descricao(orcamento, nova_desc_etapa2, 2, mapa_etapa2)
            orcamento.etapa2_descricao = nova_desc_etapa2
        
        log_activity(orcamento, "Edição Mestre", f"Usuário '{current_user.nome}' atualizou os detalhes completos do orçamento.")
        db.session.commit()
        return jsonify(orcamento.to_dict())
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro em update_orcamento_detalhes: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/orcamento/<int:orc_id>/edit_campo', methods=['PUT'])
@login_required
def edit_orcamento_campo(orc_id):
    """ Edita um campo específico de um orçamento (edição rápida) """
    orcamento = db.session.get(Orcamento, orc_id)
    if not orcamento:
        return jsonify({"error": "Orçamento não encontrado"}), 404
        
    data = request.json
    campo = data.get('campo')
    valor = data.get('valor')
    
    if not campo:
        return jsonify({"error": "O campo a ser editado não foi especificado."}), 400

    try:
        details = f"Usuário '{current_user.nome}' alterou '{campo}' para '{valor}'."
        
        if campo == 'data_visita' or campo == 'data_instalacao' or campo == 'data_pronto':
            # Estes são agendamentos (datetime)
            setattr(orcamento, campo, parse_datetime(valor))
        
        elif campo == 'data_entrada_producao':
            nova_data_entrada = parse_datetime(valor)
            data_entrada_antiga = orcamento.data_entrada_producao
            
            if nova_data_entrada:
                orcamento.data_entrada_producao = nova_data_entrada
                
                # REQ 3: Lógica de Recálculo de Prazo
                if not data_entrada_antiga: 
                    print("Nota: Data de entrada definida, mas data antiga não existia. Datas limite não foram recalculadas.")
                else:
                    if orcamento.data_limite_etapa1:
                        try:
                            delta1 = orcamento.data_limite_etapa1 - data_entrada_antiga
                            orcamento.data_limite_etapa1 = nova_data_entrada + delta1
                        except Exception: pass
                            
                    if orcamento.data_limite_etapa2:
                        try:
                            delta2 = orcamento.data_limite_etapa2 - data_entrada_antiga
                            orcamento.data_limite_etapa2 = nova_data_entrada + delta2
                        except Exception: pass
        
        elif campo == 'data_limite':
            # REQ 3: Edição direta da data limite (sem afetar entrada)
            etapa_atual = orcamento.etapa_concluida
            if etapa_atual == 0:
                orcamento.data_limite_etapa1 = parse_datetime(valor)
            else:
                orcamento.data_limite_etapa2 = parse_datetime(valor)

        elif campo == 'responsavel_visita' or campo == 'responsavel_instalacao' or campo == 'standby_details':
            setattr(orcamento, campo, valor)
            
        elif campo == 'itens_prontos':
            # Atualiza a descrição E as tarefas
            if orcamento.etapa_concluida == 0:
                mapa_etapa1 = {**MAP_ITEM_COLABORADOR, **ITENS_ETAPA_1_COMO_MAPA}
                atualizar_tarefas_from_descricao(orcamento, valor, 1, mapa_etapa1)
                orcamento.etapa1_descricao = valor
            else:
                mapa_etapa2 = {**MAP_ITEM_COLABORADOR}
                atualizar_tarefas_from_descricao(orcamento, valor, 2, mapa_etapa2)
                orcamento.etapa2_descricao = valor
        else:
            return jsonify({"error": f"Campo '{campo}' não é editável."}), 400

        log_activity(orcamento, "Edição Rápida", details)
        db.session.commit()
        return jsonify(orcamento.to_dict())

    except Exception as e:
        db.session.rollback()
        print(f"Erro em edit_orcamento_campo: {e}")
        return jsonify({"error": str(e)}), 500

# --- ==== FIM DAS NOVAS ROTAS DE EDIÇÃO ==== ---


# --- Execução ---
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(INSTANCE_FOLDER):
        os.makedirs(INSTANCE_FOLDER)
    
    # Define um mapa de strings para os itens da Etapa 1 (necessário para a função de edição)
    ITENS_ETAPA_1_COMO_MAPA = {item: "Indefinido" for item in ITENS_ETAPA_1}
    for item, colab in MAP_ITEM_COLABORADOR.items():
        if item in ITENS_ETAPA_1_COMO_MAPA:
            ITENS_ETAPA_1_COMO_MAPA[item] = colab
            
    setup_database(app)
    scheduler.init_app(app)
    scheduler.start()
    app.run(debug=True, port=5001)