# -*- coding: utf-8 -*-
import os
from services.pdf_processor import PDFProcessor
from services.annotation_linker import AnnotationLinker
from services.excel_exporter import ExcelExporter

def process_PDF_text_single_pdf(pdf_path: str, output_folder: str):
    """
    Processa um único arquivo PDF, vinculando anotações e exportando os resultados para Excel.

    Args:
        pdf_path (str): Caminho do arquivo PDF a ser processado.
        output_folder (str): Pasta onde o arquivo Excel será salvo.
    """
    print(f"\n{'='*50}\nProcessando arquivo: {os.path.basename(pdf_path)}\n{'='*50}")

    #! 1) Processa o PDF e extrai o texto
    pdf_processor = PDFProcessor(pdf_path)
    raw_text = pdf_processor.extract_text()

    #! 2) Vincula anotações às linhas de dados
    annotation_linker = AnnotationLinker(raw_text)
    final_df = annotation_linker.link_annotations()

    if not final_df.empty:
        # Define o caminho de saída
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_excel_path = os.path.join(output_folder, f"saida_anotacoes_{base_name}.xlsx")

        #! 3) Exporta para Excel
        ExcelExporter.export_to_excel(final_df, output_excel_path)
    else:
        print("Nenhum dado processado para exportação.")

def process_PDF_text_folder_pdf(input_folder: str, output_folder: str):
    """
    Processa todos os arquivos PDF em uma pasta.

    Args:
        input_folder (str): Pasta contendo os arquivos PDF a serem processados.
        output_folder (str): Pasta onde os arquivos Excel serão salvos.
    """
    pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')]

    if not pdf_files:
        print(f"Nenhum arquivo PDF encontrado na pasta: {input_folder}")
        return

    for pdf_file in pdf_files:
        pdf_path = os.path.join(input_folder, pdf_file)
        process_PDF_text_single_pdf(pdf_path, output_folder)

