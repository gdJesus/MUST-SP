import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
from typing import List, Dict
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import tempfile
from io import BytesIO

# --- 1. CONFIGURAÇÕES INICIAIS E DE ESTILO ---

load_dotenv()

# Dicionário de configuração para os roles. Agora a IA pode ter múltiplos roles.
ROLES_CONFIG = {
    "default_roles": ["assistente", "analista_de_documentos"],
    "roles": [
        {
            "nome": "assistente",
            "prompt": "Você é um assistente de IA prestativo e direto. Responda às perguntas do usuário de forma clara e concisa."
        },
        {
            "nome": "analista_de_documentos",
            "prompt": "Sua principal função é analisar o conteúdo de documentos. Baseie suas respostas estritamente no texto fornecido. Se a informação não estiver lá, afirme que não a encontrou no contexto."
        },
        {
            "nome": "tutor_python",
            "prompt": "Aja como um tutor de Python. Explique conceitos de forma didática, forneça exemplos de código e ajude a depurar erros."
        },
        {
            "nome": "escritor_criativo",
            "prompt": "Você é um escritor criativo. Ajude o usuário com ideias, continue histórias e sugira melhorias em seus textos, adotando um tom inspirador."
        }
    ]
}

# st.set_page_config(
#     page_title="Gemini Pro com RAG",
#     page_icon="🤖",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

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


# --- 2. CLASSES DE CONTROLE (LÓGICA) ---

class UseStateController:
    def __init__(self):
        self.defaults = {
            "chat_messages": [],
            "system_instructions": [],
            "pdf_context": [],
            "gemini_model": None,
            "selected_roles": ROLES_CONFIG["default_roles"],
            "active_pdf_preview": None,
            "active_pdf_bytes": None,
            "active_pdf_name": None,
        }
        self.initialize_state()

    def initialize_state(self):
        for key, value in self.defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def get(self, key): return st.session_state.get(key)
    def set(self, key, value): st.session_state[key] = value
    def append_to(self, key, item):
        if key in st.session_state and isinstance(st.session_state[key], list):
            st.session_state[key].append(item)

    def clear_all_data(self):
        for key in ["chat_messages", "system_instructions", "pdf_context", "active_pdf_preview", "active_pdf_bytes", "active_pdf_name"]:
            st.session_state[key] = self.defaults.get(key, [])
        st.success("Todos os dados (chat, instruções, PDFs) foram limpos!")

class PDFController:
    def __init__(self, state_controller: UseStateController):
        self.state = state_controller

    @staticmethod
    def parse_page_string(page_str: str, max_pages: int) -> list[int]:
        if not page_str or page_str.lower().strip() == 'all':
            return list(range(max_pages))
        pages = set()
        parts = page_str.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                try: start, end = map(int, part.split('-')); pages.update(range(start - 1, end))
                except ValueError: pass
            else:
                try: pages.add(int(part) - 1)
                except ValueError: pass
        return sorted([p for p in pages if 0 <= p < max_pages])

    def extract_text_from_pages(self, pdf_file_bytes: bytes, pages_to_process: List[int]) -> str:
        try:
            reader = PdfReader(BytesIO(pdf_file_bytes))
            text_content = [f"--- CONTEÚDO DA PÁGINA {i + 1} ---\n{reader.pages[i].extract_text() or ''}\n" for i in pages_to_process]
            return "\n".join(text_content)
        except Exception as e:
            st.error(f"Erro ao extrair texto: {e}")
            return ""

    def generate_and_store_preview(self):
        pdf_bytes = self.state.get("active_pdf_bytes")
        if pdf_bytes:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(pdf_bytes)
                images = convert_from_path(tmp.name, first_page=1, last_page=5)
                os.unlink(tmp.name)
                self.state.set("active_pdf_preview", images)
            except Exception:
                self.state.set("active_pdf_preview", None)
                st.warning("Não foi possível gerar a pré-visualização. Verifique se o Poppler está instalado corretamente no seu sistema.")
    
    def add_pdf_context_to_session(self, file_name: str, extracted_text: str):
        if extracted_text.strip():
            self.state.append_to("pdf_context", {"name": file_name, "content": extracted_text})
            st.success(f"Texto do documento '{file_name}' adicionado ao contexto da IA!")
        else:
            st.warning("Nenhum texto foi extraído das páginas selecionadas.")

# --- 3. FUNÇÕES CORE DO CHATBOT ---

def configure_gemini_model():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key: st.error("⚠️ API key do Google não encontrada!"); st.stop()
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-1.5-pro-latest")
    except Exception as e: st.error(f"Falha ao configurar o modelo Gemini: {e}"); st.stop()

def build_gemini_history(state: UseStateController) -> List[Dict]:
    history = []
    
    # Adiciona os MÚLTIPLOS roles selecionados
    selected_role_names = state.get("selected_roles")
    role_prompts = [role["prompt"] for role in ROLES_CONFIG["roles"] if role["nome"] in selected_role_names]
    full_role_prompt = "\n".join(role_prompts)
    history.append({"role": "user", "parts": [f"INSTRUÇÕES DE SISTEMA (SUAS PERSONALIDADES):\n{full_role_prompt}"]})

    # Adiciona instruções manuais
    for inst in state.get("system_instructions"):
        history.append({"role": "user", "parts": [f"INSTRUÇÃO ADICIONAL DO USUÁRIO: {inst['content']}"]})
        
    # Adiciona contexto dos PDFs
    pdf_contexts = state.get("pdf_context")
    if pdf_contexts:
        full_pdf_text = "\n\n".join([f"DOCUMENTO: {ctx['name']}\n{ctx['content']}" for ctx in pdf_contexts])
        history.append({"role": "user", "parts": [f"--- CONTEXTO DOS DOCUMENTOS ---\n{full_pdf_text}\n--- FIM DO CONTEXTO ---"]})

    # Adiciona histórico da conversa
    for msg in state.get("chat_messages"):
        role = "model" if msg["role"] == "assistant" else "user"
        history.append({"role": role, "parts": [msg["content"]]})
        
    return history

