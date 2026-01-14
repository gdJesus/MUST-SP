import streamlit as st
from mvc.controller import PDFController

def tab_extract_text(controller: PDFController, pages: str):
    """
    Renderiza o conteúdo do Tab para extração de texto com PyPDF2.
    """
    st.header("Extrair Texto com PyPDF2")
    if st.button("Extrair Texto", key="b_pypdf2"):
        controller.process_pdf(pages, extract_text=True, extract_tables=False)

def tab_extract_text_ocr(controller: PDFController):
    """
    Renderiza o conteúdo do Tab para extração de texto com OCR.
    """
    st.header("Extrair Texto com Pytesseract (OCR)")
    page_ocr = st.number_input("Selecione a Página", min_value=1, max_value=100, value=1, step=1, key="ocr_page")
    if st.button("Extrair com OCR", key="b_ocr"):
        text = PDFController.extract_text_ocr("temp_uploaded_file.pdf", page_ocr)
        st.text_area("Texto Extraído por OCR", text, height=300)

def tab_extract_tables(controller: PDFController, pages: str):
    """
    Renderiza o conteúdo do Tab para extração de tabelas.
    """
    st.header("Extrair Tabelas")
    use_powerquery = st.checkbox("Usar PowerQuery", value=True)
    if st.button("Extrair Tabelas", key="b_tabula"):
        controller.process_pdf(pages, extract_text=False, extract_tables=True)

def read_must_tables_page(controller: PDFController, pages: str):

    """
    Renderiza o container de funcionalidades no Tab específico.
    """
    st.header("📂 Container de Funcionalidades")
    with st.container():
        st.subheader("Texto Extraído")
        if st.button("Extrair Texto (PyPDF2)", key="container_pypdf2"):
            controller.process_pdf(pages, extract_text=True, extract_tables=False)

        st.subheader("Texto OCR")
        page_ocr_container = st.number_input("Página para OCR", min_value=1, max_value=100, value=1, step=1, key="container_ocr_page")
        if st.button("Extrair Texto OCR", key="container_ocr"):
            text = PDFController.extract_text_ocr("temp_uploaded_file.pdf", page_ocr_container)
            st.text_area("Texto OCR Extraído", text, height=300)

        st.subheader("Tabelas Extraídas")
        use_powerquery_container = st.checkbox("Usar PowerQuery no Container", value=True, key="container_powerquery")
        if st.button("Extrair Tabelas no Container", key="container_tabula"):
            controller.process_pdf(pages, extract_text=False, extract_tables=True)
