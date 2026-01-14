import os
import streamlit as st
import google.generativeai as genai
import pandas as pd
from openpyxl import load_workbook
from docx import Document
import cv2
import numpy as np
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from rich_menu import Menu
from rich.panel import Panel

# Substitua pelos seus dados de exemplo
DATABASE_DATA = {
    "EMPLOYEES": [
        {"NAME": "João", "EMPLOYEEID": 1, "AGE": 30, "EXPERIENCE": 5},
        {"NAME": "Maria", "EMPLOYEEID": 2, "AGE": 25, "EXPERIENCE": 2},
        {"NAME": "Carlos", "EMPLOYEEID": 3, "AGE": 40, "EXPERIENCE": 10},
        {"NAME": "Ana", "EMPLOYEEID": 4, "AGE": 35, "EXPERIENCE": 7},
        {"NAME": "Pedro", "EMPLOYEEID": 5, "AGE": 28, "EXPERIENCE": 3},
    ]
}

class C3PO:
    def __init__(self):
        # Carrega as variáveis de ambiente do arquivo .env
        load_dotenv()
        # Configura a API do Google Gemini com a chave da API
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        # Inicializa o modelo Gemini
        self.gemini_model = genai.GenerativeModel('gemini-pro')
        self.console = Console()

    def generate_gemini_response(self, prompt, question):
        """
        Gera uma resposta usando o modelo Gemini.

        Args:
            prompt (str): O prompt a ser usado pelo modelo.
            question (str): A pergunta a ser respondida.

        Returns:
            str: A resposta gerada pelo modelo.
        """
        try:
            response = self.gemini_model.generate_content([prompt, question])
            return response.text
        except Exception as e:
            self.console.print(Panel(f"Erro ao gerar resposta do Gemini: {e}", title="Erro", border_style="red"))
            return None

    def execute_sql_query(self, sql):
        """
        Executa uma consulta SQL simulada no banco de dados.

        Args:
            sql (str): A consulta SQL a ser executada.

        Returns:
            tuple: Uma tupla contendo as linhas retornadas pela consulta e os nomes das colunas.
                   Retorna (None, None) em caso de erro.
        """
        try:
            # Simula a execução da consulta SQL
            if "SELECT" in sql.upper():
                if "EMPLOYEES" in sql.upper():
                    data = DATABASE_DATA["EMPLOYEES"]
                    columns = list(data[0].keys()) if data else []
                    filtered_data = data
                    if "WHERE" in sql.upper():
                        condition = sql.split("WHERE")[1].strip()
                        filtered_data = []
                        for row in data:
                            try:
                                if eval(condition.replace(columns[0], f"row['{columns[0]}']").replace(columns[1], f"row['{columns[1]}']").replace(columns[2], f"row['{columns[2]}']").replace(columns[3], f"row['{columns[3]}']")):
                                    filtered_data.append(row)
                            except:
                                self.console.print(Panel(f"Erro ao avaliar condição: {condition}. Retornando todos os dados.", title="Erro", border_style="red"))
                                filtered_data = data
                    if "COUNT(*)" in sql.upper():
                         return [{"COUNT(*)": len(filtered_data)}], ["COUNT(*)"]
                    elif "*" in sql:
                        return filtered_data, columns
                    else:
                        selected_columns = [col.strip() for col in sql.split("SELECT")[1].split("FROM")[0].split(",")]
                        result = []
                        for row in filtered_data:
                            new_row = {}
                            for col in selected_columns:
                                if col in columns:
                                    new_row[col] = row[col]
                            result.append(new_row)
                        return result, selected_columns

                else:
                    self.console.print(Panel("Tabela não encontrada. A tabela 'EMPLOYEES' é a única disponível.", title="Erro", border_style="red"))
                    return None, None
            elif "INSERT" in sql.upper():
                table_name = sql.split("INTO")[1].split("(")[0].strip()
                if table_name == "EMPLOYEES":
                    columns_str = sql.split("(")[1].split(")")[0].split(",")
                    values_str = sql.split("VALUES")[1].split(")")[0].split(",")
                    columns = [col.strip() for col in columns_str]
                    values = [eval(v.strip()) for v in values_str]  # Use eval carefully!
                    if len(columns) != len(values):
                        self.console.print(Panel("Número de colunas e valores não correspondem.", title="Erro", border_style="red"))
                        return None, None
                    new_employee = dict(zip(columns, values))
                    DATABASE_DATA["EMPLOYEES"].append(new_employee)
                    self.console.print(Panel(f"Novo empregado inserido: {new_employee}", title="Sucesso", border_style="green"))
                    return None, None
                else:
                    self.console.print(Panel("Tabela não encontrada. A tabela 'EMPLOYEES' é a única disponível.", title="Erro", border_style="red"))
                    return None, None
            else:
                self.console.print(Panel("Consulta não suportada. Use SELECT ou INSERT.", title="Erro", border_style="red"))
                return None, None
        except Exception as e:
            self.console.print(Panel(f"Erro ao executar consulta SQL: {e}", title="Erro", border_style="red"))
            return None, None

    def read_excel_file(self, file_path):
        """
        Lê um arquivo Excel usando o Pandas.

        Args:
            file_path (str): O caminho do arquivo Excel.

        Returns:
            pandas.DataFrame: Um DataFrame com os dados do arquivo, ou None em caso de erro.
        """
        try:
            df = pd.read_excel(file_path)
            return df
        except FileNotFoundError:
            st.error(f"Erro: Arquivo não encontrado em {file_path}")
            return None
        except Exception as e:
            st.error(f"Erro ao ler o arquivo XLSX: {e}")
            return None

    def read_docx_file(self, file_path):
        """
        Lê um arquivo DOCX usando a biblioteca docx.

        Args:
            file_path (str): O caminho do arquivo DOCX.

        Returns:
            str: O texto do documento, ou None em caso de erro.
        """
        try:
            document = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in document.paragraphs])
            return text
        except FileNotFoundError:
            st.error(f"Erro: Arquivo não encontrado em {file_path}")
            return None
        except Exception as e:
            st.error(f"Erro ao ler o arquivo DOCX: {e}")
            return None

    def read_image_file(self, file_path):
        """
        Lê um arquivo de imagem usando o OpenCV.

        Args:
            file_path (str): O caminho do arquivo de imagem.

        Returns:
            numpy.ndarray: A imagem como um array NumPy, ou None em caso de erro.
        """
        try:
            img = cv2.imread(file_path)
            return img
        except FileNotFoundError:
            st.error(f"Erro: Arquivo não encontrado em {file_path}")
            return None
        except Exception as e:
            st.error(f"Erro ao ler o arquivo de imagem: {e}")
            return None

    def display_data(self, data, columns=None):
        """
        Exibe os dados no Streamlit de acordo com o tipo.

        Args:
            data: Os dados a serem exibidos.
            columns (list, optional): Os nomes das colunas, se aplicável. Padrão: None.
        """
        # Verifica se é uma lista de linhas e nomes de colunas
        if isinstance(data, list) and columns:
            try:
                df = pd.DataFrame(data, columns=columns)
                st.dataframe(df)
            except Exception as e:
                st.error(f"Erro ao exibir DataFrame: {e}")
        elif isinstance(data, list):
            try:
                for row in data:
                    st.header(row)
            except Exception as e:
                st.error(f"Erro ao exibir lista de dados: {e}")
        elif isinstance(data, pd.DataFrame):
            try:
                st.dataframe(data)
            except Exception as e:
                st.error(f"Erro ao exibir DataFrame: {e}")
        elif isinstance(data, str):
            try:
                st.text_area("Conteúdo:", data, height=300)
            except Exception as e:
                st.error(f"Erro ao exibir texto: {e}")
        elif data is not None and len(data.shape) == 3:  # Verifica se é uma imagem (3 dimensões)
            try:
                st.image(data, caption="Imagem Processada", use_column_width=True)
            except Exception as e:
                st.error(f"Erro ao exibir imagem: {e}")
        elif data is not None:
            try:
                st.write(data)
            except Exception as e:
                st.error(f"Erro ao exibir dados: {e}")
        else:
            st.info("Nada para exibir.")

    def terminal_menu(self):
        """
        Exibe um menu interativo no terminal usando Rich.
        """
        console = Console()
        menu = Menu("C3PO - Menu Principal", "Selecione uma opção:", choices=[
            ("1", "Executar Consulta SQL"),
            ("2", "Interagir com Arquivos"),
            ("3", "Conversar com o Chatbot"),
            ("4", "Inserir dados de exemplo"),
            ("0", "Sair"),
        ])
        while True:
            choice = menu.ask(console)
            if choice == "1":
                self.terminal_sql_query()
            elif choice == "2":
                self.terminal_file_interaction()
            elif choice == "3":
                self.terminal_chatbot()
            elif choice == "4":
                self.terminal_insert_data()
            elif choice == "0":
                console.print(Panel("Saindo do C3PO...", border_style="green"))
                break
            else:
                console.print(Panel("Opção inválida. Tente novamente.", border_style="red"))

    def terminal_sql_query(self):
        """
        Executa a funcionalidade de consulta SQL no terminal.
        """
        console = Console()
        prompt = [
            """
            Atue como um especialista em converter perguntas em consulta SQL
            O banco de dados SQL tem o nome EMPLOYEES e tem as seguintes colunas - NAME, EMPLOYEEID,
            AGE e EXPERIENCE. Por exemplo:
            - Exemplo 1: "Quantos registros estão presentes?" resultaria no comando SQL:
              SELECT COUNT(*) FROM EMPLOYEES;
            - Exemplo 2: "Me diga todos os empregados com mais de 2 anos de experiência?" resultaria em:
              SELECT * FROM EMPLOYEES WHERE EXPERIENCE >= 2;
            Além disso, garanta que o código SQL de saída não contenha ``` no início ou no fim, nem a palavra "sql" nele.
            """
        ]

        question = Prompt.ask(console, "Faça uma pergunta SQL")
        sql_query = self.generate_gemini_response(prompt[0], question)
        if sql_query:
            console.print(Panel(f"Consulta SQL Gerada:\n{sql_query}", title="Consulta SQL", border_style="blue"))
            response, columns = self.execute_sql_query(sql_query)
            if response:
                console.print(Panel("Resposta da Consulta SQL:", border_style="green"))
                if columns:
                  df = pd.DataFrame(response, columns=columns)
                  console.print(df)
                else:
                    console.print(response)
            else:
                console.print(Panel("Nenhum resultado retornado.", border_style="yellow"))

    def terminal_file_interaction(self):
        """
        Executa a funcionalidade de interação com arquivos no terminal.
        """
        console = Console()
        file_path = Prompt.ask(console, "Digite o caminho do arquivo (XLSX, DOCX, JPG, JPEG, PNG)")
        if not os.path.exists(file_path):
            console.print(Panel(f"Erro: Arquivo não encontrado em {file_path}", title="Erro", border_style="red"))
            return

        file_extension = file_path.split('.')[-1].lower()
        if file_extension == "xlsx":
            console.print(Panel("Conteúdo do Arquivo Excel:", border_style="blue"))
            df = self.read_excel_file(file_path)
            if df is not None:
                console.print(df)
        elif file_extension == "docx":
            console.print(Panel("Conteúdo do Documento Word:", border_style="blue"))
            text = self.read_docx_file(file_path)
            if text is not None:
                console.print(text)
        elif file_extension in ["jpg", "jpeg", "png"]:
            console.print(Panel("Imagem Carregada:", border_style="blue"))
            image = self.read_image_file(file_path)
            if image is not None:
                console.print(image) # não consigo exibir a imagem no terminal
                console.print("Imagem não pode ser exibida no terminal. Abra o arquivo para visualizá-la.")
        else:
            console.print(Panel("Tipo de arquivo não suportado.", title="Erro", border_style="red"))

    def terminal_chatbot(self):
        """
        Executa um chatbot simples no terminal.
        """
        console = Console()
        console.print(Panel("Bem-vindo ao Chatbot C3PO! Diga 'sair' para encerrar.", border_style="green"))
        prompt = "Você é um chatbot chamado C3PO."
        while True:
            question = Prompt.ask(console, "Você")
            if question.lower() == "sair":
                console.print(Panel("Encerrando o Chatbot C3PO...", border_style="green"))
                break
            response = self.generate_gemini_response(prompt, question)
            if response:
                console.print(Panel(f"C3PO: {response}", border_style="blue"))

    def terminal_insert_data(self):
        """
        Executa a inserção de dados de exemplo no terminal.
        """
        console = Console()
        console.print(Panel("Inserindo dados de exemplo na tabela EMPLOYEES.", border_style="green"))
        sql = "INSERT INTO EMPLOYEES (NAME, EMPLOYEEID, AGE, EXPERIENCE) VALUES ('Novo Empregado', 6, 30, 5)"
        self.execute_sql_query(sql)
        console.print(Panel("Dados de exemplo inseridos com sucesso.", border_style="green"))

    def streamlit_ui(self):
        """
        Cria a interface do Streamlit.
        """
        st.title("C3PO")
        menu = ["Consulta SQL", "Interagir com Arquivos", "Conversar com o Chatbot", "Inserir Dados de Exemplo"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Consulta SQL":
            self.streamlit_sql_query()
        elif choice == "Interagir com Arquivos":
            self.streamlit_file_interaction()
        elif choice == "Conversar com o Chatbot":
            self.streamlit_chatbot()
        elif choice == "Inserir Dados de Exemplo":
            self.streamlit_insert_data()

    def streamlit_sql_query(self):
        """
        Executa a funcionalidade de consulta SQL no Streamlit.
        """
        st.header("Executar Consulta SQL")
        prompt = [
            """
            Atue como um especialista em converter perguntas em consulta SQL
            O banco de dados SQL tem o nome EMPLOYEES e tem as seguintes colunas - NAME, EMPLOYEEID,
            AGE e EXPERIENCE. Por exemplo:
            - Exemplo 1: "Quantos registros estão presentes?" resultaria no comando SQL:
              SELECT COUNT(*) FROM EMPLOYEES;
            - Exemplo 2: "Me diga todos os empregados com mais de 2 anos de experiência?" resultaria em:
              SELECT * FROM EMPLOYEES WHERE EXPERIENCE >= 2;
            Além disso, garanta que o código SQL de saída não contenha ``` no início ou no fim, nem a palavra "sql" nele.
            """
        ]

        question = st.text_input("Faça uma pergunta SQL:", key="sql_input")
        submit_sql = st.button("Executar Consulta SQL")

        if submit_sql and question:
            sql_query = self.generate_gemini_response(prompt[0], question)
            if sql_query:
                st.subheader("Consulta SQL Gerada:")
                st.code(sql_query)
                # Removi a necessidade de server, database, uid e pwd
                response, columns = self.execute_sql_query(sql_query)
                st.subheader("Resposta da Consulta SQL:")
                self.display_data(response, columns)
            else:
                st.error("Não foi possível gerar a consulta SQL.")

    def streamlit_file_interaction(self):
        """
        Executa a funcionalidade de interação com arquivos no Streamlit.
        """
        st.header("Interagir com Arquivos")
        uploaded_file = st.file_uploader("Carregue um arquivo (XLSX, DOCX ou Imagem)",
                                        type=["xlsx", "docx", "jpg", "jpeg", "png"])

        if uploaded_file is not None:
            file_extension = uploaded_file.name.split('.')[-1].lower()

            if file_extension == "xlsx":
                st.subheader("Conteúdo do Arquivo Excel:")
                df = self.read_excel_file(uploaded_file)
                self.display_data(df)
            elif file_extension == "docx":
                st.subheader("Conteúdo do Documento Word:")
                text = self.read_docx_file(uploaded_file)
                self.display_data(text)
            elif file_extension in ["jpg", "jpeg", "png"]:
                st.subheader("Imagem Carregada:")
                image = self.read_image_file(uploaded_file)
                self.display_data(image)
    def streamlit_chatbot(self):
        """
        Executa um chatbot simples no Streamlit.
        """
        st.header("Chatbot C3PO")
        st.write("Bem-vindo ao Chatbot C3PO! Diga 'sair' para encerrar.")
        prompt = "Você é um chatbot chamado C3PO."
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["sender"]):
                st.markdown(message["text"])

        if question := st.chat_input("Você"):
            st.session_state.messages.append({"sender": "Você", "text": question})
            with st.chat_message("Você"):
                st.markdown(question)

            if question.lower() == "sair":
                st.write("Encerrando o Chatbot C3PO...")
            else:
                response = self.generate_gemini_response(prompt, question)
                if response:
                  st.session_state.messages.append({"sender": "C3PO", "text": response})
                  with st.chat_message("C3PO"):
                    st.markdown(response)
                else:
                    st.error("Erro ao obter resposta do Chatbot.")

    def streamlit_insert_data(self):
        """
        Executa a inserção de dados de exemplo no Streamlit.
        """
        st.header("Inserir Dados de Exemplo")
        if st.button("Inserir Dados de Exemplo"):
            sql = "INSERT INTO EMPLOYEES (NAME, EMPLOYEEID, AGE, EXPERIENCE) VALUES ('Novo Empregado', 6, 30, 5)"
            self.execute_sql_query(sql)
            st.success("Dados de exemplo inseridos com sucesso.")

def main():
    c3po = C3PO()
    if len(sys.argv) > 1 and sys.argv[1] == "terminal":
        c3po.terminal_menu()
    else:
        c3po.streamlit_ui()

if __name__ == "__main__":
    import sys
    main()