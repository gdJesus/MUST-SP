# scripts/DataBaseController.py

import pandas as pd
import re
from abc import ABC, abstractmethod
from pathlib import Path
import sqlite3
import pyodbc

# --- 1. Mapeamento e Funções de Preparação de Dados (fora das classes) ---

# --- 1. Mapeamento e Funções de Preparação de Dados (com a correção do warning) ---

COLUMN_MAPPING = {
    'EMPRESA': 'empresa', 'Cód ONS': 'cod_ons', 'Tensão (kV)': 'tensao_kv', 'De': 'ponto_de',
    'Até': 'ponto_ate', 'Ponta 2025 Valor': 'ponta_2025_valor', 'Ponta 2025 Anotacao': 'ponta_2025_anotacao',
    'Fora Ponta 2025 Valor': 'fora_ponta_2025_valor', 'Fora Ponta 2025 Anotacao': 'fora_ponta_2025_anotacao',
    'Ponta 2026 Valor': 'ponta_2026_valor', 'Ponta 2026 Anotacao': 'ponta_2026_anotacao',
    'Fora Ponta 2026 Valor': 'fora_ponta_2026_valor', 'Fora Ponta 2026 Anotacao': 'fora_ponta_2026_anotacao',
    'Ponta 2027 Valor': 'ponta_2027_valor', 'Ponta 2027 Anotacao': 'ponta_2027_anotacao',
    'Fora Ponta 2027 Valor': 'fora_ponta_2027_valor', 'Fora Ponta 2027 Anotacao': 'fora_ponta_2027_anotacao',
    'Ponta 2028 Valor': 'ponta_2028_valor', 'Ponta 2028 Anotacao': 'ponta_2028_anotacao',
    'Fora Ponta 2028 Valor': 'fora_ponta_2028_valor', 'Fora Ponta 2028 Anotacao': 'fora_ponta_2028_anotacao',
    'Anotacao': 'anotacao_geral'
}

def clean_and_separate_valor_anotacao(df: pd.DataFrame) -> pd.DataFrame:
    pattern = re.compile(r'([\d.,-]+)\s*(\(.*\).*)?')
    value_cols = [col for col in df.columns if '_valor' in col]
    for col in value_cols:
        anotacao_col = col.replace('_valor', '_anotacao')
        if anotacao_col not in df.columns:
            df[anotacao_col] = None
        def separate_row(value):
            if pd.isna(value): return pd.Series([None, None])
            match = pattern.match(str(value).strip())
            if match:
                numero, anotacao = match.groups()
                return pd.Series([numero, anotacao])
            return pd.Series([value, None])
        separated_df = df[col].apply(separate_row)
        separated_df.columns = [col, anotacao_col + '_extra']
        df[col] = separated_df[col]
        df[anotacao_col] = df[anotacao_col].fillna('') + separated_df[anotacao_col + '_extra'].fillna('')
        df[anotacao_col] = df[anotacao_col].str.strip().replace('', None)
    df.drop(columns=[col for col in df.columns if col.endswith('_extra')], inplace=True)
    return df

