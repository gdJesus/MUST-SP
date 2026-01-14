# ... (APP_STYLES e classes PandasModel, Worker permanecem os mesmos) ...
APP_STYLES = """
QWidget {
    background-color: #2b2b2b; color: #f0f0f0; font-family: "Segoe UI", sans-serif; font-size: 10pt;
}
QMainWindow { background-color: #212121; }
QGroupBox {
    font-weight: bold; border: 1px solid #444; border-radius: 8px; margin-top: 10px; padding: 15px;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top center; padding: 0 10px; color: #f0f0f0;
}
QPushButton {
    background-color: #3c3f41; color: #f0f0f0; border: 1px solid #555;
    padding: 8px 16px; border-radius: 4px; font-weight: bold;
}
QPushButton:hover { background-color: #4f5355; }
QPushButton:pressed { background-color: #2a2d2f; }
QPushButton#run_button { background-color: #007acc; }
QPushButton#run_button:hover { background-color: #008ae6; }
QPushButton#export_excel { background-color: #9CCC65; }

QLineEdit, QTextEdit {
    background-color: #3c3f41; border: 1px solid #555; border-radius: 4px;
    padding: 5px; color: #f0f0f0;
}
QLabel { font-weight: bold; }
QTabWidget::pane { border: 1px solid #444; border-top: 0px; }
QTabBar::tab {
    background: #3c3f41; border: 1px solid #444; border-bottom: none;
    padding: 8px 16px; border-top-left-radius: 4px; border-top-right-radius: 4px;
}
QTabBar::tab:selected { background: #2b2b2b; margin-bottom: 0px; }
QTableView { gridline-color: #444; }
QHeaderView::section {
    background-color: #3c3f41; padding: 4px; border: 1px solid #555; font-weight: bold;
}
"""


STYLESHEET = """
QWidget { font-family: Arial, sans-serif; color: #E0E0E0; background-color: #111827; }
QMainWindow { background-color: #111827; }
QLabel { background-color: transparent; }
QLabel#headerTitle { font-size: 28px; font-weight: bold; }
QLabel#headerSubtitle { color: #9CA3AF; }
QLabel#sectionTitle { font-size: 18px; font-weight: bold; margin-bottom: 10px; margin-left: 5px;}
QFrame#kpiCard, QFrame#navPanel, QFrame#container { background-color: #1F2937; border-radius: 8px; }
QLabel#kpiTitle { color: #9CA3AF; font-size: 12px; }
QLabel#kpiValue { font-size: 26px; font-weight: bold; }
QLineEdit, QComboBox { background-color: #374151; border: 1px solid #4B5563; border-radius: 6px; padding: 8px; font-size: 14px; }
QLineEdit:focus, QComboBox:focus { border-color: #3B82F6; }
QPushButton { border-radius: 6px; padding: 8px 16px; font-size: 14px; font-weight: bold; text-align: left; }
QPushButton#navButton { background-color: transparent; border: none; padding: 12px; }
QPushButton#navButton:hover { background-color: #374151; }
QPushButton#navButton:checked { background-color: #3B82F6; color: white; }
QPushButton#filterButton { background-color: #EA580C; color: white; text-align: center; }
QPushButton#filterButton:hover { background-color: #F97316; }
QPushButton#clearButton { background-color: transparent; border: 1px solid #6B7280; text-align: center; }
QPushButton#clearButton:hover { background-color: #374151; }
QTableWidget { background-color: #1F2937; border: none; gridline-color: #374151; }
QHeaderView::section { background-color: #374151; color: #D1D5DB; padding: 8px; border: none; font-weight: bold; }
QTableWidget::item { padding-left: 10px; border-bottom: 1px solid #374151; }
QScrollBar:vertical, QScrollBar:horizontal { background: #1f2937; width: 10px; height: 10px; margin: 0; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #4b5563; min-width: 20px; border-radius: 5px; }
QTabWidget::pane { border: none; } QTabBar::tab { background: #1F2937; padding: 10px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
QTabBar::tab:selected { background: #374151; color: white; }
QProgressBar { border: 1px solid #4B5563; border-radius: 5px; text-align: center; color: #E0E0E0; background-color: #374151; }
QProgressBar::chunk { background-color: #F97316; border-radius: 4px; }
"""
