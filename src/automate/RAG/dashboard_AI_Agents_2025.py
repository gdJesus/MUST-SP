# Referencias das bibliotecas usadas:

# https://streamlit.io/

# https://dspy.ai/#__tabbed_1_4

# https://hub.asimov.academy/blog/agno-agente-de-ia/ 

# https://ai.pydantic.dev/models/google/#api-key-generative-language-api

# https://github.com/tvst/htbuilder

# https://github.com/agno-agi/agno/issues/2401


# https://saptak.in/writing/2025/04/25/building-ai-applications-with-dspy-and-gemini-flash

"""
Streamlit & HTBuilder: Para a interface gráfica interativa e elegante.
LangGraph: Para orquestrar o fluxo de trabalho complexo da sua equipe de agentes (Pesquisa -> Redação -> Consolidação). É a ferramenta perfeita para isso.
DSPy: Para definir o "cérebro" de cada agente de forma clara e estruturada (suas Signatures), garantindo que o LLM entenda exatamente o que precisa fazer.
Agno: Será mantido nas abas de "Extração" e "Pesquisa", onde sua capacidade de interagir com arquivos e usar ferramentas como o DuckDuckGo é demonstrada.
PydanticAI: Continuará na aba "Estrutura", mostrando sua força na extração de dados para um esquema (schema) definido.
Google GenAI & PyPDF2: Como a base para a comunicação com o modelo e o processamento de documentos em todas as abas.
---
"""
# Comando de instalação com todas as bibliotecas necessárias:
# pip install streamlit dspy-ai google-generativeai langgraph PyPDF2 requests  pydantic "pydantic-ai-slim[google]" agno duckduckgo-search htbuilder

import streamlit as st
import google.generativeai as genai
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Any
import operator
from PyPDF2 import PdfReader
import dspy
import tempfile
from pathlib import Path
from pydantic import BaseModel, Field
from google.genai.types import HarmBlockThreshold, HarmCategory
import textwrap
from concurrent.futures import ThreadPoolExecutor
import os
from dotenv import load_dotenv


# --- Importação do HTBuilder, conforme solicitado ---
from htbuilder import div, styles
from htbuilder.units import rem

# --- Importações condicionais de Bibliotecas de IA ---
try:
    from pydantic_ai import PydanticAI
    from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
    PYDANTIC_AI_INSTALLED = True
except ImportError:
    PYDANTIC_AI_INSTALLED = False

try:
    from agno.agent import Agent as AgnoExecutor
    from agno.models.google import Gemini as AgnoGemini
    from agno.media import File as AgnoFile
    from agno.tools.duckduckgo import DuckDuckGoTools
    from agno.memory import BufferMemory
    AGNO_INSTALLED = True
except ImportError:
    AGNO_INSTALLED = False

# --- Definições de Estrutura para a Equipe de Agentes (Aba 1) ---
load_dotenv()


# Example signature for a question-answering task
class QuestionAnswer(dspy.Signature):
    """Answer questions with short factoid answers."""
    question = dspy.InputField()
    answer = dspy.OutputField(desc="often between 1 and 50 words")

# Example module that uses a signature
class SimpleQA(dspy.Module):
    def __init__(self):
        super().__init__()
        self.qa_predictor = dspy.Predict(QuestionAnswer)

    def forward(self, question):
        return self.qa_predictor(question=question)

#TODO ISSO DENTRO DO DASHBOARD
# Example optimizer usage
# optimizer = dspy.MIPROv2(metric=answer_accuracy)
# optimized_program = optimizer.compile(
#     program=my_program,
#     trainset=examples[:80],
#     valset=examples[80:100]
# )

# O estado compartilhado que flui através do nosso grafo de agentes
class CrewState(TypedDict):
    task: str
    research_result: str
    draft_result: str
    final_result: Annotated[list[str], operator.add]