def prepare_and_normalize_data(df_source: pd.DataFrame):
    print("1. Renomeando e limpando colunas...")
    df_source.rename(columns=COLUMN_MAPPING, inplace=True)
    df_source['empresa'] = df_source['empresa'].str.strip()
    df_source['cod_ons'] = df_source['cod_ons'].str.strip()
    
    print("1.5. Separando valores e anotações...")
    df_source = clean_and_separate_valor_anotacao(df_source)

    print("2. Normalizando a estrutura de dados...")
    
    empresas_unicas = df_source['empresa'].dropna().unique()
    df_empresas = pd.DataFrame(empresas_unicas, columns=['nome_empresa'])
    df_empresas.insert(0, 'id_empresa', range(1, len(df_empresas) + 1))
    
    df_merged = pd.merge(df_source, df_empresas, left_on='empresa', right_on='nome_empresa')
    
    cols_equip_base = ['cod_ons', 'tensao_kv', 'ponto_de', 'ponto_ate', 'anotacao_geral', 'id_empresa']
    df_equipamentos = df_merged[cols_equip_base].drop_duplicates(subset=['cod_ons']).reset_index(drop=True)
    df_equipamentos.insert(0, 'id_conexao', range(1, len(df_equipamentos) + 1))
    df_equipamentos['aprovado_por'] = None
    df_equipamentos['data_aprovacao'] = None
    
    id_vars = ['cod_ons']
    value_vars = [col for col in df_source.columns if re.match(r'(ponta|fora_ponta)_\d{4}', col)]
    df_melted = df_source.melt(id_vars=id_vars, value_vars=value_vars, var_name='medicao_tipo', value_name='valor')
    df_melted.dropna(subset=['valor'], inplace=True)

    extracted_data = df_melted['medicao_tipo'].str.extract(r'(ponta|fora_ponta)_(\d{4})_(valor|anotacao)')
    df_melted[['periodo', 'ano', 'tipo']] = extracted_data
    df_melted.dropna(subset=['ano', 'periodo', 'tipo'], inplace=True)
    df_melted['ano'] = df_melted['ano'].astype(int)

    df_pivot = df_melted.pivot_table(index=['cod_ons', 'ano', 'periodo'], columns='tipo', values='valor', aggfunc='first').reset_index()
    df_pivot.rename(columns={'valor': 'valor_must', 'anotacao': 'anotacao_valor'}, inplace=True)

    df_final_valores = pd.merge(df_pivot, df_equipamentos[['id_conexao', 'cod_ons']], on='cod_ons')
    
    # ===== CORREÇÃO PARA O WARNING AQUI =====
    # Selecionamos as colunas e explicitamente criamos uma cópia.
    df_valores_must = df_final_valores[['id_conexao', 'ano', 'periodo', 'valor_must', 'anotacao_valor']].copy()
    
    # Agora podemos renomear esta cópia com segurança.
    df_valores_must.rename(columns={'valor_must': 'valor'}, inplace=True)

    print(f"  -> Normalização concluída: {len(df_empresas)} empresas, {len(df_equipamentos)} equipamentos, {len(df_valores_must)} registros de valores.")
    return df_empresas, df_equipamentos, df_valores_must


# --- 2. Classe Base Abstrata (agora mais simples) ---

class DataBaseController(ABC):
    def __init__(self, db_path: Path, df_empresas, df_equipamentos, df_valores_must):
        self.db_path = db_path
        self.df_empresas = df_empresas
        self.df_equipamentos = df_equipamentos
        self.df_valores_must = df_valores_must
        self.conn = None
        self.cursor = None

    @abstractmethod
    def connect(self): pass
    @abstractmethod
    def close(self): pass
    @abstractmethod
    def _create_tables(self): pass
    @abstractmethod
    def _insert_data(self): pass

    def load_data(self):
        try:
            self.connect()
            self._create_tables()
            self._insert_data()
            print(f"\n✅ Entrada de dados para '{self.db_path.name}' concluída com sucesso!")
        except Exception as e:
            print(f"\n❌ ERRO GERAL para {self.db_path.name}: {e}")
        finally:
            self.close()

# --- 3. Implementações Específicas (SQLite e Access) ---

class SQLiteController(DataBaseController):
    def connect(self):
        print("3. Conectando ao banco de dados SQLite...")
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def close(self):
        if self.conn: self.conn.close(); print("Conexão SQLite fechada.")
    
    def _create_tables(self):
        print("4. Criando tabelas (se não existirem)...")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS empresas (id_empresa INTEGER PRIMARY KEY, nome_empresa TEXT NOT NULL UNIQUE)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS anotacao (id_conexao INTEGER PRIMARY KEY, cod_ons TEXT NOT NULL UNIQUE, tensao_kv INTEGER, ponto_de TEXT, ponto_ate TEXT, anotacao_geral TEXT, id_empresa_fk INTEGER, FOREIGN KEY (id_empresa_fk) REFERENCES empresas(id_empresa))")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS valores_must (id_valor INTEGER PRIMARY KEY, id_equipamento_fk INTEGER, ano INTEGER, periodo TEXT, valor REAL, FOREIGN KEY (id_equipamento_fk) REFERENCES equipamentos(id_conexao))")
        self.conn.commit()

    def _insert_data(self):
        print("5. Inserindo dados...")
        self.df_empresas.to_sql('empresas', self.conn, if_exists='replace', index=False)
        self.df_equipamentos.to_sql('anotacao', self.conn, if_exists='replace', index=False)
        self.df_valores_must.to_sql('valores_must', self.conn, if_exists='replace', index=False)
        self.conn.commit()

    def list_tables(self):
        """Lista todas as tabelas no banco de dados SQLite."""
        if not self.conn:
            self.connect()

        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [table[0] for table in self.cursor.fetchall()]

    def select_from_table(self, table_name):

        if not self.conn:
            self.connect()

        self.cursor.execute(f"SELECT * FROM {table_name};")
        columns = [description[0] for description in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]


