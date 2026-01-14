import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env no início.
#load_dotenv()

#! https://github.com/google-gemini/cookbook/tree/8f9eb8fed4106da996020cd895ac0e2bf009ff0c/examples

class RAGPipeline:
    """
    Uma classe para encapsular o fluxo de trabalho de Retrieval-Augmented Generation (RAG).
    Carrega, processa, e permite fazer perguntas a um conjunto de documentos PDF.
    """
    def __init__(self, google_api_key: str, pdf_directory: str = "documentos_pdf"):
        """
        Inicializa a pipeline com a chave da API e o diretório dos PDFs.

        Args:
            google_api_key (str): A chave da API do Google para o Gemini.
            pdf_directory (str): O nome da pasta onde os arquivos PDF estão localizados.
        """
        if not google_api_key:
            raise ValueError("A chave da API do Google não foi encontrada. Verifique seu arquivo .env")
        
        self.api_key = google_api_key
        self.pdf_directory = Path(pdf_directory)
        self.docs = []
        self.vectorstore = None
        self.retriever = None
        self.document_chain = None
        
        # A importação do LLM é feita aqui, pois ele é central para a classe.
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", # Usando o flash para velocidade e custo-benefício
            temperature=0.0,
            api_key=self.api_key
        )
        print("RAGPipeline inicializada com o modelo Gemini.")

    def _carregar_e_dividir_documentos(self):
        """Etapa 1: Carrega os PDFs e os divide em pedaços (chunks)."""
        print("\n--- Etapa 1: Carregando e dividindo documentos ---")
        
        # Ferramenta para carregar o conteúdo de arquivos PDF.
        from langchain_community.document_loaders import PyMuPDFLoader
        
        if not self.pdf_directory.exists() or not any(self.pdf_directory.glob("*.pdf")):
            print(f"Diretório '{self.pdf_directory}' não encontrado ou está vazio. Crie-o e adicione seus PDFs.")
            return

        for n in self.pdf_directory.glob("*.pdf"):
            try:
                loader = PyMuPDFLoader(str(n))
                self.docs.extend(loader.load())
                print(f"  - Carregado com sucesso: {n.name}")
            except Exception as e:
                print(f"  - Erro ao carregar {n.name}: {e}")
        
        if not self.docs:
            print("Nenhum documento foi carregado. A pipeline não pode continuar.")
            return

        print(f"\nTotal de páginas carregadas: {len(self.docs)}")
        
        # Ferramenta para quebrar os textos em pedaços menores e gerenciáveis.
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_documents(self.docs)
        print(f"Documentos divididos em {len(chunks)} chunks.")
        
        return chunks

    def _criar_vectorstore_e_retriever(self, chunks: list):
        """Etapa 2: Cria os embeddings e armazena em um vector store (FAISS)."""
        print("\n--- Etapa 2: Criando embeddings e vector store ---")
        
        # Ferramenta para converter os chunks de texto em vetores numéricos (embeddings).
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        # Modelo de embedding
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=self.api_key
        )

        # Ferramenta para criar um banco de dados em memória para buscar vetores similares.
        from langchain_community.vectorstores import FAISS
        
        #! --- CORREÇÃO: PROCESSAMENTO EM LOTES PARA EVITAR RATE LIMIT ---
        batch_size = 100  # Número de chunks a processar por vez
        
        print(f"  - Processando o primeiro lote de {min(batch_size, len(chunks))} chunks...")
        self.vectorstore = FAISS.from_documents(chunks[:batch_size], embeddings)
        
        # Processa o restante dos chunks em lotes, com uma pausa entre eles
        for i in range(batch_size, len(chunks), batch_size):

            print(f"\n  - Aguardando 62 segundos para respeitar o limite da API...")
            time.sleep(62)  # Pausa para o limite de RPM resetar
            
            batch = chunks[i:i + batch_size]
            print(f"  - Processando próximo lote de {len(batch)} chunks (iniciando no índice {i})...")
            
            self.vectorstore.add_documents(batch)

        # O retriever é o componente que busca os chunks relevantes para uma pergunta.
        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"score_threshold": 0.5, "k": 5} # Ajustado para melhor relevância
        )
        print("\nVector store e retriever criados com sucesso.")

    def _criar_cadeia_rag(self):
        """Etapa 3: Monta a cadeia (chain) que conecta o prompt, o LLM e os documentos."""
        print("\n--- Etapa 3: Criando a cadeia RAG ---")
        
        # Ferramenta para criar um template de prompt estruturado.
        from langchain_core.prompts import ChatPromptTemplate
        prompt_rag = ChatPromptTemplate.from_messages([
            ("system",
             "Você é um Assistente de estudos elétricos (Engenharia e Modelagem) da empresa ONS. "
             "Responda SOMENTE com base no contexto fornecido. "
             "Se não houver base suficiente, responda apenas 'Não sei'."),
            ("human", "Pergunta: {input}\n\nContexto:\n{context}")
        ])

        # Ferramenta para "rechear" o prompt com os documentos encontrados pelo retriever.
        from langchain.chains.combine_documents import create_stuff_documents_chain
        self.document_chain = create_stuff_documents_chain(self.llm, prompt_rag)
        print("Cadeia RAG criada com sucesso.")

    def setup(self):
        """
        Executa todas as etapas de configuração da pipeline: carregar, dividir e criar a cadeia.
        """
        chunks = self._carregar_e_dividir_documentos()
        if chunks:
            self._criar_vectorstore_e_retriever(chunks)
            self._criar_cadeia_rag()
            print("\n✅ Pipeline de RAG pronta para uso!")
        else:
            print("\n❌ Falha na configuração da pipeline devido à falta de documentos.")

    def perguntar(self, query: str) -> dict:
        """
        Executa uma pergunta contra a pipeline de RAG.

        Args:
            query (str): A pergunta do usuário.

        Returns:
            dict: Um dicionário contendo a resposta e as fontes.
        """
        if not self.retriever or not self.document_chain:
            return {"resposta": "A pipeline não foi configurada corretamente. Execute o método setup().", "fontes": []}
            
        print("\nBuscando documentos relevantes...")
        docs_relacionados = self.retriever.invoke(query)
        print(f"Encontrados {len(docs_relacionados)} documentos relevantes.")
        
        print("Gerando resposta com base nos documentos...")
        resposta = self.document_chain.invoke({
            "input": query,
            "context": docs_relacionados
        })
        
        fontes = self._formatar_citacoes(docs_relacionados, query)
        
        return {"resposta": resposta, "fontes": fontes}

    def _formatar_citacoes(self, docs_rel: list, query: str) -> list:
        """Formata as fontes dos documentos para exibição."""
        
        # Ferramentas de formatação
        import re
        from typing import List, Dict

        def _clean_text(s: str) -> str:
            return re.sub(r"\s+", " ", s or "").strip()

        def extrair_trecho(texto: str, query: str, janela: int = 240) -> str:
            txt = _clean_text(texto)
            termos = [t.lower() for t in re.findall(r"\w+", query or "") if len(t) >= 4]
            pos = -1
            for t in termos:
                pos = txt.lower().find(t)
                if pos != -1: break
            if pos == -1: pos = 0
            ini, fim = max(0, pos - janela//2), min(len(txt), pos + janela//2)
            return f"...{txt[ini:fim]}..."

        cites, seen = [], set()
        for d in docs_rel:
            src = Path(d.metadata.get("source","")).name
            page = int(d.metadata.get("page", 0)) + 1
            key = (src, page)
            if key in seen:
                continue
            seen.add(key)
            cites.append({"documento": src, "pagina": page, "trecho": extrair_trecho(d.page_content, query)})
        return cites[:3]


# --- Bloco Principal de Execução ---
if __name__ == "__main__":
    #GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # Use uma das suas chaves de API
    GOOGLE_API_KEY = "AIzaSyBeoQUgDGxOO-uU075SUrAfGklnimpdO2M"

    pasta_arquivos_PDF = r"C:\Users\pedrovictor.veras\OneDrive - Operador Nacional do Sistema Eletrico\Documentos\ESTAGIO_ONS_PVRV_2025\GitHub\Electrical-System-Simulator\ONS_SIMULATOR_SYSTEM\arquivos"

    # 1. Cria a instância da pipeline
    pipeline = RAGPipeline(google_api_key=GOOGLE_API_KEY, pdf_directory=pasta_arquivos_PDF)
    
    # 2. Executa a configuração (carrega PDFs, cria embeddings, etc.)
    pipeline.setup()
    
    # 3. Faz uma pergunta (apenas se a configuração foi bem-sucedida)
    if pipeline.document_chain:
        print("\n" + "="*50)

        pergunta = "Quais são as principais observações MUST"

        print(f"Fazendo a pergunta: [bold]{pergunta}[/bold]")
        
        resultado = pipeline.perguntar(pergunta)
        
        print("\n[bold]Resposta do Assistente:[/bold]")
        print(resultado["resposta"])
        
        print("\n[bold]Fontes Consultadas:[/bold]")
        if resultado["fontes"]:
            for fonte in resultado["fontes"]:
                print(f"  - Documento: {fonte['documento']}, Página: {fonte['pagina']}")
                print(f"    Trecho: {fonte['trecho']}")
        else:
            print("Nenhuma fonte específica foi consultada.")
        print("="*50)

