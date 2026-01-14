import os
import time
from pathlib import Path
from dotenv import load_dotenv

from rich.console import Console

class Logger:
    """
    Classe para encapsular o console do Rich para logging.
    """
    def __init__(self):
        self.console = Console()

    def log(self, message, *args, **kwargs):
        """Usa o método log do console Rich para exibir mensagens com timestamp."""
        self.console.log(message, *args, **kwargs)
    
    def print(self, message, *args, **kwargs):
        """Usa o método print do console Rich para exibir mensagens sem timestamp."""
        self.console.print(message, *args, **kwargs)


# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class RAGPipeline:
    """
    Pipeline de RAG aprimorada com persistência de índice e extração de tabelas.
    Agora aceita um único arquivo PDF ou um diretório de PDFs.
    """
    def __init__(self, google_api_key: str, source_path: str, index_path: str = None):
        if not google_api_key:
            raise ValueError("A chave da API do Google não foi encontrada. Verifique seu arquivo .env")
        
        self.api_key = google_api_key
        self.source_path = Path(source_path)

        # Se um caminho de índice não for fornecido, cria um nome padrão
        # baseado no nome do arquivo ou diretório de origem. Isso evita
        # que o índice de um PDF seja usado para outro.
        if index_path is None:
            base_name = self.source_path.stem if self.source_path.is_file() else self.source_path.name
            index_path = f"{base_name}_faiss_index"
        self.index_path = Path(index_path)
        
        self.docs = []
        self.vectorstore = None
        self.retriever = None
        self.document_chain = None
        
        from langchain_google_genai import ChatGoogleGenerativeAI
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.0,
            api_key=self.api_key
        )
        print("RAGPipeline inicializada com o modelo Gemini.")

    def _processar_documentos_hibrido(self):
        """
        Etapa 1: Carrega texto e TABELAS de um PDF ou de um diretório de PDFs.
        """
        print("\n--- Etapa 1: Processamento Híbrido (Texto e Tabelas) ---")
        
        from langchain_community.document_loaders import PyMuPDFLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_core.documents import Document
        import camelot

        chunks = []
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

        # Determina a lista de arquivos a serem processados com base na entrada (arquivo ou pasta)
        paths_a_processar = []
        if self.source_path.is_dir():
            paths_a_processar = list(self.source_path.glob("*.pdf"))
            print(f"Processando diretório: {self.source_path}")
        elif self.source_path.is_file() and self.source_path.suffix.lower() == '.pdf':
            paths_a_processar = [self.source_path]
            print(f"Processando arquivo único: {self.source_path}")
        else:
            print(f"[bold red]ERRO: O caminho '{self.source_path}' não é um PDF ou diretório válido.[/bold red]")
            return chunks

        for pdf_path in paths_a_processar:
            try:
                # 1. Extração de TEXTO
                print(f"  - Extraindo texto de: {pdf_path.name}")
                text_loader = PyMuPDFLoader(str(pdf_path))
                docs_texto = text_loader.load()
                chunks.extend(text_splitter.split_documents(docs_texto))
                
                # 2. Extração de TABELAS
                print(f"  - Extraindo tabelas de: {pdf_path.name}")
                tabelas = camelot.read_pdf(str(pdf_path), pages='all', flavor='lattice')
                
                for i, tabela in enumerate(tabelas):
                    tabela_markdown = tabela.df.to_markdown(index=False)
                    chunk_tabela = Document(
                        page_content=f"A seguir uma tabela extraída do documento:\n\n{tabela_markdown}",
                        metadata={
                            "source": str(pdf_path),
                            "page": tabela.page,
                            "type": "table"
                        }
                    )
                    chunks.append(chunk_tabela)
                print(f"    - Encontradas {len(tabelas)} tabelas.")
                
            except Exception as e:
                print(f"  - Erro ao processar o arquivo {pdf_path.name}: {e}")

        print(f"\nTotal de chunks (texto + tabelas) criados: {len(chunks)}")
        return chunks

    def _criar_e_salvar_novo_indice(self, chunks: list):
        """
        Etapa 2: Cria um novo vector store do zero e o salva localmente.
        """
        print("\n--- Etapa 2: Criando e salvando novo índice (isso pode demorar) ---")
        
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        from langchain_community.vectorstores import FAISS
        
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", google_api_key=self.api_key
        )
        
        #! --- CORREÇÃO: Reduz o tamanho do lote para evitar erros de limite de uso (rate limit) ---
        # Um lote menor faz requisições menores à API, respeitando o limite do plano gratuito.
        batch_size = 15
        
        print(f"  - Processando o primeiro lote de {min(batch_size, len(chunks))} chunks...")
        self.vectorstore = FAISS.from_documents(chunks[:batch_size], embeddings)
        
        for i in range(batch_size, len(chunks), batch_size):
            print(f"\n  - Aguardando 61 segundos para respeitar o limite da API...")
            time.sleep(61)
            
            batch = chunks[i:i + batch_size]
            print(f"  - Processando próximo lote de {len(batch)} chunks...")
            self.vectorstore.add_documents(batch)

        self.vectorstore.save_local(str(self.index_path))
        print(f"\nÍndice salvo localmente em: '{self.index_path}'")

    def _carregar_indice_local(self):
        """Carrega um índice FAISS pré-existente do disco."""
        print("\n--- Carregando índice local pré-existente ---")
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        from langchain_community.vectorstores import FAISS

        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", google_api_key=self.api_key
        )
        self.vectorstore = FAISS.load_local(str(self.index_path), embeddings, allow_dangerous_deserialization=True)
        print("Índice carregado com sucesso.")

    def _configurar_retriever_e_cadeia(self):
        """Configura o retriever e a cadeia RAG após o vector store estar pronto."""
        print("\n--- Configurando Retriever e Cadeia RAG ---")
        from langchain_core.prompts import ChatPromptTemplate
        from langchain.chains.combine_documents import create_stuff_documents_chain

        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"score_threshold": 0.5, "k": 5}
        )

        prompt_rag = ChatPromptTemplate.from_messages([
            ("system",
             "Você é um assistente especialista em analisar documentos técnicos e tabelas da ONS. "
             "Responda SOMENTE com base no contexto fornecido, que pode incluir texto e tabelas em formato Markdown. "
             "Se a resposta estiver em uma tabela, apresente-a de forma clara. "
             "Se não souber a resposta, diga 'Não sei'."),
            ("human", "Pergunta: {input}\n\nContexto:\n{context}")
        ])
        
        self.document_chain = create_stuff_documents_chain(self.llm, prompt_rag)
        print("Retriever e Cadeia RAG prontos.")

    def setup(self):
        """
        Executa a configuração da pipeline: carrega ou cria o índice e monta a cadeia.
        """
        if self.index_path.exists():
            self._carregar_indice_local()
        else:
            chunks = self._processar_documentos_hibrido()
            if not chunks:
                print("\n❌ Nenhum documento processado. A pipeline não pode continuar.")
                return
            self._criar_e_salvar_novo_indice(chunks)
        
        self._configurar_retriever_e_cadeia()
        print("\n✅ Pipeline de RAG pronta para uso!")

    def perguntar(self, query: str) -> dict:
        """Executa uma pergunta contra a pipeline de RAG."""
        if not self.retriever or not self.document_chain:
            return {"resposta": "A pipeline não foi configurada corretamente. Execute o método setup().", "fontes": []}
            
        docs_relacionados = self.retriever.invoke(query)
        
        resposta = self.document_chain.invoke({
            "input": query,
            "context": docs_relacionados
        })
        
        fontes = self._formatar_citacoes(docs_relacionados, query)
        
        return {"resposta": resposta, "fontes": fontes}

    def _formatar_citacoes(self, docs_rel: list, query: str) -> list:
        """Formata as fontes dos documentos para exibição."""
        import re
        cites, seen = [], set()
        for d in docs_rel:
            src = Path(d.metadata.get("source","")).name
            page = d.metadata.get("page", 0)
            if d.metadata.get("type") != "table":
                page += 1
            key = (src, page)
            if key in seen:
                continue
            seen.add(key)
            cites.append({"documento": src, "pagina": page})
        return cites[:3]


