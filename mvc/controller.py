# -*- coding: utf-8 -*-
import os
from mvc.model import PDFModel
from mvc.view import PDFView

class PDFController:
    """
    Classe responsável por gerenciar a interação entre o Model e a View.
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def process_pdf(self, pages: str, extract_text: bool = True, extract_tables: bool = True):
        """
        Processa o PDF e atualiza a interface com os resultados.

        Args:
            pages (str): Páginas a serem processadas (ex: '1-3,5' ou 'all').
            extract_text (bool): Se True, extrai o texto do PDF.
            extract_tables (bool): Se True, extrai as tabelas do PDF.
        """
        if not os.path.exists(self.pdf_path):
            PDFView.display_error("Arquivo PDF não encontrado.")
            return

        if extract_text:
            text = PDFModel.extract_text_pypdf2(self.pdf_path, pages)
            PDFView.display_extracted_text(text)

        if extract_tables:
            tables = PDFModel.extract_tables(self.pdf_path, pages)
            PDFView.display_extracted_tables(tables)

    @staticmethod
    def extract_text_pypdf2(pdf_path: str, pages: str) -> str:
        """Método estático para extrair texto via PyPDF2."""
        return PDFModel.extract_text_pypdf2(pdf_path, pages)

    @staticmethod
    def extract_text_ocr(pdf_path: str, page: int) -> str:
        """Método estático para extrair texto via OCR."""
        return PDFModel.extract_text_ocr(pdf_path, page)
