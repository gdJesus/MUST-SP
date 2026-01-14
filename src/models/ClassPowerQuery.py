import pandas as pd
import camelot
from PyPDF2 import PdfReader
from typing import Dict

class MiniPowerQuery:
    def __init__(self, file_path: str = None):
        self.df = pd.DataFrame()
        self.file_path = file_path
        self.pdf_info = {}

    # -------------------- ANÁLISE INICIAL DO PDF --------------------
    def analyze_pdf(self, file_path: str):
        """Analisa o PDF para mostrar informações sobre tabelas e páginas."""
        print(f"Analisando PDF: {file_path}")
        
        # Informações básicas do PDF
        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            print(f"📄 Total de páginas encontradas: {total_pages}")
        except Exception as e:
            print(f"Erro ao ler PDF com PyPDF2: {e}")
            total_pages = 0

        # Análise com Camelot para contar tabelas
        try:
            tables = camelot.read_pdf(file_path, pages='all', flavor='lattice')
            print(f"\n📊 Tabelas encontradas com Camelot: {len(tables)}")
            
            for i, table in enumerate(tables):
                print(f"   Tabela {i+1}: {table.shape[0]}x{table.shape[1]} (página {table.page})")
            
            self.pdf_info = {
                'total_pages': total_pages,
                'total_tables': len(tables),
                'tables': tables
            }
            
        except Exception as e:
            print(f"Erro ao analisar com Camelot: {e}")
            self.pdf_info = {'total_pages': total_pages, 'total_tables': 0}
        
        return self

    # -------------------- EXTRAÇÃO DE DADOS --------------------
    def from_pdf_table(self, file_path: str, table_id: str = "Table011", pages: str = "all"):
        """Extrai tabela específica do PDF (equivalente ao Pdf.Tables do Power Query)."""
        try:
            # Tenta extrair a tabela 6 por padrão, que parece ser a correta no seu exemplo

            table_index_to_try = 5 # Índice 5 para a Tabela 6
            tables = camelot.read_pdf(file_path, pages=pages, flavor='lattice')
            
            if len(tables) > table_index_to_try:
                 self.df = tables[table_index_to_try].df
                 print(f"\n📖 Extraindo Tabela {table_index_to_try + 1} por padrão.")
            elif tables:
                 self.df = tables[0].df
                 print("Tabela 6 não encontrada, extraindo a primeira tabela disponível.")
            else:
                 self.df = pd.DataFrame()
                 print("Nenhuma tabela encontrada no PDF.")

        except Exception as e:
            print(f"Erro ao extrair tabela: {e}")
            self.df = pd.DataFrame()
        
        return self

    def force_all_columns_as_text(self):
        """Força todas as colunas como texto (equivalente ao TransformColumnTypes)."""
        for col in self.df.columns:
            self.df[col] = self.df[col].astype(str)
        return self

    # -------------------- MANIPULAÇÃO DE CABEÇALHOS --------------------
    def extract_header_rows(self, n_rows: int = 2):
        """Captura as primeiras n linhas e remove do DataFrame."""
        if len(self.df) < n_rows:
            print(f"DataFrame tem apenas {len(self.df)} linhas, menor que {n_rows}")
            return self
        
        self.header_rows = [self.df.iloc[i].tolist() for i in range(n_rows)]
        self.df = self.df.iloc[n_rows:].reset_index(drop=True)
        return self

    def create_concatenated_headers(self):
        """Cria nomes de colunas concatenados a partir das linhas de cabeçalho extraídas."""
        if not hasattr(self, 'header_rows') or len(self.header_rows) < 2:
            print("Nenhuma linha de cabeçalho encontrada. Execute extract_header_rows primeiro.")
            return self
        
        linha1, linha2 = self.header_rows[0], self.header_rows[1]
        
        colunas_concatenadas = []
        for i in range(len(linha1)):
            parte1 = str(linha1[i]).strip() if linha1[i] is not None else ""
            parte2 = str(linha2[i]).strip() if linha2[i] is not None else ""
            
            if parte1 in ["None", "nan", "_"]: parte1 = ""
            if parte2 in ["None", "nan", "_"]: parte2 = ""
            
            if not parte1 and not parte2:
                nome = f"Coluna{i + 1}"
            else:
                nome = f"{parte1} {parte2}".strip()
            
            colunas_concatenadas.append(nome)
        
        colunas_unicas = []
        for i, current_name in enumerate(colunas_concatenadas):
            if current_name in colunas_concatenadas[:i]:
                count = colunas_concatenadas[:i].count(current_name)
                nome_unico = f"{current_name} {count}"
            else:
                nome_unico = current_name
            colunas_unicas.append(nome_unico)
        
        self.df.columns = colunas_unicas
        return self

    # -------------------- EXTRAÇÃO DE DADOS (NOVA LÓGICA) --------------------
    def identify_columns_with_parentheses(self):
        """Identifica colunas que contêm dados entre parênteses."""
        self.columns_to_process = []
        for col in self.df.columns:
            # Verifica se alguma célula na coluna contém o padrão (...)
            if self.df[col].str.contains(r'\(.*\)', na=False).any():
                self.columns_to_process.append(col)
        print(f"🔍 Colunas para extrair anotações: {self.columns_to_process}")
        return self

    def extract_data_from_parentheses(self):
        """
        Extrai dados de parênteses para uma nova coluna 'Anotacao' e
        limpa a coluna original 'Valor'.
        """
        if not hasattr(self, 'columns_to_process'):
            self.identify_columns_with_parentheses()
        
        tabela_atual = self.df.copy()
        
        for nome_coluna in self.columns_to_process:
            novos_nomes = [f"{nome_coluna} Valor", f"{nome_coluna} Anotacao"]
            
            # 1. Extrai o conteúdo DENTRO dos parênteses para a coluna "Anotacao"
            # Ex: "44,100(BR)" -> "BR"
            tabela_atual[novos_nomes[1]] = tabela_atual[nome_coluna].str.extract(r'\((.*?)\)').fillna('')
            
            # 2. Remove o conteúdo dos parênteses (e os próprios parênteses) da coluna "Valor"
            # Ex: "44,100(BR)" -> "44,100"
            tabela_atual[novos_nomes[0]] = tabela_atual[nome_coluna].str.replace(r'\s*\([^)]*\)', '', regex=True).str.strip()
            
            # Remove a coluna original que já foi processada
            tabela_atual = tabela_atual.drop(columns=[nome_coluna])
            
        self.df = tabela_atual
        print(f"✂️ Extração concluída. Novas colunas: {len(self.df.columns)}")
        return self

    # -------------------- PADRONIZAÇÃO DE NOMES --------------------
    def standardize_column_names(self, mapping: Dict[str, str]):
        """Padroniza nomes das colunas (equivalente ao RenameColumns do Power Query)."""
        existing_mapping = {old: new for old, new in mapping.items() if old in self.df.columns}
        self.df = self.df.rename(columns=existing_mapping)
        
        missing = set(mapping.keys()) - set(self.df.columns)
        if missing:
            print(f"Aviso: As seguintes colunas do mapeamento não foram encontradas no DataFrame final: {missing}")
        
        return self

    # -------------------- FUNÇÃO PRINCIPAL --------------------
    def read_must_tables(self, pdf_path: str, pages: str = "all"):
        """
        Função principal que replica o comportamento do Power Query com a nova lógica.
        """
        column_mapping = {
            "Ponto de Conexão Cód ONS¹": "Cód ONS",
            "Ponto de Conexão Instalação": "Instalação",
            "Ponto de Conexão Tensão \n(kV)": "Tensão (kV)",
            "Período de \nContratação De": "De",
            "Período de \nContratação Até": "Até",
            "MUST - 2025 Ponta \n(MW) Valor": "Ponta 2025 Valor",
            "MUST - 2025 Ponta \n(MW) Anotacao": "Ponta 2025 Anotacao",
            "Fora \nPonta \n(MW) Valor": "Fora Ponta 2025 Valor",
            "Fora \nPonta \n(MW) Anotacao": "Fora Ponta 2025 Anotacao",
            "MUST - 2026 Ponta \n(MW) Valor": "Ponta 2026 Valor",
            "MUST - 2026 Ponta \n(MW) Anotacao": "Ponta 2026 Anotacao",
            "Fora \nPonta \n(MW) 1 Valor": "Fora Ponta 2026 Valor",
            "Fora \nPonta \n(MW) 1 Anotacao": "Fora Ponta 2026 Anotacao",
            "MUST - 2027 Ponta \n(MW) Valor": "Ponta 2027 Valor",
            "MUST - 2027 Ponta \n(MW) Anotacao": "Ponta 2027 Anotacao",
            "Fora \nPonta \n(MW) 2 Valor": "Fora Ponta 2027 Valor",
            "Fora \nPonta \n(MW) 2 Anotacao": "Fora Ponta 2027 Anotacao",
            "MUST - 2028 Ponta \n(MW) Valor": "Ponta 2028 Valor",
            "MUST - 2028 Ponta \n(MW) Anotacao": "Ponta 2028 Anotacao",
            "Fora \nPonta \n(MW) 3 Valor": "Fora Ponta 2028 Valor",
            "Fora \nPonta \n(MW) 3 Anotacao": "Fora Ponta 2028 Anotacao",
        }
        
        print("🔍 Iniciando processamento do PDF...")
        
        (self
         .analyze_pdf(pdf_path)
         .from_pdf_table(pdf_path, pages=pages)
         .force_all_columns_as_text()
         .extract_header_rows(2)
         .create_concatenated_headers()
         .identify_columns_with_parentheses() # Nova função
         .extract_data_from_parentheses()   # Nova função
         .standardize_column_names(column_mapping)
         )
        
        print("\n\n✅ Processamento concluído!")
        print(f"📊 DataFrame final: {self.df.shape[0]} linhas x {self.df.shape[1]} colunas")
        print(f"\n\n📋 Colunas: {list(self.df.columns)}")
        
        return self

    # -------------------- OPERAÇÕES AUXILIARES --------------------
    def drop_nulls(self, cols=None):
        self.df = self.df.dropna(subset=cols)
        return self

    def drop_duplicates(self, cols=None):
        self.df = self.df.drop_duplicates(subset=cols)
        return self

    def trim_spaces(self):
        # O .strip() já é aplicado durante a extração, mas podemos garantir
        self.df = self.df.map(lambda x: x.strip() if isinstance(x, str) else x)
        return self

    def preview(self, n: int = 5):
        print(f"\n📋 Preview ({n} primeiras linhas):")
        # Exibe todas as colunas para melhor visualização
        with pd.option_context('display.max_rows', None, 'display.max_columns', None):
            print(self.df.head(n))
        return self

    # -------------------- EXPORTAÇÃO --------------------
    def export_excel(self, output_path: str):
        self.df.to_excel(output_path, index=False)
        print(f"\n\n📁 Arquivo Excel exportado: {output_path}")
        return self