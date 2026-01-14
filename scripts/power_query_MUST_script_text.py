# -*- coding: utf-8 -*-
import pandas as pd
import re
from PyPDF2 import PdfReader
import os

class PDFAnnotationLinker:
    """
    Esta classe foi projetada para analisar o texto de um PDF, identificar
    as tabelas de MUST e extrair informações específicas:
    - O Cód ONS e a Instalação de cada linha que contém uma anotação nos dados.
    - O texto completo de cada anotação.
    - O objetivo é criar um vínculo direto entre uma linha de dados e a
      condição textual que se aplica a ela, ignorando anotações no nome da Instalação.
    """

    def __init__(self, pdf_path: str):
        """
        O construtor da classe. Ele é executado assim que criamos um objeto.
        Sua função é preparar tudo para a extração.

        Args:
            pdf_path (str): O caminho para o arquivo PDF que queremos processar.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"O arquivo não foi encontrado: {pdf_path}")
        
        self.pdf_path = pdf_path
        self.raw_text = self._extract_text_from_pdf()

        # --- DEFINIÇÃO DAS EXPRESSÕES REGULARES (REGEX) ---
        # As expressões regulares (regex) são a ferramenta mais poderosa para este tipo de extração,
        # pois permitem encontrar padrões complexos em textos.

        # 1. Regex para encontrar o título de uma tabela.
        self.table_regex = re.compile(r'Tabela\s+([0-9A-Z.]+)\s*-\s*(.*)')

        # 2. Regex para encontrar a definição de uma anotação (ex: "(A) - ...").
        self.annotation_regex = re.compile(r'^\s*\(([A-Z])\)\s*-\s*(.*)')

        # 3. Regex para identificar o início de uma linha de dados pelo Cód ONS.
        self.row_start_regex = re.compile(r'^(SP[A-Z0-9\s-]+(?:--?[A-Z])?)\s+.*')
        
        # 4. Regex AVANÇADA para extrair todas as partes de uma linha de dados.
        #    Ela usa "grupos nomeados" (?P<nome>...) para facilitar a extração.
        self.data_row_regex = re.compile(
            r'^(?P<cod_ons>SP[A-Z0-9\s-]+(?:--?[A-Z])?)\s+'  # Captura o Cód ONS
            r'(?P<instalacao>.*?)\s+'                          # Captura a Instalação (não-guloso)
            r'(?P<tensao>\d{2,3})\s+'                           # Captura a Tensão (2 ou 3 dígitos)
            r'(?P<de>\d{1,2}/[A-Za-z]{3})\s+'                   # Captura a data de início (ex: 1/Jan)
            r'(?P<ate>\d{1,2}/[A-Za-z]{3})\s+'                   # Captura a data de fim (ex: 31/Dez)
            r'(?P<must_data>.*)'                               # Captura todo o resto da linha (os dados MUST)
        )

    def _extract_text_from_pdf(self) -> str:
        """
        Função auxiliar para ler o arquivo PDF e extrair todo o texto.
        """
        print(f"📄 Lendo o arquivo: {os.path.basename(self.pdf_path)}...")
        text = ""
        try:
            reader = PdfReader(self.pdf_path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            print("✅ Texto extraído com sucesso.")
            return text
        except Exception as e:
            print(f"❌ Erro ao ler o PDF: {e}")
            return ""

    def link_annotations_to_codes(self) -> pd.DataFrame:
        """
        Esta é a função principal. Ela orquestra todo o processo de extração e vinculação.
        """
        print("🔍 Vinculando anotações aos códigos ONS...")
        lines = self.raw_text.split('\n')
        all_linked_data = []
        
        table_starts = [i for i, line in enumerate(lines) if self.table_regex.search(line)]

        if not table_starts:
            print("🔴 Nenhuma tabela no formato 'Tabela XX - ...' foi encontrada.")
            return pd.DataFrame()

        for i, start_index in enumerate(table_starts):
            end_index = table_starts[i + 1] if i + 1 < len(table_starts) else len(lines)
            block_lines = lines[start_index:end_index]
            
            table_match = self.table_regex.search(block_lines[0])
            table_number = table_match.group(1)
            table_title = table_match.group(2).strip()
            print(f"\n  -> Processando Tabela {table_number}: {table_title}")

            annotations_map = self._extract_annotations_from_block(block_lines)
            if not annotations_map:
                print("    - Nenhuma definição de anotação (ex: '(A) - ...') encontrada para esta tabela.")
                continue

            processed_lines = self._merge_wrapped_data_lines(block_lines)

            for line in processed_lines:
                match = self.data_row_regex.match(line)
                
                if match:
                    data = match.groupdict()
                    cod_ons = data['cod_ons']
                    instalacao = data['instalacao'].strip()
                    must_data = data['must_data']

                    found_letters = set(re.findall(r'\(([A-Z])\)', must_data))
                    
                    if found_letters:
                        for letter in sorted(list(found_letters)):
                            if letter in annotations_map:
                                all_linked_data.append({
                                    "Num_Tabela": table_number,
                                    "Cód ONS": cod_ons,
                                    "Instalação": instalacao,
                                    "Letra": letter,
                                    "Anotacao": annotations_map[letter]
                                })
        
        if not all_linked_data:
            print("🔴 Nenhuma anotação foi encontrada dentro das colunas de dados das tabelas.")
            return pd.DataFrame()

        print(f"\n📊 {len(all_linked_data)} vínculos entre Cód ONS e anotações foram criados.")
        return pd.DataFrame(all_linked_data)

    def _merge_wrapped_data_lines(self, block_lines: list) -> list:
        """
        Função auxiliar para juntar linhas de dados que foram quebradas.
        """
        merged_lines = []
        i = 0
        while i < len(block_lines):
            line = block_lines[i].strip()
            if self.row_start_regex.match(line):
                j = i + 1
                while j < len(block_lines):
                    next_line = block_lines[j].strip()
                    if next_line and not any([
                        self.table_regex.search(next_line),
                        self.annotation_regex.match(next_line),
                        self.row_start_regex.match(next_line)
                    ]):
                        line += " " + next_line
                        j += 1
                    else:
                        break
                merged_lines.append(line)
                i = j
            else:
                i += 1
        return merged_lines

    def _extract_annotations_from_block(self, block_lines: list) -> dict:
        """
        Esta função recebe um bloco de texto e retorna um dicionário mapeando
        cada letra de anotação ao seu texto completo.
        """
        annotations = {}
        i = 0
        while i < len(block_lines):
            line = block_lines[i].strip()
            match = self.annotation_regex.match(line)
            if match:
                letter = match.group(1)
                text = match.group(2).strip()
                
                j = i + 1
                while j < len(block_lines):
                    next_line = block_lines[j].strip()
                    if next_line and not self.annotation_regex.match(next_line):
                        text += " " + next_line
                        j += 1
                    else:
                        break
                annotations[letter] = text
                i = j
            else:
                i += 1
        return annotations

    def to_excel(self, df: pd.DataFrame, output_path: str):
        """
        Exporta o DataFrame para um arquivo Excel.
        """
        if df.empty:
            print("Nenhum dado para exportar.")
            return
        try:
            df.to_excel(output_path, index=False, engine='xlsxwriter')
            print(f"💾 Planilha de anotações vinculadas salva com sucesso em: {output_path}")
        except Exception as e:
            print(f"❌ Erro ao salvar a planilha: {e}")

def clean_final_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpa o DataFrame final para separar corretamente 'Cód ONS' e 'Instalação'.
    Esta função é chamada antes de exportar para o Excel.

    Args:
        df (pd.DataFrame): O DataFrame gerado pela extração.

    Returns:
        pd.DataFrame: O DataFrame com as colunas corrigidas.
    """
    print("🧹 Limpando e separando colunas do DataFrame final...")
    
    df_copy = df.copy()

    # Regex para capturar o Cód ONS (primeira palavra) e o resto (Instalação)
    # da coluna 'Cód ONS' que atualmente contém ambos.
    # ^(SP\S+) -> Captura o grupo 1: Começa com SP e vai até o primeiro espaço.
    # \s+(.*)  -> Captura o grupo 2: Pega todo o resto da string após o espaço.
    pattern = re.compile(r'^(SP\S+)\s+(.*)')

    # Aplica a extração em cada linha da coluna 'Cód ONS'
    # expand=True cria novas colunas no DataFrame para cada grupo capturado
    extracted_data = df_copy['Cód ONS'].str.extract(pattern)

    # Verifica se a extração produziu as duas colunas esperadas
    if not extracted_data.empty and extracted_data.shape[1] == 2:
        # Renomeia as novas colunas
        extracted_data.columns = ['Cód ONS_limpo', 'Instalação_extraida']
        
        # Atualiza o DataFrame original com os dados limpos
        # Usamos .loc para garantir que estamos modificando o df_copy
        df_copy.loc[:, 'Cód ONS'] = extracted_data['Cód ONS_limpo']
        df_copy.loc[:, 'Instalação'] = extracted_data['Instalação_extraida']
    else:
        print("⚠️ Não foi possível aplicar a separação de Cód ONS e Instalação. Verifique o padrão da regex.")

    print("✅ Limpeza concluída.")
    return df_copy

