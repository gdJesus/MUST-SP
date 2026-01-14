# https://github.com/CourtBouillon/weasyprint-samples/tree/main
import os
import markdown2
from weasyprint import HTML

# Arquivo Markdown
md_filename = "documento.md"
output_pdf = "documento_convertido.pdf"

# Verifica se o arquivo existe
if not os.path.exists(md_filename):
    raise FileNotFoundError(f"Arquivo '{md_filename}' não encontrado.")

# Lê o conteúdo do Markdown
with open(md_filename, "r", encoding="utf-8") as f:
    md_content = f.read()

# Converte para HTML
html_body = markdown2.markdown(md_content)

# Logotipo (pode ser local ou URL)
logo_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/ONS_logo.svg/1200px-ONS_logo.svg.png"

# Template HTML com header, footer e logotipo
html_template = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Relatório PDF</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
        }}
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        footer {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            text-align: center;
            font-size: 12px;
            color: #888;
        }}
        img.logo {{
            max-height: 80px;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        pre, code {{
            background-color: #f4f4f4;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
        }}
    </style>
</head>
<body>
    <header>
        {logo_url}
        <h1>Relatório de Estágio</h1>
    </header>

    {html_body}

    <footer>
        Gerado por Pedro Victor Rodrigues Veras - Estágio ONS
    </footer>
</body>
</html>
"""

# Gera o PDF
HTML(string=html_template).write_pdf(output_pdf)

print(f"✅ PDF gerado com sucesso: {output_pdf}")