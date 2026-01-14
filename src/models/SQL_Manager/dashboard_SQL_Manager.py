import streamlit as st
import sqlite3
import pandas as pd

# -----------------------------------------------------------------------------
# MODEL
# Camada de dados: responsável por toda a interação com o banco de dados.
# -----------------------------------------------------------------------------
class DatabaseModel:
    """
    Classe Model que gerencia todas as operações do banco de dados SQLite.
    """
    def __init__(self, db_name="database.db"):
        """Inicializa e conecta ao banco de dados."""
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()

    def _execute_query(self, query, params=None, fetch=None):
        """Método genérico para executar queries."""
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)

            if fetch == "one":
                return self.cursor.fetchone()
            if fetch == "all":
                return self.cursor.fetchall()
            
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            st.error(f"Erro no Banco de Dados: {e}")
            return None

    def setup_database(self):
        """Cria tabelas e insere dados de exemplo se não existirem."""
        # Tabela de Clientes
        self._execute_query("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            status TEXT DEFAULT 'active'
        )
        """)
        # Tabela de Produtos
        self._execute_query("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            price REAL,
            stock INTEGER
        )
        """)

        # Insere dados de exemplo se as tabelas estiverem vazias
        if self.get_data("clientes").empty:
            sample_clients = [
                ('João Silva', 'joao.silva@email.com', 'active'),
                ('Maria Oliveira', 'maria.o@email.com', 'active'),
                ('Carlos Pereira', 'carlos.p@email.com', 'inactive'),
                ('Ana Costa', 'ana.costa@email.com', 'active'),
            ]
            for client in sample_clients:
                self._execute_query("INSERT INTO clientes (name, email, status) VALUES (?, ?, ?)", client)

        if self.get_data("produtos").empty:
            sample_products = [
                ('Notebook Gamer', 4599.90, 15),
                ('Mouse Sem Fio', 120.50, 50),
                ('Teclado Mecânico', 350.00, 30),
                ('Monitor 4K', 1800.00, 10),
            ]
            for product in sample_products:
                self._execute_query("INSERT INTO produtos (product_name, price, stock) VALUES (?, ?, ?)", product)


    def get_table_names(self):
        """Busca os nomes de todas as tabelas no banco."""
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        tables = self._execute_query(query, fetch="all")
        return [table[0] for table in tables] if tables else []

    def get_column_names(self, table_name):
        """Busca os nomes das colunas de uma tabela específica."""
        query = f"PRAGMA table_info({table_name});"
        columns_info = self._execute_query(query, fetch="all")
        return [col[1] for col in columns_info] if columns_info else []

    def get_data(self, table_name, where_clause=""):
        """Busca dados de uma tabela, com um filtro opcional."""
        query = f"SELECT * FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        
        data = self._execute_query(query, fetch="all")
        columns = self.get_column_names(table_name)
        return pd.DataFrame(data, columns=columns) if data is not None else pd.DataFrame()

    def add_row(self, table_name, data):
        """Adiciona uma nova linha a uma tabela."""
        columns = self.get_column_names(table_name)
        # Remove o 'id' pois é autoincremento
        columns.remove('id')
        placeholders = ', '.join(['?'] * len(columns))
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        values = tuple(data[col] for col in columns)
        return self._execute_query(query, values)

    def delete_row(self, table_name, row_id):
        """Deleta uma linha pelo seu ID."""
        query = f"DELETE FROM {table_name} WHERE id = ?"
        return self._execute_query(query, (row_id,))

    def add_column(self, table_name, column_name, column_type):
        """Adiciona uma nova coluna a uma tabela."""
        query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        return self._execute_query(query)

    def drop_column(self, table_name, column_name):
        """Remove uma coluna de uma tabela."""
        # SQLite não tem um comando DROP COLUMN simples, a recriação da tabela é o método seguro
        query = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
        # ATENÇÃO: A query acima não funciona em SQLite padrão. 
        # A forma correta seria criar uma nova tabela, copiar os dados e renomear.
        # Por simplicidade, deixaremos um aviso.
        st.warning(f"O SQLite não suporta 'DROP COLUMN' diretamente. A forma segura de fazer isso é mais complexa e não foi implementada neste exemplo simples.")
        return False # Retorna False pois a operação não é suportada de forma simples

    def close(self):
        """Fecha a conexão com o banco de dados."""
        self.conn.close()