def process_single_pdf(pdf_path: str, output_folder: str):
    """
    Função de orquestração para processar um único arquivo PDF.
    """
    print(f"\n{'='*50}\nProcessando arquivo: {os.path.basename(pdf_path)}\n{'='*50}")
    
    linker = PDFAnnotationLinker(pdf_path=pdf_path)
    final_df = linker.link_annotations_to_codes()

    if not final_df.empty:
        # Chama a nova função de limpeza antes de exportar
        cleaned_df = clean_final_df(final_df)

        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_excel_path = os.path.join(output_folder, f"saida_anotacoes_{base_name}.xlsx")

        print("\n📋 Preview dos dados vinculados (após limpeza):")
        print(cleaned_df.head())

        linker.to_excel(cleaned_df, output_excel_path)

def process_folder(input_folder: str, output_folder: str):
    """
    Função de orquestração para processar todos os PDFs em uma pasta.
    """
    pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')]

    if not pdf_files:
        print(f"Nenhum arquivo PDF encontrado na pasta: {input_folder}")
        return

    for pdf_file in pdf_files:
        pdf_path = os.path.join(input_folder, pdf_file)
        process_single_pdf(pdf_path, output_folder)



# --- PONTO DE PARTIDA DO SCRIPT ---
if __name__ == "__main__":
    
    # --- CONFIGURAÇÃO ---

    mode = "folder"  # Pode ser "single" ou "folder"

    # Caminho para a pasta onde estão seus arquivos
    input_folder = r"C:\Users\pedrovictor.veras\OneDrive - Operador Nacional do Sistema Eletrico\Documentos\ESTAGIO_ONS_PVRV_2025\AUTOMACÕES ONS\arquivos"
    
    # Nome do arquivo específico a ser usado no modo "single"
    single_file_name = "CUST-2002-123-41 - JAGUARI - RECON 2025-2028.pdf"

    # Pasta para salvar os resultados
    output_folder = os.path.join(input_folder, "anotacoes_extraidas")
    os.makedirs(output_folder, exist_ok=True)

    # --- EXECUÇÃO ---
    if mode == "single":
        pdf_path = os.path.join(input_folder, single_file_name)
        if os.path.exists(pdf_path):
            process_single_pdf(pdf_path, output_folder)
        else:
            print(f"ERRO: O arquivo '{single_file_name}' não foi encontrado na pasta de entrada.")
    
    elif mode == "folder":
        process_folder(input_folder, output_folder)
        
    else:
        print(f"ERRO: Modo '{mode}' inválido. Use 'single' ou 'folder'.")

    # --- FIM DO SCRIPT ---
    print("\n🔚 script de automação de extração de texto concluído.")