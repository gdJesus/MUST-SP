import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# Carrega a chave da API, pois vamos usar o Gemini para a geração da resposta.
load_dotenv()

class RAGPipelineHibrida:
    """
    Pipeline de RAG Híbrida: usa embeddings locais (open-source) para evitar
    custos e limites de API, e o Gemini (API) para a geração de respostas de alta qualidade.
    """
    def __init__(self, google_api_key: str, source_path: str, index_path: str = None):
        if not google_api_key:
            raise ValueError("A chave da API do Google não foi encontrada para o LLM. Verifique seu arquivo .env")

        self.source_path = Path(source_path)

        if index_path is None:
            base_name = self.source_path.stem if self.source_path.is_file() else self.source_path.name
            index_path = f"{base_name}_faiss_index_hibrido"
        self.index_path = Path(index_path)
        
        # --- MUDANÇA 1: O LLM volta a ser o Gemini via API ---
        from langchain_google_genai import ChatGoogleGenerativeAI
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0, api_key=google_api_key)
        
        # --- MUDANÇA 2: O Embedding continua sendo local e open-source ---
        from langchain_community.embeddings import HuggingFaceEmbeddings
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        print("RAGPipelineHibrida inicializada: LLM (Gemini via API) e Embeddings (Local).")
        
        self.vectorstore = None
        self.retriever = None
        self.document_chain = None

    def _processar_documentos_hibrido(self):
        """Etapa 1: Carrega texto e TABELAS do PDF (sem mudanças aqui)."""
        print("\n--- Etapa 1: Processamento Híbrido (Texto e Tabelas) ---")
        
        from langchain_community.document_loaders import PyMuPDFLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_core.documents import Document
        import camelot

        chunks = []
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        paths_a_processar = [self.source_path]

        for pdf_path in paths_a_processar:
            try:
                print(f"  - Extraindo texto de: {pdf_path.name}")
                loader = PyMuPDFLoader(str(pdf_path))
                chunks.extend(text_splitter.split_documents(loader.load()))
                
                print(f"  - Extraindo tabelas de: {pdf_path.name}")
                tabelas = camelot.read_pdf(str(pdf_path), pages='all', flavor='lattice')
                
                for tabela in tabelas:
                    tabela_markdown = tabela.df.to_markdown(index=False)
                    chunks.append(Document(
                        page_content=f"Tabela extraída:\n{tabela_markdown}",
                        metadata={"source": str(pdf_path), "page": tabela.page, "type": "table"}
                    ))
                print(f"    - Encontradas {len(tabelas)} tabelas.")
            except Exception as e:
                print(f"  - Erro ao processar o arquivo {pdf_path.name}: {e}")

        print(f"\nTotal de chunks (texto + tabelas) criados: {len(chunks)}")
        return chunks

    def _criar_e_salvar_novo_indice(self, chunks: list):
        """Etapa 2: Cria o índice localmente, sem chamadas de API."""
        print("\n--- Etapa 2: Criando índice local (sem chamadas de API) ---")
        from langchain_community.vectorstores import FAISS
        self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
        self.vectorstore.save_local(str(self.index_path))
        print(f"\nÍndice salvo localmente em: '{self.index_path}'")

    def _carregar_indice_local(self):
        """Carrega o índice local."""
        print("\n--- Carregando índice local pré-existente ---")
        from langchain_community.vectorstores import FAISS
        self.vectorstore = FAISS.load_local(
            str(self.index_path), self.embeddings, allow_dangerous_deserialization=True
        )
        print("Índice carregado com sucesso.")

    def _configurar_retriever_e_cadeia(self):
        """Configura o retriever e a cadeia RAG com o LLM Gemini."""
        print("\n--- Configurando Retriever e Cadeia RAG (com Gemini) ---")
        from langchain_core.prompts import ChatPromptTemplate
        from langchain.chains.combine_documents import create_stuff_documents_chain

        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"score_threshold": 0.5, "k": 5}
        )
        prompt_rag = ChatPromptTemplate.from_messages([
            ("system",
             "Você é um assistente especialista em analisar documentos técnicos da ONS. "
             "Responda SOMENTE com base no contexto fornecido."),
            ("human", "Pergunta: {input}\n\nContexto:\n{context}")
        ])
        self.document_chain = create_stuff_documents_chain(self.llm, prompt_rag)
        print("Retriever e Cadeia RAG prontos.")

    def setup(self):
        """Configura a pipeline."""
        if self.index_path.exists():
            self._carregar_indice_local()
        else:
            chunks = self._processar_documentos_hibrido()
            if not chunks:
                print("\n❌ Nenhum documento processado.")
                return
            self._criar_e_salvar_novo_indice(chunks)
        self._configurar_retriever_e_cadeia()
        print("\n✅ Pipeline Híbrida pronta para uso!")

    def perguntar(self, query: str) -> dict:
        """Executa uma pergunta contra a pipeline."""
        if not self.retriever or not self.document_chain:
            return {"resposta": "A pipeline não foi configurada corretamente."}
        docs_relacionados = self.retriever.invoke(query)
        resposta = self.document_chain.invoke({
            "input": query, "context": docs_relacionados
        })
        return {"resposta": resposta}


if __name__ == "__main__":
    logger = Console()
    
    # Carrega a chave da API do arquivo .env
    GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')
    GOOGLE_API_KEY = "AIzaSyBeoQUgDGxOO-uU075SUrAfGklnimpdO2M"

    # Especifique o caminho para o seu arquivo PDF.
    caminho_fonte = r"C:\Users\pedrovictor.veras\OneDrive - Operador Nacional do Sistema Eletrico\Documentos\ESTAGIO_ONS_PVRV_2025\GitHub\Electrical-System-Simulator\ONS_SIMULATOR_SYSTEM\arquivos\CUST-2002-025-41 - SUL SUDESTE_minuta_recon_2025_28_final.pdf"

    logger.print("[bold blue]Inicializando a pipeline de RAG Híbrida...[/bold blue]")
    pipeline = RAGPipelineHibrida(
        google_api_key=GOOGLE_API_KEY,
        source_path=caminho_fonte
    )
    
    pipeline.setup()
    
    if pipeline.document_chain:
        while True:
            logger.print("\n" + "="*50)
            pergunta = input("Faça sua pergunta sobre o PDF (ou digite 'sair'): ")
            if pergunta.lower() == 'sair':
                break
            
            logger.print(f"\n[yellow]Buscando resposta para:[/yellow] '{pergunta}'")
            resultado = pipeline.perguntar(pergunta)
            
            logger.print("\n[bold green]Resposta do Assistente (via Gemini):[/bold green]")
            logger.print(resultado["resposta"])
