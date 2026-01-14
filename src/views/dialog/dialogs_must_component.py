

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea, QFrame, QDialog, QTextBrowser, QTabWidget,
    QProgressBar, QStackedWidget, QMessageBox, QFileDialog
)


try:
    from ansi2html import Ansi2HTMLConverter
    ansi_converter = Ansi2HTMLConverter(dark_bg=True, scheme="xterm")
except ImportError:
    ansi_converter = None



# ==============================================================================
#! ESTILOS CSS
# Garante que o arquivo styles.py esteja na mesma pasta
# ==============================================================================

try:
    #usa pathlib para ir apra raiz do projeto e depois para a pasta src/views/dialog
    import pathlib

    base_path = pathlib.Path(__file__).parent.parent.parent.parent.parent.parent
    styles_path = base_path / "styles.py"
    if styles_path.exists():
        from styles import STYLESHEET, APP_STYLES
    else:
        print("AVISO: 'styles.py' não encontrado. Usando estilos padrão.")
        STYLESHEET = "QWidget { background-color: #111827; color: white; }"
        APP_STYLES = STYLESHEET
except Exception as e:
    print(f"Erro ao carregar estilos: {e}")
    STYLESHEET = "QWidget { background-color: #111827; color: white; }"
    APP_STYLES = STYLESHEET

# ==============================================================================
# DIÁLOGOS
# ==============================================================================

class DetailsDialog(QDialog):
    def __init__(self, annotation_content, history_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detalhes do Ponto de Conexão")
        self.setMinimumSize(700, 500)
        self.setStyleSheet(STYLESHEET)
        
        layout = QVBoxLayout(self)
        tab_widget = QTabWidget()

        ressalva_widget = QWidget()
        ressalva_layout = QVBoxLayout(ressalva_widget)
        text_view = QTextBrowser()
        text_view.setPlainText(annotation_content if annotation_content else "Nenhuma ressalva.")
        ressalva_layout.addWidget(text_view)
        
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        history_table = QTableWidget()
        history_table.setColumnCount(3)
        history_table.setHorizontalHeaderLabels(["Ano", "Período", "Valor MUST"])
        history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        history_table.setRowCount(len(history_data))
        
        for i, row in enumerate(history_data):
            valor = row.get('valor')
            valor_str = f"{valor}" if valor is not None else "N/D"
            history_table.setItem(i, 0, QTableWidgetItem(str(row['ano'])))
            history_table.setItem(i, 1, QTableWidgetItem(str(row['periodo'])))
            history_table.setItem(i, 2, QTableWidgetItem(valor_str))
        
        history_layout.addWidget(history_table)
        
        tab_widget.addTab(ressalva_widget, "Ressalva")
        tab_widget.addTab(history_widget, "Histórico de Valores")
        
        close_button = QPushButton("Fechar")
        close_button.clicked.connect(self.accept)
        
        layout.addWidget(tab_widget)
        layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)

class ApprovalDialog(QDialog):
    def __init__(self, cod_ons, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aprovar Solicitação")
        self.setStyleSheet(STYLESHEET)
        self.setMinimumWidth(400)
        self.approver_name = ""
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>Ponto de Conexão:</b> {cod_ons}"))
        layout.addWidget(QLabel("Digite seu nome para confirmar:"))
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nome do Responsável")
        layout.addWidget(self.name_input)
        
        button_layout = QHBoxLayout()
        self.confirm_button = QPushButton("Confirmar")
        self.confirm_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
    
    def accept(self):
        if self.name_input.text().strip():
            self.approver_name = self.name_input.text().strip()
            super().accept()
        else:
            self.name_input.setStyleSheet("border: 1px solid red;")