# --- 4. Implementação para MS Access (VERSÃO FINAL) ---
class AccessController(DataBaseController):
    def connect(self):
        print("3. Conectando ao banco de dados MS Access...")
        if not self.db_path.exists(): raise FileNotFoundError(f"Arquivo Access não encontrado: {self.db_path}.")
        conn_str = (r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};" fr"DBQ={self.db_path};")
        self.conn = pyodbc.connect(conn_str)
        self.cursor = self.conn.cursor()

    def close(self):
        if self.conn: self.conn.close(); print("Conexão Access fechada.")

    def list_tables(self):
        """Lista todas as tabelas no banco de dados SQLite."""
        if not self.conn:
            self.connect()

        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [table[0] for table in self.cursor.fetchall()]

    def select_from_table(self, table_name):

        if not self.conn:
            self.connect()

        self.cursor.execute(f"SELECT * FROM {table_name};")
        columns = [description[0] for description in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def _create_tables(self):
        print("4. Verificando e limpando tabelas no Access...")
        required_tables = ['tb_empresas', 'tb_anotacao', 'tb_valores_must']
        existing_tables = [table.table_name.lower() for table in self.cursor.tables(tableType='TABLE')]
        for table in required_tables:
            if table not in existing_tables: raise ValueError(f"Tabela '{table}' não encontrada no Access!")
        
        print("   -> Limpando tabelas para nova carga (ordem reversa por causa dos relacionamentos)...")
        self.cursor.execute("DELETE FROM tb_valores_must")
        self.cursor.execute("DELETE FROM tb_anotacao")
        self.cursor.execute("DELETE FROM tb_empresas")
        self.conn.commit()

    def _insert_data(self):
        print("5. Inserindo dados no Access...")
        
        # ETAPA 1: Inserir Empresas e mapear ID do pandas -> ID do Access
        print("   -> Inserindo empresas...")
        empresa_id_map = {}
        for _, row in self.df_empresas.iterrows():
            self.cursor.execute("INSERT INTO tb_empresas (nome_empresa) VALUES (?)", row['nome_empresa'])
            self.cursor.execute("SELECT @@IDENTITY")
            access_id = self.cursor.fetchone()[0]
            empresa_id_map[row['id_empresa']] = access_id
        
        # ETAPA 2: Inserir Anotações
        print("   -> Inserindo anotações...")
        df_equip_to_insert = self.df_equipamentos.copy()

        # Usa o mapa para obter os IDs corretos do Access para a FK
        df_equip_to_insert['id_empresa'] = df_equip_to_insert['id_empresa'].map(empresa_id_map)

        for _, row in df_equip_to_insert.iterrows():
            # Nomes das colunas no Access, exatamente como na sua imagem
            sql_cols = "id_conexao, cod_ons, tensao_kv, ponto_de, ponto_ate, anotacao_geral, id_empresa, aprovado_por, data_aprovacao"
            
            params = (
                int(row['id_conexao']), # PK vinda do pandas
                row['cod_ons'],
                int(row['tensao_kv']) if pd.notna(row['tensao_kv']) else None,
                row['ponto_de'],
                row['ponto_ate'],
                row['anotacao_geral'],
                int(row['id_empresa']) if pd.notna(row['id_empresa']) else None,
                row['aprovado_por'],
                row['data_aprovacao']
            )
            
            # Note que agora o ID (id_conexao) faz parte da inserção
            self.cursor.execute(f"INSERT INTO tb_anotacao ({sql_cols}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", params)
            
        # ETAPA 3: Inserir Valores
        print("   -> Inserindo valores MUST...")
        df_valores_to_insert = self.df_valores_must.copy()
        sql_cols_valores = "id_conexao, ano, periodo, valor, anotacao_valor"
        
        valores_data = []
        for _, row in df_valores_to_insert.iterrows():
            
            # ===== CORREÇÃO DEFINITIVA ESTÁ AQUI =====
            raw_valor = row['valor']
            cleaned_valor = None # Valor padrão caso a conversão falhe

            if pd.notna(raw_valor):
                valor_str = str(raw_valor).strip()
                if valor_str == '-':
                    cleaned_valor = 0.0 # Trata o hífen como zero
                else:
                    try:
                        # Tenta a conversão para formatos como "1.500,25"
                        cleaned_valor = float(valor_str.replace('.', '').replace(',', '.'))
                    except ValueError:
                        # Se ainda assim falhar, é um texto inesperado. Mantém como Nulo.
                        print(f"AVISO: Não foi possível converter o valor '{valor_str}' para número. Será inserido como Nulo.")
                        cleaned_valor = None
            
            params = (
                int(row['id_conexao']),
                int(row['ano']),
                row['periodo'],
                cleaned_valor, # Usa o valor limpo e seguro
                row['anotacao_valor']
            )
            valores_data.append(params)
        
        self.cursor.executemany(f"INSERT INTO tb_valores_must ({sql_cols_valores}) VALUES (?, ?, ?, ?, ?)", valores_data)
        self.conn.commit()

# --- 5. Exemplo de Execução Refatorado ---

if __name__ == '__main__':
    print("--- INICIANDO TESTE DO DATABASE CONTROLLER (REATORADO) ---")
    
    EXCEL_PATH = Path(r"C:\Users\pedrovictor.veras\OneDrive - Operador Nacional do Sistema Eletrico\Documentos\ESTAGIO_ONS_PVRV_2025\GitHub\Palkia-PDF-extractor\src\ScrapperPDF\database\must_tables_PDF_notes_merged.xlsx")
    
    DB_OUTPUT_FOLDER = EXCEL_PATH.parent
    SQLITE_DB_PATH = DB_OUTPUT_FOLDER / "database_consolidado.db"
    ACCESS_DB_PATH = DB_OUTPUT_FOLDER / "Database_MUST.accdb"

    if not EXCEL_PATH.exists():
        print(f"ERRO: O arquivo Excel de entrada não foi encontrado em '{EXCEL_PATH}'")
    else:
        df_consolidado = pd.read_excel(EXCEL_PATH)
        
        # 1. Prepara os dados UMA ÚNICA VEZ
        df_empresas, df_anotacao, df_valores_must = prepare_and_normalize_data(df_consolidado)
        
        #! --- Processar para SQLite ---
        print("\n" + "="*50 + "\nPROCESSANDO PARA SQLITE\n" + "="*50)
        sqlite_controller = SQLiteController(SQLITE_DB_PATH, df_empresas, df_anotacao, df_valores_must)
        
        tabelas = sqlite_controller.list_tables()
        print("\nTabelas no Banco: ", tabelas)

        data_json = sqlite_controller.select_from_table(tabelas[0])
        print(f"\nDados da Tabela {tabelas[0]}:\n{data_json}")
        
        print("\nInserindo os dados das tabelas MUST no banco de dados SQLite...")
        sqlite_controller.load_data()

      
        #! --- Processar para MS Access ---
        try:
            print("\n" + "="*50 + "\nPROCESSANDO PARA MS ACCESS\n" + "="*50)
            access_controller = AccessController(ACCESS_DB_PATH, df_empresas, df_anotacao, df_valores_must)
            access_controller.load_data()
        except Exception as e:
            print(f"Falha na execução do Access Controller: {e}")