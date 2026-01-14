# -*- coding: utf-8 -*-
import pandas as pd

class ExcelExporter:
    """
    Classe responsável por exportar DataFrames para arquivos Excel.
    """

    @staticmethod
    def export_to_excel(df: pd.DataFrame, output_path: str):
        """
        Exporta um DataFrame para um arquivo Excel.

        Args:
            df (pd.DataFrame): DataFrame a ser exportado.
            output_path (str): Caminho do arquivo de saída.
        """
        if df.empty:
            print("Nenhum dado para exportar.")
            return
        try:
            df.to_excel(output_path, index=False, engine='xlsxwriter')
            print(f"💾 Planilha salva com sucesso em: {output_path}")
        except Exception as e:
            print(f"❌ Erro ao salvar a planilha: {e}")