# Assinaturas DSPy para definir a "habilidade" de cada agente
class ResearchSignature(dspy.Signature):
    """Pesquisa de forma abrangente sobre um tópico, focando em fontes confiáveis e recentes. Retorna um resumo e uma lista de links."""
    task = dspy.InputField(desc="A tarefa detalhada para pesquisa.")
    summary = dspy.OutputField(desc="Um resumo estruturado das descobertas, com os pontos chave.")
    sources = dspy.OutputField(desc="Uma lista Python de strings, onde cada string é um URL de fonte confiável.")

class DraftSignature(dspy.Signature):
    """Com base em um relatório de pesquisa, escreve um artigo didático em formato Markdown, com tom encorajador e motivador."""
    task = dspy.InputField(desc="O objetivo geral do artigo a ser escrito.")
    research_report = dspy.InputField(desc="O resumo e as fontes fornecidas pelo agente pesquisador.")
    draft = dspy.OutputField(desc="O rascunho completo do artigo em Markdown, seguindo uma estrutura lógica (Introdução, Desenvolvimento, Conclusão).")

class CoordinationSignature(dspy.Signature):
    """Analisa o relatório de pesquisa e o rascunho para produzir um guia final coeso, integrando as fontes de forma fluida no texto."""
    task = dspy.InputField(desc="A meta final do guia a ser entregue.")
    research_report = dspy.InputField(desc="O relatório completo do pesquisador.")
    draft_article = dspy.InputField(desc="O rascunho do artigo escrito pelo redator.")
    final_answer = dspy.OutputField(desc="O guia final e polido em Markdown, em português do Brasil, pronto para publicação.")

# Classe conceitual do Agente para a nossa equipe
class Agent(BaseModel):
    role: str
    goal: str
    dspy_module: Any
    def execute(self, **kwargs):
        st.write(f"▶️ Executando Agente: **{self.role}**...")
        return self.dspy_module(**kwargs)

class RAGSignature(dspy.Signature):
    """Answer questions with short fact-based sentences."""
    context = dspy.InputField(desc="may contain relevant facts")
    question = dspy.InputField()
    response = dspy.OutputField(desc="often between 1 and 5 sentences")

