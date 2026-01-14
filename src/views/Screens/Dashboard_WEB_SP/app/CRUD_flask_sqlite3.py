# -*- coding: utf-8 -*-
# CÓDIGO FINAL DE BACK-END: Pikachu Web Server
# Base para o Dashboard ONS e o CRUD de Clientes.
# Este script implementa a Modelagem de Banco de Dados e os Endpoints REST.

import os
import sys
import json
import random
from flask import Flask, jsonify, request, send_from_directory, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime

# Garante que o projeto seja importável (mantendo a estrutura do Pedro)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# --- 1. CONFIGURAÇÃO BASE ---
# Instância do banco de dados (Global)
db = SQLAlchemy()

# --- 2. MODELAGEM DE DADOS (Matriz de Confiança) ---
# Esta é a sua tabela de Log de Tarefas ou Clientes (o alicerce do CRUD)
class TaskLog(db.Model):
    __tablename__ = 'tasks_log'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500))
    status = db.Column(db.String(50), default='PENDENTE')
    category = db.Column(db.String(50), default='ONS')
    due_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'category': self.category,
            'due_date': self.due_date.strftime('%Y-%m-%d %H:%M:%S'),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

# --- 3. BLUEPRINT DE ROTAS (O CRUD do Dashboard) ---
task_bp = Blueprint('tasks', __name__)

@task_bp.route('/tasks', methods=['GET'])
def get_tasks():
    """Endpoint para GET (Leitura) - Alimenta o Dashboard ONS."""
    try:
        # Se a tabela estiver vazia, cria 3 tarefas mock para teste
        if TaskLog.query.count() == 0:
            db.session.add_all([
                TaskLog(title="Debug MUST PySide6", description="Resolver falha no deploy desktop.", status="IN_PROGRESS", category="ONS"),
                TaskLog(title="Estudo Matriz Y-Bus", description="Finalizar a Matriz 3x3 com NumPy.", status="PENDENTE", category="SEP"),
                TaskLog(title="Treino Karatê", description="Alongamento e calistenia.", status="PENDENTE", category="ROTINA")
            ])
            db.session.commit()
            
        tasks = TaskLog.query.all()
        return jsonify([task.to_dict() for task in tasks])
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar tarefas: {e}"}), 500

@task_bp.route('/tasks', methods=['POST'])
def create_task():
    """Endpoint para POST (Criação) - Adiciona uma nova tarefa ao banco."""
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({"error": "Título da tarefa é obrigatório."}), 400

    new_task = TaskLog(
        title=data['title'],
        description=data.get('description', ''),
        status=data.get('status', 'PENDENTE'),
        category=data.get('category', 'PROJETO')
    )
    db.session.add(new_task)
    db.session.commit()
    return jsonify(new_task.to_dict()), 201

# --- 4. CLASSE PRINCIPAL DO SERVIDOR ---
class PikachuWebServer:
    def __init__(self):
        # O nome '__main__' é importante para o contexto do Flask.
        self.app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
        self.configure_app()
        self.setup_routes()
        self.setup_database()
        
    def configure_app(self):
        """Configurações básicas (Chave Secreta, Banco de Dados, CORS)"""
        self.app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'
        # Usando SQLite3 (o DB que o Pedro prefere)
        db_path = os.path.join(os.path.dirname(__file__), 'database', 'app.db')
        os.makedirs(os.path.join(os.path.dirname(__file__), 'database'), exist_ok=True)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Habilita CORS para o Frontend (React/HTML/JS)
        CORS(self.app)
        
    def setup_database(self):
        """Configura e inicializa o banco de dados (Ciclo 1)"""
        db.init_app(self.app)
        # CRÍTICO: Cria o contexto para inicializar o DB
        with self.app.app_context():
            db.create_all()
            print("✅ Banco de dados 'app.db' inicializado e tabelas criadas.")
    
    def setup_routes(self):
        """Configura todas as rotas da aplicação (APIs e Arquivos Estáticos)"""
        
        # 1. Rotas API (CRUD)
        self.app.register_blueprint(task_bp, url_prefix='/api')
        # ... Outras Blueprints (user_bp, astro_bp) seriam registradas aqui
        
        # 2. Rota para servir arquivos estáticos (Frontend - o seu HTML/JS)
        @self.app.route('/', defaults={'path': ''})
        @self.app.route('/<path:path>')
        def serve(path):
            static_folder_path = self.app.static_folder

            if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
                return send_from_directory(static_folder_path, path)
            else:
                # Retorna o index.html como padrão para o Dashboard
                index_path = os.path.join(static_folder_path, 'index.html')
                if os.path.exists(index_path):
                    return send_from_directory(static_folder_path, 'index.html')
                else:
                    return "Dashboard index.html não encontrado. Configure sua pasta 'static'.", 404
    
    def run(self, host='0.0.0.0', port=8888, debug=True):
        """Executa a aplicação Flask"""
        print(f"🚀 Pikachu Web Server rodando em http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

# Instância global e execução
if __name__ == '__main__':
    server = PikachuWebServer()
    server.run()