# -----------------------------------------------------------------------------
# VIEW
# Camada de apresentação: responsável por exibir a UI para o usuário.
# -----------------------------------------------------------------------------
def setup_view():
    """Configurações iniciais da página Streamlit."""
    st.set_page_config(page_title="Dashboard de Dados", layout="wide")
    st.title("📊 Dashboard de Dados: SQLite & Excel")
    st.markdown("Use este painel para interagir com suas fontes de dados.")

def show_query_tab(controller):
    """Exibe a aba de consulta e filtro de dados."""
    with st.expander("🔍 **Filtro WHERE**", expanded=True):
        st.info("Escreva uma condição SQL. Ex: `status = 'active'` ou `price > 200`")
        where_input = st.text_area("Condição WHERE:", key="where_clause", height=70)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Aplicar Filtro"):
                controller.filter_data(where_input)
        with col2:
            if st.button("Remover Filtro"):
                controller.filter_data("") # Passa string vazia para limpar
    
    st.subheader(f"Dados Atuais da Tabela: `{st.session_state.get('selected_table', '')}`")
    df = st.session_state.get('dataframe', pd.DataFrame())
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("Nenhum dado encontrado ou a tabela está vazia.")


def show_add_data_tab(controller):
    """Exibe a aba para adicionar novos dados."""
    st.subheader(f"Adicionar nova linha em `{st.session_state.selected_table}`")
    columns = controller.get_columns()
    
    # Remove 'id' da lista de colunas para inserção
    insert_columns = [col for col in columns if col != 'id']

    with st.form("add_row_form"):
        new_data = {}
        for col in insert_columns:
            new_data[col] = st.text_input(f"{col.capitalize()}:")
        
        submitted = st.form_submit_button("Adicionar Linha")
        if submitted:
            controller.add_new_row(new_data)

def show_manage_table_tab(controller):
    """Exibe a aba para gerenciar a estrutura da tabela."""
    st.subheader("Gerenciar Estrutura da Tabela")

    # Adicionar Coluna
    with st.container(border=True):
        st.markdown("##### Adicionar Nova Coluna")
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            new_col_name = st.text_input("Nome da Coluna")
        with col2:
            new_col_type = st.selectbox("Tipo da Coluna", ["TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC"])
        with col3:
            st.markdown("<br/>", unsafe_allow_html=True)
            if st.button("Adicionar Coluna"):
                controller.add_new_column(new_col_name, new_col_type)
    
    # Deletar Linha por ID
    with st.container(border=True):
        st.markdown("##### Deletar Linha por ID")
        col1, col2 = st.columns([2, 1])
        with col1:
            row_id_to_delete = st.number_input("ID da Linha para Deletar", min_value=1, step=1)
        with col2:
            st.markdown("<br/>", unsafe_allow_html=True)
            if st.button("Deletar Linha", type="primary"):
                controller.delete_selected_row(row_id_to_delete)

def show_excel_tab():
    """Exibe a aba para visualizar dados de um arquivo Excel."""
    st.subheader("Visualizador de Arquivo Excel")
    excel_data = st.session_state.get('excel_data', None)

    if excel_data:
        sheet_names = list(excel_data.keys())
        selected_sheet = st.selectbox("Selecione uma planilha:", sheet_names)
        
        if selected_sheet:
            st.dataframe(excel_data[selected_sheet], use_container_width=True)
    else:
        st.info("Carregue um arquivo Excel na barra lateral para começar.")

