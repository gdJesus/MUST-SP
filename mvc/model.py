# -*- coding: utf-8 -*-
import os
import re
import pandas as pd
import tempfile
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import pytesseract
import camelot
import tabula
from models.ClassPowerQuery import MiniPowerQuery

class PDFModel:
    """
    Classe responsável por gerenciar a lógica de extração de dados de PDFs.
    """

    @staticmethod
    def extract_text_pypdf2(pdf_path: str, pages: str) -> str:
        """
        Extrai texto de um PDF usando PyPDF2.

        Args:
            pdf_path (str): Caminho do arquivo PDF.
            pages (str): Páginas a serem extraídas (ex: '1-3,5' ou 'all').

        Returns:
            str: Texto extraído do PDF.
        """
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        page_indices = PDFModel._parse_pages_string(pages, total_pages)

        text = ""
        for page_index in page_indices:
            text += reader.pages[page_index].extract_text() or ""
        return text

    @staticmethod
    def extract_text_ocr(pdf_path: str, page: int) -> str:
        """
        Extrai texto de uma página de um PDF usando OCR (Pytesseract).

        Args:
            pdf_path (str): Caminho do arquivo PDF.
            page (int): Número da página a ser extraída.

        Returns:
            str: Texto extraído da página.
        """
        images = convert_from_path(pdf_path, first_page=page, last_page=page)
        if images:
            return pytesseract.image_to_string(images[0], lang='por')
        return ""

    @staticmethod
    def extract_tables(pdf_path: str, pages: str, use_powerquery: bool = True) -> list:
        """
        Extrai tabelas de um PDF usando Camelot e Tabula.

        Args:
            pdf_path (str): Caminho do arquivo PDF.
            pages (str): Páginas a serem extraídas (ex: '1-3,5' ou 'all').
            use_powerquery (bool): Se True, aplica limpeza avançada nas tabelas.

        Returns:
            list: Lista de DataFrames com as tabelas extraídas.
        """
        try:
            tables = camelot.read_pdf(pdf_path, pages=pages, flavor='lattice', strip_text='\n')
            if tables:
                return [PDFModel._process_table_with_powerquery(table.df) for table in tables] if use_powerquery else [table.df for table in tables]
        except Exception:
            pass

        try:
            tables = tabula.read_pdf(pdf_path, pages=pages, multiple_tables=True, stream=True, lattice=False, pandas_options={'header': None})
            if tables:
                return [PDFModel._process_table_with_powerquery(df) for df in tables] if use_powerquery else tables
        except Exception:
            pass

        return []

    @staticmethod
    def _process_table_with_powerquery(df: pd.DataFrame) -> pd.DataFrame:
        """
        Processa um DataFrame usando MiniPowerQuery para limpeza e formatação.

        Args:
            df (pd.DataFrame): DataFrame a ser processado.

        Returns:
            pd.DataFrame: DataFrame processado.
        """
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            temp_path = tmp.name
            df.to_csv(temp_path, index=False)

        try:
            mpq = MiniPowerQuery(temp_path)
            mpq.trim_spaces().drop_nulls(how='all').drop_duplicates().preview()
            return mpq.df
        finally:
            os.unlink(temp_path)

    @staticmethod
    def _parse_pages_string(pages: str, total_pages: int) -> list:
        """
        Converte uma string de páginas em uma lista de índices de páginas.

        Args:
            pages (str): String de páginas (ex: '1-3,5' ou 'all').
            total_pages (int): Número total de páginas no PDF.

        Returns:
            list: Lista de índices de páginas (base 0).
        """
        if pages.lower() == 'all':
            return list(range(total_pages))

        page_indices = set()
        for part in pages.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                page_indices.update(range(start - 1, end))
            else:
                page_indices.add(int(part) - 1)

        return sorted([i for i in page_indices if 0 <= i < total_pages])
