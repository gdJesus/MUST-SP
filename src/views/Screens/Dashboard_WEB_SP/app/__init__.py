"""
Fábrica de Aplicação (Application Factory) [app/__init__.py]

Cria a instância principal da aplicação Flask e registra as rotas (Blueprints).
"""
from flask import Flask
import logging

# Pega o logger 'rich' configurado no main.py
log = logging.getLogger("rich")

def create_app():
    """Cria e configura a instância principal da aplicação Flask."""
    log.info("Criando aplicação Flask...")
    
    # Define os caminhos para templates e arquivos estáticos
    # O Flask procura 'templates' e 'static' relativo a este arquivo (__name__ = 'app')
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    
    # --- Registro dos Blueprints (Rotas) ---
    try:
        # CORREÇÃO: Importa a variável 'router' (como definido em routes.py)
        # em vez de 'main_blueprint'
        from .routes import router
        
        # CORREÇÃO: Registra a variável 'router'
        app.register_blueprint(router)
        log.info("Blueprint 'router' (main) registrado com sucesso.")
        
    except ImportError as e:
        log.error(f"Falha ao importar ou registrar o blueprint de rotas: {e}", exc_info=True)
    except Exception as e:
        log.error(f"Erro inesperado ao registrar rotas: {e}", exc_info=True)


    log.info("Aplicação Flask criada e configurada.")
    return app

