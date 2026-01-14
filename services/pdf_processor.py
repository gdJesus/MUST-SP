# -*- coding: utf-8 -*-
import os
from PyPDF2 import PdfReader

class PDFProcessor:
    """
    Classe responsável por processar arquivos PDF e extrair texto bruto.
    """

    def __init__(self, pdf_path: str):
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"O arquivo não foi encontrado: {pdf_path}")
        self.pdf_path = pdf_path

    def extract_text(self) -> str:
        """
        Extrai o texto bruto de um arquivo PDF.

        Returns:
            str: Texto extraído do PDF.
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
