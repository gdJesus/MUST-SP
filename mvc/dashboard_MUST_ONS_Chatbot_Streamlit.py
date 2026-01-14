import streamlit as st
from pathlib import Path

# --- Dependências da Interface e Análise de PDF ---
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
import camelot


from view import render_texto_tab, render_tabelas_tab, ChatbotWithRAG
from components import read_must_tables_page, tab_extract_text_ocr
from controller import PDFController

# --- Dependências para o Chatbot com Contexto ---
from langchain_community.document_loaders import PyMuPDFLoader # Langchain ainda é útil para carregar o PDF


#st.set_page_config(layout="wide", page_icon="📄", page_title="Dashboard ONS", initial_sidebar_state="expanded")


def SideBar(temp_pdf_path):
    # --- Sidebar ---
    with st.sidebar:
        with st.spinner("Analisando documento..."):
            try:
                # Conta páginas
                reader = PdfReader(temp_pdf_path)
                num_pages = len(reader.pages)
                st.info(f"Total de páginas: {num_pages}")

                # Conta tabelas
                tables = camelot.read_pdf(temp_pdf_path, pages='all', flavor='lattice')
                st.info(f"Tabelas encontradas: {len(tables)}")

            except Exception as e:
                st.error(f"Erro na análise: {e}")
                num_pages = 0
        
        # Botão para extrair o texto completo para o chatbot
        if st.button("Preparar Chatbot com Conteúdo do PDF"):
            st.session_state.messages = [] 
            with st.spinner("A extrair texto completo para a IA..."):
                try:
                    loader = PyMuPDFLoader(str(temp_pdf_path))
                    docs = loader.load()
                    st.session_state.pdf_context = "\n\n".join([doc.page_content for doc in docs])
                    st.success("Chatbot preparado!")
                except Exception as e:
                    st.session_state.pdf_context = None
                    st.error(f"Erro ao extrair texto: {e}")

        # Renderiza as páginas do PDF
        if num_pages > 0:
            st.subheader("Visualização do PDF")
            with st.spinner("A renderizar páginas..."):
                try:
                    images = convert_from_path(str(temp_pdf_path))
                    for i, image in enumerate(images):
                        st.image(image, caption=f"Página {i + 1}", use_column_width=True)
                except Exception:
                    st.warning("Não foi possível renderizar o PDF. Verifique se o Poppler está instalado e no PATH do sistema.")

# --- Interface Principal ---
def Dashboard_MUST_PDF_RAG():
    

    st.title("📄 Dashboard MUST 2025 -  ONS")

    if "pdf_context" not in st.session_state:
        st.session_state.pdf_context = None
    if "messages" not in st.session_state:
        st.session_state.messages = []

    uploaded_file = st.sidebar.file_uploader("Escolha um arquivo PDF", type="pdf")

    if uploaded_file:

        # Define o caminho do script para garantir que o arquivo seja salvo no lugar certo.
        script_dir = Path(__file__).parent
        temp_pdf_path = script_dir / "temp_uploaded_file.pdf"
       
        with open(temp_pdf_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        controller = PDFController(temp_pdf_path)

        SideBar(temp_pdf_path)

        pages = st.text_input("Páginas para extração (ex: 1-3,5 ou 'all')", value='all')

        # Tabs for functionalities
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📂 Funcionalidades",
            "📄 Extrair Texto (PyPDF2)", 
            "👁️ Extrair Texto (OCR)", 
            "📊 Extrair Tabelas (Camelot)",
            "🤖 Chatbot"
        ])

        with tab1:
            read_must_tables_page(controller, pages)

        with tab2:
            render_texto_tab(PdfReader(temp_pdf_path))

        with tab3:
            tab_extract_text_ocr(controller)

        with tab4:
            render_tabelas_tab(str(temp_pdf_path))

        with tab5:
            # Passa o nome original do arquivo para exibição
            ChatbotWithRAG(uploaded_file.name)



Dashboard_MUST_PDF_RAG()