# --- Classe Principal da Aplicação ---
class DashboardAgents:
    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.model_name = "gemini-2.5-flash"
        st.set_page_config(page_title="Painel de Agentes de IA (POO)", page_icon="🚀", layout="wide")
        self.executor = ThreadPoolExecutor(max_workers=5)

    def _initialize_ai_modules(self):
        """Inicializa todos os módulos de IA necessários para todas as abas."""
        try:

            # Configuração do Genai - Google Generative AI
            genai.configure(api_key=self.google_api_key)

            # Confiuração do DSPy
            LLM = dspy.LM(f"gemini/{self.model_name}", api_key=self.google_api_key)
            dspy.configure(lm=LLM)


            # --- Inicialização para a Aba de Equipe de Agentes (Aba 1) ---
            st.session_state.buscador = Agent(role="Pesquisador", goal="Encontrar e resumir informações.", dspy_module=dspy.Predict(ResearchSignature))
            st.session_state.redator = Agent(role="Redator", goal="Criar um rascunho coeso.", dspy_module=dspy.Predict(DraftSignature))
            st.session_state.chefe = Agent(role="Coordenador de Conteúdo", goal="Consolidar e finalizar o guia.", dspy_module=dspy.Predict(CoordinationSignature))
            st.session_state.agent_graph = self._build_crew_graph()

            # --- Inicializações para as outras abas (mantidas do seu código original) ---
            st.session_state.agente_rag = dspy.ChainOfThought(RAGSignature)
            st.session_state.genai_model = genai.GenerativeModel(self.model_name)

            if PYDANTIC_AI_INSTALLED:
                settings = GoogleModelSettings(temperature=0.2, max_tokens=1024)
                st.session_state.pydantic_ai_llm = GoogleModel(api_key=self.google_api_key, model_name=self.model_name, settings=settings)

            st.session_state.modules_initialized = True
            return True
        except Exception as e:
            st.error(f"Erro ao inicializar os modelos de IA: {e}")
            st.session_state.modules_initialized = False
            return False

    def _build_crew_graph(self):
        """Constrói o fluxo de trabalho (grafo) para a equipe de agentes."""
        workflow = StateGraph(CrewState)
        def run_pesquisador(state):
            res = st.session_state.buscador.execute(task=state['task'])
            return {"research_result": f"Resumo: {res.summary}\nFontes: {res.sources}"}
        def run_redator(state):
            res = st.session_state.redator.execute(task=state['task'], research_report=state['research_result'])
            return {"draft_result": res.draft}
        def run_coordenador(state):
            res = st.session_state.chefe.execute(task=state['task'], research_report=state['research_result'], draft_article=state['draft_result'])
            return {"final_result": [res.final_answer]}

        workflow.add_node("pesquisador", run_pesquisador)
        workflow.add_node("redator", run_redator)
        workflow.add_node("coordenador", run_coordenador)
        workflow.set_entry_point("pesquisador")
        workflow.add_edge("pesquisador", "redator")
        workflow.add_edge("redator", "coordenador")
        workflow.add_edge("coordenador", END)
        return workflow.compile()

    def _render_sidebar(self):
        with st.sidebar:
            st.header("🛠️ Configurações Globais")
            api_key_input = st.text_input("Digite sua Google API Key", type="password", value=self.google_api_key)
            if api_key_input and api_key_input != self.google_api_key:
                self.google_api_key = api_key_input
                st.session_state.modules_initialized = False
                st.rerun()

            st.markdown(f"<small>Modelo em uso: `{self.model_name}`</small>", unsafe_allow_html=True)
            st.markdown("---")
            st.header("📄 Documento de Contexto")
            pdf_doc = st.file_uploader("Envie um PDF para usar nas outras abas", accept_multiple_files=False)
            if pdf_doc and st.button("Processar Documento"):
                with st.spinner("Processando..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        st.session_state.pdf_temp_path = tmp.name
                        tmp.write(pdf_doc.getbuffer())
                    st.session_state.pdf_text = "".join(p.extract_text() or "" for p in PdfReader(st.session_state.pdf_temp_path).pages)
                    st.success("Documento pronto para uso!")

    # --- ABA 1: EQUIPE DE AGENTES (NOSSA NOVA IMPLEMENTAÇÃO) ---
    def _render_agents_tab(self):
        st.header("🤖 Equipe de Agentes Autônomos (LangGraph + DSPy)")
        st.markdown("Esta aba demonstra uma equipe de três agentes (Pesquisador, Redator, Coordenador) trabalhando juntos. Forneça uma tarefa detalhada e eles colaborarão para produzir um resultado final.")

        agent_prompt = st.text_area(
            "Qual é a tarefa para a equipe de agentes?",
            height=150,
            key="agent_prompt",
            placeholder="Ex: Crie um guia para iniciantes sobre como usar a biblioteca Streamlit em Python, explicando o que é, como instalar, e mostrando um exemplo de código de um app simples."
        )

        if st.button("Executar Equipe", key="run_agents") and agent_prompt:
            with st.spinner("A equipe de agentes está trabalhando..."):
                progress_container = st.container(border=True)
                with progress_container:
                    st.subheader("Diário de Bordo da Equipe:")
                    inputs = {"task": agent_prompt}
                    final_state = st.session_state.agent_graph.invoke(inputs)

            st.success("Tarefa concluída pela equipe!")
            st.subheader("Resultado Final (Entregue pelo Coordenador):")
            final_answer = final_state.get('final_result', ["Erro ao gerar resposta."])[-1]
            st.markdown(final_answer)

            with st.expander("Ver trabalho dos agentes individuais"):
                st.markdown("**Relatório do Pesquisador:**")
                st.text_area("Pesquisa", final_state.get('research_result', "N/A"), height=200, disabled=True)
                st.markdown("**Rascunho do Redator:**")
                st.text_area("Rascunho", final_state.get('draft_result', "N/A"), height=200, disabled=True)

    # --- DEMAIS ABAS (Mantidas como no seu código original) ---

    def _render_rag_tab(self):
        st.header("Pergunte ao seu Documento (RAG com DSPy)")
        if "pdf_text" not in st.session_state: st.info("👈 Envie e processe um PDF na barra lateral.")
        else:
            rag_question = st.text_input("Qual sua pergunta sobre o documento?", key="rag_question")
            if st.button("Encontrar Resposta", key="run_rag") and rag_question:
                with st.spinner("O agente RAG está lendo e pensando..."):
                    response = st.session_state.agente_rag(context=st.session_state.pdf_text, question=rag_question)
                    st.success("Resposta encontrada!"); st.subheader("Resposta:"); st.markdown(response.response)
                    if hasattr(response, 'reasoning'):
                        with st.expander("Ver Raciocínio"): st.markdown(f"```\n{response.reasoning}\n```")

    def _render_extract_tab(self):
        st.header("Extração Direta de Informação (Agno)")
        if not AGNO_INSTALLED: st.warning("Execute `pip install agno` para usar esta aba.")
        elif "pdf_temp_path" not in st.session_state: st.info("👈 Envie e processe um PDF na barra lateral.")
        else:
            extract_prompt = st.text_input("O que você quer extrair?", key="extract_prompt", placeholder="Ex: o nome do autor e o ano")
            if st.button("Extrair Informação", key="run_extract") and extract_prompt:
                with st.spinner("O agente Agno está escaneando o arquivo..."):
                    agno_agent = AgnoExecutor(model=AgnoGemini(id=self.model_name, api_key=self.google_api_key), markdown=True)
                    response = agno_agent.get_response(f"Do arquivo, {extract_prompt}. Retorne só a info.", files=[AgnoFile(filepath=Path(st.session_state.pdf_temp_path))])
                    st.success("Informação extraída!"); st.markdown(response.text())

    def _render_pydantic_ai_tab(self):
        st.header("Extração Estruturada com PydanticAI")
        if not PYDANTIC_AI_INSTALLED: st.warning("Execute `pip install pydantic-ai-slim[google]` para usar esta aba.")
        else:
            class Pessoa(BaseModel):
                nome: str = Field(description="O nome completo da pessoa")
                idade: int = Field(description="A idade da pessoa")
            p_prompt = st.text_input("Frase para extrair", key="p_prompt", placeholder="Ex: João Silva tem 30 anos.")
            if st.button("Extrair com PydanticAI", key="run_p_ai") and p_prompt:
                with st.spinner("PydanticAI processando..."):
                    ai = PydanticAI(llm=st.session_state.pydantic_ai_llm)
                    pessoa = ai(output_model=Pessoa, prompt=p_prompt)
                    st.success("Dados extraídos!"); st.json(pessoa.model_dump_json(indent=2))

    def _render_research_agent_tab(self):
        st.header("Agente de Pesquisa com Ferramentas e Memória (Agno)")
        if not AGNO_INSTALLED: st.warning("Execute `pip install agno duckduckgo-search` para usar esta aba.")
        else:
            if 'agno_research_agent' not in st.session_state:
                st.session_state.agno_research_agent = AgnoExecutor(name="Info Agent", model=AgnoGemini(id=self.model_name, api_key=self.google_api_key), tools=[DuckDuckGoTools()], memory=BufferMemory(max_tokens=1024), markdown=True)
            if "agno_messages" not in st.session_state: st.session_state.agno_messages = []
            for message in st.session_state.agno_messages:
                with st.chat_message(message["role"]): st.markdown(message["content"])
            if prompt := st.chat_input("Pergunte algo para o agente...", key="research_chat_input"):
                st.session_state.agno_messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)
                with st.chat_message("assistant"):
                    with st.spinner("Agente de pesquisa está pensando..."):
                        response = st.session_state.agno_research_agent.get_response(prompt)
                        st.markdown(response.text()); st.session_state.agno_messages.append({"role": "assistant", "content": response.text()})

    def _chatbot_build_prompt(self, **kwargs):
        prompt = []
        for name, contents in kwargs.items():
            if contents: prompt.append(f"<{name}>\n{contents}\n</{name}>")
        return "\n".join(prompt)

    def _chatbot_get_response(self, prompt):
        return st.session_state.genai_model.generate_content(prompt, stream=True)

    def _chatbot_search_pdf_context(self, query):
        if "pdf_text" in st.session_state and st.session_state.pdf_text: return st.session_state.pdf_text
        return "Nenhum documento PDF foi fornecido como contexto."

    # --- ABA 6: CHATBOT (IMPLEMENTAÇÃO COMPLETA) ---
    def _render_chatbot_tab(self):
        st.html(div(style=styles(font_size=rem(1.5), line_height=1))["💬"])
        st.header("Chatbot Conversacional (GenAI)")

        INSTRUCTIONS = textwrap.dedent("- Você é um assistente de IA prestativo.\n- Use o contexto para basear suas respostas.")
        SUGGESTIONS = {"O que é IA?": "Explique o que é IA.", "Resuma o documento": "Faça um resumo do documento."}

        if "chatbot_messages" not in st.session_state: st.session_state.chatbot_messages = []
        
        for message in st.session_state.chatbot_messages:
            with st.chat_message(message["role"]): st.markdown(message["content"])

        user_message = st.chat_input("Faça uma pergunta...")
        
        if not st.session_state.chatbot_messages:
             pills = st.pills(
                options=list(SUGGESTIONS.keys()), label="Ou escolha uma sugestão:",  key="chatbot_suggestions"
             )
             if pills:
                 user_message = SUGGESTIONS[pills]

        if user_message:
            st.session_state.chatbot_messages.append({"role": "user", "content": user_message})
            with st.chat_message("user"): st.markdown(user_message)

            with st.chat_message("assistant"):
                with st.spinner("Pesquisando e pensando..."):
                    context_future = self.executor.submit(self._chatbot_search_pdf_context, user_message)
                    pdf_context = context_future.result()
                    history_str = "\n".join([f"[{m['role']}]: {m['content']}" for m in st.session_state.chatbot_messages])
                    full_prompt = self._chatbot_build_prompt(instructions=INSTRUCTIONS, document_context=pdf_context, chat_history=history_str, question=user_message)
                
                with st.spinner("Gerando resposta..."):
                    response_stream = self._chatbot_get_response(full_prompt)
                    response = st.write_stream(response_stream)
            
            st.session_state.chatbot_messages.append({"role": "assistant", "content": response})
            st.rerun()

    def run(self):
        st.title("🚀 Painel de Agentes de IA com POO")
        self._render_sidebar()

        if not self.google_api_key:
            st.info("👈 Por favor, adicione sua Google API Key no menu lateral para começar."); st.stop()

        if not st.session_state.get('modules_initialized', False):
            if not self._initialize_ai_modules():
                st.warning("Não foi possível inicializar os módulos de IA. Verifique sua chave API e conexão.")
                

        tab_list = ["🤖 Equipe de Agentes", "🔍 RAG", "📄 Extração", "✨ Estrutura", "🔎 Pesquisa", "💬 Chatbot"]
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(tab_list)
        with tab1: self._render_agents_tab()
        with tab2: self._render_rag_tab()
        with tab3: self._render_extract_tab()
        with tab4: self._render_pydantic_ai_tab()
        with tab5: self._render_research_agent_tab()
        with tab6: self._render_chatbot_tab()

# --- Ponto de Entrada da Aplicação ---
if __name__ == "__main__":
    app = DashboardAgents()
    app.run()