def get_gemini_response(model: genai.GenerativeModel, state: UseStateController, user_message: str) -> str:
    try:
        chat_history = build_gemini_history(state)
        chat = model.start_chat(history=chat_history)
        response = chat.send_message(user_message)
        return response.text
    except Exception as e:
        return f"❌ Erro ao comunicar com a IA: {e}"

# --- 4. COMPONENTES DA INTERFACE (VIEWS) ---

def Header():
    st.markdown("""
    <div class="main-header">
        <h1>🤖 Chat IA com Gemini Pro e RAG</h1>
        <p>Combine personalidades, faça upload de PDFs e converse com seus documentos</p>
    </div>
    """, unsafe_allow_html=True)

def MenuLateral(state: UseStateController, pdf_controller: PDFController):
    with st.sidebar:
        st.markdown("## ⚙️ Painel de Controle")

        with st.expander("👤 Personalidades da IA", expanded=True):
            roles_disponiveis = [role["nome"] for role in ROLES_CONFIG["roles"]]
            selected_roles = st.multiselect(
                "Combine as personalidades do assistente:",
                options=roles_disponiveis,
                default=state.get("selected_roles"),
                key="role_selector"
            )
            state.set("selected_roles", selected_roles)

        with st.expander("🛠️ Instruções Adicionais"):
            system_instruction = st.text_area("Adicionar instrução para a IA:", key="system_input")
            if st.button("➕ Adicionar Instrução"):
                if system_instruction: state.append_to("system_instructions", {"content": system_instruction}); st.rerun()
            if state.get("system_instructions"):
                st.markdown("**Instruções Ativas:**")
                for inst in state.get("system_instructions"):
                    st.markdown(f'<div class="system-message">📋 {inst["content"][:50]}...</div>', unsafe_allow_html=True)

        with st.expander("📄 Gerenciador de Documentos (RAG)", expanded=True):
            uploaded_file = st.file_uploader("Carregue um arquivo PDF:", type="pdf", key="pdf_uploader")
            
            if uploaded_file and uploaded_file.getvalue() != state.get("active_pdf_bytes"):
                with st.spinner("Gerando pré-visualização..."):
                    state.set("active_pdf_bytes", uploaded_file.getvalue())
                    state.set("active_pdf_name", uploaded_file.name)
                    pdf_controller.generate_and_store_preview()

            if state.get("active_pdf_bytes"):
                st.markdown(f"**Arquivo ativo: `{state.get('active_pdf_name')}`**")
                if state.get("active_pdf_preview"):
                    st.image(state.get("active_pdf_preview"), use_column_width=True, caption="Pré-visualização das primeiras páginas")
                
                num_pages = len(PdfReader(BytesIO(state.get("active_pdf_bytes"))).pages)
                page_selection = st.text_input(f"Páginas para processar (1-{num_pages}, ex: 1-3,5,all):", key="page_selector")
                
                if st.button(f"Processar Páginas"):
                    with st.spinner("Extraindo texto..."):
                        pages_to_process = pdf_controller.parse_page_string(page_selection, num_pages)
                        extracted_text = pdf_controller.extract_text_from_pages(state.get("active_pdf_bytes"), pages_to_process)
                        pdf_controller.add_pdf_context_to_session(state.get('active_pdf_name'), extracted_text)
                        st.rerun()

            if state.get("pdf_context"):
                st.markdown("**Documentos no Contexto:**")
                for i, doc in enumerate(state.get("pdf_context")):
                    if st.button(f"🗑️ Remover '{doc['name']}'", key=f"remove_pdf_{i}"):
                        state.get("pdf_context").pop(i); st.rerun()

        with st.expander("⚙️ Controles do Chat"):
            if st.button("🧹 Limpar Tudo"):
                state.clear_all_data(); st.rerun()

def ChatbotView(state: UseStateController, model: genai.GenerativeModel):
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Ordem cronológica normal (de cima para baixo)
    for message in state.get("chat_messages"):
        with st.chat_message(message["role"]):
            st.markdown(message['content'])
            
    st.markdown('</div>', unsafe_allow_html=True)
    
    user_input = st.chat_input("Digite sua mensagem aqui...")
    if user_input:
        state.append_to("chat_messages", {"role": "user", "content": user_input})
        with st.spinner("🤔 Pensando..."):
            ai_response = get_gemini_response(model, state, user_input)
        state.append_to("chat_messages", {"role": "assistant", "content": ai_response})
        st.rerun()

def Footer():
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #666;'><p>🚀 Desenvolvido com Streamlit + Google Gemini</p></div>", unsafe_allow_html=True)

# --- 5. FUNÇÃO PRINCIPAL DA APLICAÇÃO ---

def ChatbotGeminiApp():
    state_controller = UseStateController()
    pdf_controller = PDFController(state_controller)
    
    if state_controller.get("gemini_model") is None:
        state_controller.set("gemini_model", configure_gemini_model())
    
    Header()
    MenuLateral(state_controller, pdf_controller)
    ChatbotView(state_controller, state_controller.get("gemini_model"))
    Footer()

if __name__ == "__main__":
    ChatbotGeminiApp()