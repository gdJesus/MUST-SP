"""
Ponto de entrada principal para iniciar o servidor Flask.
Este arquivo configura o logging com 'Rich' e inicia a aplicação.
"""
import logging
import sys
import os

# --- Adiciona o diretório 'app' ao path ANTES das importações ---
# Isso resolve problemas de 'render_template' não encontrado
# ao garantir que o Flask encontre a pasta 'app' corretamente.
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app

# --- Importações do Rich ---
try:
    # A 'Console' não é necessária aqui, apenas o 'RichHandler'
    from rich.logging import RichHandler
except ImportError:
    print("Erro: A biblioteca 'rich' não está instalada.")
    print("Por favor, instale com: pip install rich")
    sys.exit(1)

# --- Configuração do Logging com Rich ---
# Configura o logger raiz para usar o RichHandler.
# Isso irá formatar todos os logs, incluindo os do Flask/Werkzeug.
logging.basicConfig(
    level="INFO",
    format="%(message)s", # Deixa o RichHandler cuidar da formatação
    datefmt="[%X]", # Formato de hora [HH:MM:SS]
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)] # Usa o RichHandler
)

# Pega o logger principal que usaremos
log = logging.getLogger("rich")
# --- Fim da Configuração ---


# Cria a instância da aplicação Flask
app = create_app()

if __name__ == "__main__":
    # Usa o logger do Rich para a mensagem de início
    log.info("Iniciando servidor Flask em [link=http://127.0.0.1:5000]http://127.0.0.1:5000[/link]", extra={"markup": True})
    
    # O log do Werkzeug (servidor) também será formatado pelo RichHandler
    app.run(debug=True, port=5000, host='127.0.0.1')