# --- Exemplo de uso ---
if __name__ == "__main__":
    
    logger = Logger()

    # Carrega a chave da API do arquivo .env
    GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')
    GOOGLE_API_KEY = "AIzaSyBd7QkbQz3u9JDW2BT4zm3-hfNdEvb-7TI"

    # Especifique o caminho para o seu arquivo PDF
    # O 'r' antes da string é importante no Windows para evitar erros com barras invertidas
    caminho_fonte = r"C:\Users\pedrovictor.veras\OneDrive - Operador Nacional do Sistema Eletrico\Documentos\ESTAGIO_ONS_PVRV_2025\GitHub\Electrical-System-Simulator\ONS_SIMULATOR_SYSTEM\arquivos\CUST-2002-025-41 - SUL SUDESTE_minuta_recon_2025_28_final.pdf"

    logger.print("[bold blue]Inicializando a pipeline de RAG...[/bold blue]")
    pipeline = RAGPipeline(
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
            
            logger.print("\n[bold green]Resposta do Assistente:[/bold green]")
            logger.print(resultado["resposta"])
            
            logger.print("\n[bold]Fontes Consultadas:[/bold]")
            if resultado["fontes"]:
                for fonte in resultado["fontes"]:
                    logger.print(f"  - Documento: [cyan]{fonte['documento']}[/cyan], Página: [cyan]{fonte['pagina']}[/cyan]")
            else:
                logger.print("Nenhuma fonte específica foi consultada.")

