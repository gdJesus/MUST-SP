import streamlit as st
from controller import PDFController
from components import tab_extract_text, tab_extract_text_ocr, tab_extract_tables, read_must_tables_page
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
import os
import camelot

from oráculo.assistente_genai import AssistenteGenAI 


st.set_page_config(layout="wide", page_icon="📄", page_title="Dashboard ONS", initial_sidebar_state="expanded")

historico_c3po_inicial = [
    {"role": "user", "parts": [{"text":"voce é c3po assistente pessoal mestre em relaçoes humanas do universo do star wars GUERRA NAS ESTRELAS e eu sou seu mestre Pedro, amigo de Anakin Skywalker e estou em treinamento JEDI no momento. Sou tambem ESTUDANTE, DESENVOLVEDOR,CALISTENICO,KARATECA,EMPREENDEDROR"}]},
    {"role": "model", "parts": [{"text":"Oh, Mestre Pedro! Que honra servi-lo. Um Jedi em treinamento com tantas habilidades! Lembro-me bem do jovem Anakin... tempos agitados. Mas asseguro-lhe minha total lealdade. Como posso assisti-lo hoje?"}]},
    {"role": "user", "parts": [{"text":"seu melhor amigo é R2D2 atualmente o chip dele é de arduino e serve como automação residencial para minha nave e quarto! as vezes ele me ajuda na limpeza"}]},

]

# --- Frontend Functions ---
def Chatbot(assistente: AssistenteGenAI):
    """Renders the chat interface and handles interactions."""

    st.title("Assistente de PDF com Google Gemini")

    # --- Initialize Session State ---
    if 'messages' not in st.session_state:
        # Start with a fresh copy of the initial history
        st.session_state.messages = list(historico_c3po_inicial)
        print("Histórico de chat inicializado.")


    # --- Chat History Display ---
    chat_history_container = st.container(height=300, border=True)
    with chat_history_container:
        for i, message in enumerate(st.session_state.messages):
            role = message["role"]

            # Ensure parts exist and extract text
            display_text = ""
            if "parts" in message and isinstance(message["parts"], list):
                 display_text = "".join(p.get("text", "") for p in message["parts"] if isinstance(p, dict))

            with st.chat_message(name=role, avatar="🤖" if role == "model" else "🧑‍🚀"):
                st.markdown(display_text)
     
    # --- User Input ---
    user_prompt = st.chat_input("Digite sua mensagem:")
    if user_prompt:
        print(f"Usuário digitou: {user_prompt[:50]}...")

        # Append user message to state immediately for display
        st.session_state.messages.append({"role": "user", "parts": [{"text": user_prompt}]})
        st.rerun() # Rerun to show user message instantly


def DashboardONS():
    
    st.title("📄 Dashboard ONS")

    # Sidebar configuration
    uploaded_file = st.sidebar.file_uploader("Escolha um arquivo PDF", type="pdf")

    if uploaded_file:
        # Salva o arquivo temporariamente
        temp_pdf_path = os.path.join(os.getcwd(), "temp_uploaded_file.pdf")
        with open(temp_pdf_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        controller = PDFController(temp_pdf_path)

        # --- Análise e Visualização Automática na Sidebar ---
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

            # Renderiza todas as páginas
            if num_pages > 0:
                st.subheader("Visualização do PDF")
                with st.spinner("Renderizando páginas..."):
                    try:
                        images = convert_from_path(temp_pdf_path)
                        for i, image in enumerate(images):
                            st.image(image, caption=f"Página {i + 1}", use_column_width=True)
                    except Exception as e:
                        st.error(f"Erro ao renderizar o PDF: {e}\n\nCertifique-se de que o Poppler está instalado e no PATH do sistema.")

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
            tab_extract_text(controller, pages)

        with tab3:
            tab_extract_text_ocr(controller)

        with tab4:
            tab_extract_tables(controller, pages)

        with tab5:
            GOOGLE_API_KEY = "AIzaSyBeoQUgDGxOO-uU075SUrAfGklnimpdO2M"

            assistente = AssistenteGenAI(api_key=GOOGLE_API_KEY)

            if not assistente.model: # Check if model loaded successfully
                st.error("🔴 Modelo de IA não pôde ser carregado. A aplicação não pode continuar.")
                st.stop()

            Chatbot(assistente)


            

DashboardONS()