# -----------------------------------------------------------------------------
# CONTROLLER
# Lógica da aplicação: conecta a View (UI) com o Model (dados).
# -----------------------------------------------------------------------------
class AppController:
    def __init__(self, model):
        self.model = model
        # Inicializa o estado da sessão se não existir
        if 'selected_table' not in st.session_state:
            st.session_state.selected_table = None
        if 'dataframe' not in st.session_state:
            st.session_state.dataframe = pd.DataFrame()
        if 'where_clause' not in st.session_state:
            st.session_state.where_clause = ""
        if 'excel_data' not in st.session_state:
            st.session_state.excel_data = None


    def run(self):
        """Executa a aplicação principal."""
        self.model.setup_database()
        setup_view()

        st.sidebar.title("Navegação")

        # Seção de Upload de Excel
        st.sidebar.header("Carregar Excel")
        uploaded_file = st.sidebar.file_uploader("Escolha um arquivo .xlsx", type="xlsx")
        if uploaded_file:
            st.session_state.excel_data = pd.read_excel(uploaded_file, sheet_name=None)

        # Seção de Banco de Dados
        st.sidebar.header("Banco de Dados")
        tables = self.model.get_table_names()
        if not tables:
            st.sidebar.error("Nenhuma tabela encontrada no banco de dados.")
            # return # Comentado para permitir que a app continue mesmo sem tabelas

        # Define a primeira tabela como padrão se nenhuma estiver selecionada
        if st.session_state.selected_table is None and tables:
            st.session_state.selected_table = tables[0]
        
        selected_table = st.sidebar.radio(
            "Selecione uma tabela:",
            options=tables,
            key='selected_table',
            on_change=self.load_data # Callback para recarregar os dados ao mudar de tabela
        )

        # Abas Dinâmicas
        tabs_list = []
        if st.session_state.excel_data:
            tabs_list.append("Dados do Excel")
        
        db_tabs = ["Consultar Dados", "Adicionar Dados", "Gerenciar Tabela"]
        tabs_list.extend(db_tabs)

        # st.tabs só pode ser chamado uma vez
        if tabs_list:
            selected_tab = st.tabs(tabs_list)

            # Renderiza a aba de Excel se existir
            if "Dados do Excel" in tabs_list:
                with selected_tab[tabs_list.index("Dados do Excel")]:
                    show_excel_tab()

            # Renderiza as abas do banco de dados
            if selected_table:
                self.load_data()
                with selected_tab[tabs_list.index("Consultar Dados")]:
                    show_query_tab(self)
                with selected_tab[tabs_list.index("Adicionar Dados")]:
                    show_add_data_tab(self)
                with selected_tab[tabs_list.index("Gerenciar Tabela")]:
                    show_manage_table_tab(self)

    def load_data(self):
        """Carrega os dados da tabela selecionada para o estado da sessão."""
        table = st.session_state.selected_table
        if table:
            where = st.session_state.where_clause
            df = self.model.get_data(table, where)
            st.session_state.dataframe = df

    def filter_data(self, where_clause):
        """Aplica ou remove um filtro e recarrega os dados."""
        st.session_state.where_clause = where_clause
        self.load_data()

    def get_columns(self):
        """Busca as colunas da tabela selecionada."""
        if st.session_state.selected_table:
            return self.model.get_column_names(st.session_state.selected_table)
        return []

    def add_new_row(self, data):
        """Adiciona uma nova linha e atualiza a visualização."""
        if any(not val for val in data.values()):
            st.error("Todos os campos devem ser preenchidos.")
            return

        if self.model.add_row(st.session_state.selected_table, data):
            st.success("Linha adicionada com sucesso!")
            self.load_data() # Recarrega os dados para mostrar a nova linha
        else:
            st.error("Falha ao adicionar a linha.")
    
    def delete_selected_row(self, row_id):
        """Deleta uma linha e atualiza a visualização."""
        if self.model.delete_row(st.session_state.selected_table, row_id):
            st.success(f"Linha com ID {row_id} deletada com sucesso!")
            self.load_data()
        else:
            st.error(f"Falha ao deletar a linha com ID {row_id}.")

    def add_new_column(self, name, type):
        """Adiciona uma nova coluna e atualiza a visualização."""
        if not name or not type:
            st.warning("Por favor, forneça nome e tipo para a nova coluna.")
            return
        
        if self.model.add_column(st.session_state.selected_table, name, type):
            st.success(f"Coluna '{name}' adicionada com sucesso!")
            self.load_data()
        else:
            st.error(f"Falha ao adicionar a coluna '{name}'.")


# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    db_model = DatabaseModel()
    controller = AppController(db_model)
    controller.run()