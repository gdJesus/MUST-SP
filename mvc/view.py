# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd

class PDFView:
    """
    Classe responsável por gerenciar a interface do usuário com Streamlit.
    """

    @staticmethod
    def display_pdf_details(file_name: str, num_pages: int):
        """
        Exibe os detalhes do PDF na interface.

        Args:
            file_name (str): Nome do arquivo PDF.
            num_pages (int): Número de páginas no PDF.
        """
        st.subheader("Detalhes do PDF")
        st.write(f"**Nome:** {file_name}")
        st.write(f"**Páginas:** {num_pages}")
        st.markdown("---")

    @staticmethod
    def display_extracted_text(text: str):
        """
        Exibe o texto extraído na interface.

        Args:
            text (str): Texto extraído do PDF.
        """
        st.text_area("Texto Extraído", text, height=300)

    @staticmethod
    def display_extracted_tables(tables: list):
        """
        Exibe as tabelas extraídas na interface.

        Args:
            tables (list): Lista de DataFrames com as tabelas extraídas.
        """
        for i, df in enumerate(tables):
            st.write(f"**Tabela {i + 1}**")
            st.dataframe(df)

    @staticmethod
    def display_error(message: str):
        """
        Exibe uma mensagem de erro na interface.

        Args:
            message (str): Mensagem de erro.
        """
        st.error(message)

import os
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

# --- Dependências da Interface e Análise de PDF ---
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
import camelot

# --- Dependências para o Chatbot com Contexto ---
# MUDANÇA: Usando a biblioteca nativa do Google
import google.generativeai as genai
from langchain_community.document_loaders import PyMuPDFLoader # Langchain ainda é útil para carregar o PDF


# Carrega a chave da API do Gemini
load_dotenv()


# --- Funções Auxiliares e de Abas ---

def parse_page_string(page_str: str, max_pages: int) -> list[int]:
    """
    Converte uma string de páginas (ex: '1-3,5', 'all') em uma lista de índices (0-based).
    """
    if page_str.lower().strip() == 'all':
        return list(range(max_pages))

    pages = set()
    parts = page_str.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if start > 0 and end <= max_pages and start <= end:
                    pages.update(range(start - 1, end))
            except ValueError:
                st.warning(f"Formato de intervalo inválido: '{part}'. Ignorando.")
        else:
            try:
                page_num = int(part)
                if 1 <= page_num <= max_pages:
                    pages.add(page_num - 1)
            except ValueError:
                st.warning(f"Número de página inválido: '{part}'. Ignorando.")
    
    return sorted(list(pages))

def render_texto_tab(pdf_reader: PdfReader):
    """Renderiza o conteúdo da aba de extração de texto simples."""
    with st.container():
        st.header("Extração de Texto Simples com PyPDF2")
        
        page_selection = st.text_input("Páginas para extração (ex: 1-3,5 ou 'all')", value='all', key='text_pages')
        
        if st.button("Extrair Texto das Páginas Selecionadas"):
            with st.spinner("A ler texto..."):
                num_total_pages = len(pdf_reader.pages)
                pages_to_extract = parse_page_string(page_selection, num_total_pages)
                
                if not pages_to_extract:
                    st.warning("Nenhuma página válida selecionada para extração.")
                
                for page_index in pages_to_extract:
                    page = pdf_reader.pages[page_index]
                    st.text_area(f"Página {page_index + 1}", page.extract_text(), height=200, key=f"text_page_{page_index}")

def render_tabelas_tab(pdf_path: str):
    """Renderiza o conteúdo da aba de extração de tabelas."""
    with st.container():
        st.header("Extração de Tabelas com Camelot")

        page_selection = st.text_input("Páginas para extração (ex: 1-3,5 ou 'all')", value='all', key='table_pages')

        if st.button("Extrair Tabelas das Páginas Selecionadas"):
            with st.spinner("A ler tabelas..."):
                try:
                    tables = camelot.read_pdf(pdf_path, pages=page_selection.strip(), flavor='lattice')
                    if tables:
                        st.success(f"Encontradas {len(tables)} tabelas nas páginas selecionadas.")
                        for i, table in enumerate(tables):
                            st.write(f"**Tabela {i+1} (Página {table.page})**")
                            st.dataframe(table.df)
                    else:
                        st.info("Nenhuma tabela foi encontrada nas páginas especificadas.")
                except Exception as e:
                    st.error(f"Ocorreu um erro ao extrair as tabelas: {e}")


def get_gemini_response(prompt: str, pdf_context: str) -> str:
    """Função de backend que chama a API do Gemini e retorna a resposta."""
    try:
        GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
        if not GOOGLE_API_KEY:
            return "Erro: Chave da API do Gemini não encontrada. Verifique o arquivo .env"

        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        full_prompt = (
            "Você é um assistente especialista em analisar documentos técnicos da ONS. "
            "Responda a pergunta do usuário baseando-se SOMENTE no seguinte contexto extraído de um PDF:\n\n"
            f"--- CONTEXTO ---\n{pdf_context}\n--- FIM DO CONTEXTO ---\n\n"
            f"Pergunta do Usuário: {prompt}"
        )
        
        response = model.generate_content(full_prompt)
        return response.text
        
    except Exception as e:
        return f"Ocorreu um erro ao comunicar com a IA: {e}"



# CSS Aprimorado:
# - .chat-container: Removido height fixo, adicionado max-height e flex-end para alinhar o conteúdo embaixo.
# - Removido display: flex e flex-direction: column-reverse para um fluxo de chat natural (de cima para baixo).
st.markdown("""
<style>
    .main-header {
        text-align: center; padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px; margin-bottom: 2rem; color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .chat-container {
        background: #ffffff; border: 1px solid #e0e0e0;
        border-radius: 15px; padding: 1rem; margin: 1rem 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        max-height: 65vh; /* Altura máxima para evitar que o chat ocupe a tela inteira */
        overflow-y: auto; /* Adiciona scroll quando o conteúdo excede a altura máxima */
        display: flex;
        flex-direction: column;
    }
    .role-card {
        background: linear-gradient(45deg, #4CAF50, #45a049);
        color: white; padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0;
        font-weight: 500; font-size: 0.9em; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .system-message {
        background: linear-gradient(45deg, #FF6B6B, #FF8E8E);
        color: white; padding: 0.8rem; border-radius: 8px; margin: 0.5rem 0;
        font-weight: 500; font-size: 0.9em;
    }
    .stButton > button {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white; border: none; border-radius: 25px; padding: 0.5rem 1.5rem;
        font-weight: 600; transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)


def ChatbotWithRAG(uploaded_file_name: str):

    """Renderiza a interface e a lógica do chatbot."""
    with st.container():
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)

        st.header("Converse com o Documento PDF da sua Empresa.")

        if st.session_state.pdf_context is None:
            st.info("⬅️ Clique em 'Preparar Chatbot com Conteúdo do PDF' na barra lateral para começar.")
        else:
            st.success(f"Assistente pronto para responder sobre: **{uploaded_file_name}**")
            
            # Ordem cronológica normal (de cima para baixo)
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            st.markdown('</div>', unsafe_allow_html=True)

            
            if prompt := st.chat_input("Faça sua pergunta sobre o PDF..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("🤔 Pensando e analisando o documento..."):
                        response = get_gemini_response(prompt, st.session_state.pdf_context)
                        st.markdown(response)
                
                st.session_state.messages.append({"role": "assistant", "content": response})





