"""
Blueprint de Rotas Principais

Aqui definimos as URLs (rotas) da nossa aplicação e qual
template HTML elas devem renderizar.
"""
from flask import Blueprint, render_template
import logging

# Cria um Blueprint chamado 'main'. 
# Blueprints são a forma POO de organizar rotas no Flask.
router = Blueprint('main', __name__)

@router.route('/')
@router.route('/dashboard')
def index():
    """Rota para o Dashboard principal."""
    logging.info(f"Acessando rota: / (renderizando index.html)")
    # Todas as rotas renderizam o MESMO template 'index.html'.
    # O JavaScript dentro dele cuidará de mostrar a view correta.
    return render_template('index.html')

@router.route('/kanban')
def kanban():
    """Rota para a view Kanban."""
    logging.info(f"Acessando rota: /kanban (renderizando index.html)")
    return render_template('index.html')

@router.route('/eisenhower')
def eisenhower():
    """Rota para a view Eisenhower."""
    logging.info(f"Acessando rota: /eisenhower (renderizando index.html)")
    return render_template('index.html')

@router.route('/pros-contras')
def pros_contras():
    """Rota para a view Prós e Contras."""
    logging.info(f"Acessando rota: /pros-contras (renderizando index.html)")
    return render_template('index.html')

@router.route('/planejador')
def planejador():
    """Rota para a view Planejador Semanal."""
    logging.info(f"Acessando rota: [bold cyan]/planejador[/] (renderizando index.html)")
    return render_template('index.html')
# --- FIM DA NOVA ROTA ---

# Teste de erro (opcional)
@router.errorhandler(404)
def page_not_found(e):
    logging.warning(f"Erro 404 - Página não encontrada: {e}")
    return "<h1>Erro 404</h1><p>Página não encontrada.</p>", 404
