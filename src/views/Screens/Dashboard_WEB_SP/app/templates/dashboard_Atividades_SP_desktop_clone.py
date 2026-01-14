import sys
import pandas as pd
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QComboBox, QFileDialog, QTableView, QHeaderView,
    QLabel, QFrame, QGridLayout, QDialog, QCalendarWidget,
    QTableWidget, QTableWidgetItem, QAbstractItemView
)
from PySide6.QtCore import (
    Qt, QObject, Signal, Slot, QThread, QAbstractTableModel
)
from PySide6.QtGui import QColor, QPalette, QTextCharFormat, QFont

# Para os gráficos
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# --- Folha de Estilo (CSS convertido para QSS) ---
STYLESHEET = """
QWidget {
    font-family: 'Inter', sans-serif;
    background-color: #f0f2f5;
    color: #212529;
}

/* --- Sidebar --- */
#sidebar {
    background-color: #212529;
}

#sidebar QLabel, #sidebar h3 {
    color: #adb5bd;
    font-weight: 500;
}

#sidebar #sidebarHeader {
    background-color: #343a40;
    color: #fff;
    font-size: 18px;
    font-weight: 700;
    padding: 15px;
    border: none;
}

#sidebar QComboBox {
    background-color: #343a40;
    color: #fff;
    border: 1px solid #495057;
    border-radius: 4px;
    padding: 5px;
}
#sidebar QComboBox::drop-down {
    border: none;
}
#sidebar QComboBox QAbstractItemView {
    background-color: #343a40;
    color: #fff;
    selection-background-color: #0d6efd;
}

#sidebar QPushButton {
    background-color: #0d6efd;
    color: white;
    border: none;
    padding: 8px;
    border-radius: 4px;
    font-weight: 500;
}
#sidebar QPushButton:hover {
    background-color: #0b5ed7;
}
#fileNameLabel {
    color: #adb5bd;
    font-size: 11px;
}

/* --- Main Content --- */
#content, #initialMessage {
    background-color: #f0f2f5;
}

/* --- Cards --- */
.card {
    background-color: white;
    border: none;
    border-radius: 8px;
}

.card QLabel {
    background-color: white;
}

.card #cardTitle {
    font-weight: 700;
    font-size: 16px;
}

.card #cardValue {
    font-weight: 700;
    font-size: 32px;
}

.card #cardDescription {
    color: #6c757d;
}

/* --- Tabela --- */
QTableView {
    border: none;
    gridline-color: #e0e0e0;
}
QHeaderView::section {
    background-color: #212529;
    color: white;
    padding: 4px;
    border: 1px solid #495057;
    font-weight: 600;
}

/* --- Agenda de Prioridades --- */
#agendaCard .QListWidget {
    border: 1px solid #dee2e6;
    border-radius: 4px;
}

#agendaCard .QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #f0f2f5;
}
#agendaCard h6 {
    font-weight: bold;
    font-size: 14px;
}

/* --- Modal --- */
QDialog {
    background-color: #f8f9fa;
}

QDialog #modal-activity-details {
    background-color: #e9ecef;
    border-radius: 5px;
}
"""

# --- MODELO (Lógica de Dados) ---

class DataModel(QObject):
    dataLoaded = Signal(list)
    processingFinished = Signal(dict)

    def __init__(self):
        super().__init__()
        self.all_data = pd.DataFrame()
        self.filtered_data = pd.DataFrame()
        self.sheet_names = []

    def parse_date(self, date_input):
        if pd.isna(date_input): return None
        try:
            # Pandas to_datetime é robusto para vários formatos
            parsed_date = pd.to_datetime(date_input)
            return parsed_date.normalize().to_pydatetime()
        except (ValueError, TypeError):
            return None
    
    def format_date(self, date_obj):
        if not isinstance(date_obj, datetime): return ''
        return date_obj.strftime('%d/%m/%Y')

    def calculate_workdays(self, end_date):
        if not isinstance(end_date, datetime): return None
        today = datetime.now().normalize()
        workdays = 0
        
        if end_date >= today:
            current_date = today
            while current_date < end_date:
                if current_date.weekday() < 5: # Segunda a Sexta
                    workdays += 1
                current_date += timedelta(days=1)
            return workdays
        else:
            current_date = end_date
            while current_date < today:
                if current_date.weekday() < 5:
                    workdays -= 1
                current_date += timedelta(days=1)
            return workdays
    
    @Slot(str)
    def load_workbook(self, file_path):
        try:
            xls = pd.ExcelFile(file_path)
            self.sheet_names = xls.sheet_names
            all_dfs = []
            for i, name in enumerate(self.sheet_names):
                df = pd.read_excel(xls, sheet_name=name)
                df['ORIGEM'] = name
                df['STATUS'] = 'Concluído' if 'CONCLUÍDOS' in name.upper() else 'Pendente'
                df['ID'] = f"{name.replace(' ', '')}-{df.index}"
                all_dfs.append(df)
            
            self.all_data = pd.concat(all_dfs, ignore_index=True)

            # Tratamento de dados
            self.all_data['dueDate'] = self.all_data['PREVISÃO DE TÉRMINO'].apply(self.parse_date)
            self.all_data['PREVISÃO DE TÉRMINO_FORMATADA'] = self.all_data['dueDate'].apply(self.format_date)
            self.all_data['DIAS ÚTEIS'] = self.all_data['dueDate'].apply(self.calculate_workdays)
            
            self.dataLoaded.emit(self.sheet_names)
            self.apply_filters({}) # Aplica filtro inicial (tudo)

        except Exception as e:
            print(f"Error loading workbook: {e}")

    @Slot(dict)
    def apply_filters(self, filters):
        df = self.all_data.copy()

        if filters.get('sheet') and filters['sheet'] != 'Consolidado':
            df = df[df['ORIGEM'] == filters['sheet']]
        
        if filters.get('responsible') and filters['responsible'] != 'Todos':
            df = df[df['RESPONSÁVEL'] == filters['responsible']]

        if filters.get('status') == 'Pendente':
            df = df[df['STATUS'] == 'Pendente']
        elif filters.get('status') == 'Concluído':
            df = df[df['STATUS'] == 'Concluído']
        
        if filters.get('ressalva') == 'Com Ressalvas':
            df = df[df['OBSERVAÇÃO'].notna() & (df['OBSERVAÇÃO'] != '')]
        elif filters.get('ressalva') == 'Sem Ressalvas':
            df = df[df['OBSERVAÇÃO'].isna() | (df['OBSERVAÇÃO'] == '')]
        
        self.filtered_data = df
        self.process_filtered_data()

    def process_filtered_data(self):
        # Process data for charts and tables
        stats = self.get_stats()
        priorities = self.get_categorized_priorities()
        activities_by_month = self.get_activities_by_month()

        self.processingFinished.emit({
            'stats': stats,
            'priorities': priorities,
            'table_data': self.filtered_data,
            'activities_by_month': activities_by_month
        })
    
    def get_stats(self):
        df = self.filtered_data
        total_activities = len(df)
        com_ressalvas = len(df[df['OBSERVAÇÃO'].notna() & (df['OBSERVAÇÃO'] != '')])
        status_counts = df['STATUS'].value_counts().to_dict()
        
        responsible_counts = df.groupby('RESPONSÁVEL')['STATUS'].value_counts().unstack(fill_value=0)
        
        return {
            'total_activities': total_activities,
            'unique_responsibles': df['RESPONSÁVEL'].nunique(),
            'ressalvas': {'com': com_ressalvas, 'sem': total_activities - com_ressalvas},
            'status_counts': {
                'pendente': status_counts.get('Pendente', 0),
                'concluido': status_counts.get('Concluído', 0)
            },
            'responsible_chart': responsible_counts.to_dict('index')
        }

    def get_categorized_priorities(self):
        today = datetime.now().normalize()
        next7 = today + timedelta(days=7)
        next30 = today + timedelta(days=30)
        
        pending_df = self.filtered_data[self.filtered_data['STATUS'] == 'Pendente'].dropna(subset=['dueDate'])
        
        categories = {'overdue': [], 'today': [], 'next7days': [], 'next30days': []}
        
        for _, row in pending_df.iterrows():
            due_date = row['dueDate']
            if due_date < today:
                categories['overdue'].append(row.to_dict())
            elif due_date == today:
                categories['today'].append(row.to_dict())
            elif due_date <= next7:
                categories['next7days'].append(row.to_dict())
            elif due_date <= next30:
                categories['next30days'].append(row.to_dict())
        
        for cat in categories:
            categories[cat].sort(key=lambda x: x['dueDate'])
            
        return categories
        
    def get_activities_by_month(self):
        monthly_activities = {}
        df_with_dates = self.filtered_data.dropna(subset=['dueDate'])
        
        for _, row in df_with_dates.iterrows():
            key = row['dueDate'].strftime('%Y-%m')
            if key not in monthly_activities:
                monthly_activities[key] = []
            monthly_activities[key].append(row.to_dict())
        return monthly_activities


# --- COMPONENTES DA VIEW ---

class MplChartWidget(QWidget):
    """Widget para incorporar um gráfico Matplotlib."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.figure.patch.set_facecolor('#FFFFFF')

    def plot_pie(self, sizes, labels, colors):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        self.canvas.draw()
        
    def plot_stacked_bar(self, data):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        labels = list(data.keys())
        pendente = [d.get('Pendente', 0) for d in data.values()]
        concluido = [d.get('Concluído', 0) for d in data.values()]
        
        ax.bar(labels, pendente, label='Pendente', color='#dc3545')
        ax.bar(labels, concluido, bottom=pendente, label='Concluído', color='#198754')
        
        ax.set_ylabel('Nº de Atividades')
        ax.legend()
        self.figure.autofmt_xdate()
        self.canvas.draw()


class PandasModel(QAbstractTableModel):
    """Modelo de tabela para exibir DataFrames do Pandas."""
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        
        value = self._data.iloc[index.row(), index.column()]
        
        if role == Qt.DisplayRole:
            return str(value)
        
        if role == Qt.BackgroundRole:
            if self._data.columns[index.column()] == 'PREVISÃO DE TÉRMINO_FORMATADA' and value:
                return QColor('#212529')
        
        if role == Qt.ForegroundRole:
            col_name = self._data.columns[index.column()]
            if col_name == 'PREVISÃO DE TÉRMINO_FORMATADA' and value:
                return QColor('#FFFFFF')
            
            if col_name in ['DIAS ÚTEIS', 'TEMPO TOTAL']:
                try:
                    if int(value) < 0:
                        return QColor('red')
                except (ValueError, TypeError):
                    pass
        
        if role == Qt.FontRole:
            col_name = self._data.columns[index.column()]
            if col_name in ['DIAS ÚTEIS', 'TEMPO TOTAL']:
                try:
                    if int(value) < 0:
                        font = QFont()
                        font.setBold(True)
                        return font
                except (ValueError, TypeError):
                    pass
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._data.columns[section]
            if orientation == Qt.Vertical:
                return str(self._data.index[section])
        return None


# --- VIEW PRINCIPAL ---

class MainWindow(QMainWindow):
    fileRequested = Signal(str)
    filtersChanged = Signal(dict)
    dateCellClicked = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard de Atividades")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet(STYLESHEET)

        # Layout principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar ---
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 10, 10, 10)

        # Header
        header_label = QLabel("Controles")
        header_label.setObjectName("sidebarHeader")
        header_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(header_label)

        # Controles
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        # File loader
        load_btn = QPushButton(" Carregar Excel")
        load_btn.clicked.connect(self.open_file_dialog)
        self.file_name_label = QLabel("Nenhum arquivo.")
        self.file_name_label.setObjectName("fileNameLabel")
        controls_layout.addWidget(QLabel("Arquivo"))
        controls_layout.addWidget(load_btn)
        controls_layout.addWidget(self.file_name_label)
        
        # Filtros
        self.sheet_combo = self.create_combo_box("Visão por Aba", ["Carregue um arquivo"], controls_layout)
        self.responsavel_combo = self.create_combo_box("Responsável", ["Todos"], controls_layout)
        self.status_combo = self.create_combo_box("Status Geral", ["Todos", "Pendente", "Concluído"], controls_layout)
        self.ressalva_combo = self.create_combo_box("Ressalvas", ["Todas", "Com Ressalvas", "Sem Ressalvas"], controls_layout)

        sidebar_layout.addWidget(controls_widget)
        sidebar_layout.addStretch()
        main_layout.addWidget(self.sidebar)

        # --- Content ---
        self.content_area = QWidget()
        self.content_area.setObjectName("content")
        content_layout = QVBoxLayout(self.content_area)
        main_layout.addWidget(self.content_area)

        # Navbar
        navbar = QFrame()
        navbar_layout = QHBoxLayout(navbar)
        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setFixedSize(40, 40)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        navbar_layout.addWidget(self.toggle_btn)
        navbar_layout.addWidget(QLabel("Dashboard de Atividades"))
        navbar_layout.addStretch()
        content_layout.addWidget(navbar)

        # Área de conteúdo principal (cards, gráficos, etc.)
        self.main_stack = QWidget()
        self.main_stack_layout = QVBoxLayout(self.main_stack)
        content_layout.addWidget(self.main_stack)
        
        self.create_dashboard_widgets()
        
        # Mensagem inicial
        self.initial_message = QLabel("Aguardando arquivo...\nUse o menu lateral para carregar um arquivo Excel.")
        self.initial_message.setAlignment(Qt.AlignCenter)
        self.initial_message.setObjectName("initialMessage")
        content_layout.addWidget(self.initial_message)
        
        self.dashboard_widgets.setHidden(True)


    def create_combo_box(self, label, items, layout):
        layout.addWidget(QLabel(label))
        combo = QComboBox()
        combo.addItems(items)
        combo.currentTextChanged.connect(self.on_filters_changed)
        layout.addWidget(combo)
        return combo

    def create_dashboard_widgets(self):
        self.dashboard_widgets = QWidget()
        layout = QVBoxLayout(self.dashboard_widgets)

        # Stats Cards
        cards_layout = QHBoxLayout()
        self.total_card_value = QLabel("0")
        self.resp_card_value = QLabel("0")
        cards_layout.addWidget(self.create_stat_card("Total de Atividades", self.total_card_value))
        cards_layout.addWidget(self.create_stat_card("Responsáveis Únicos", self.resp_card_value))
        layout.addLayout(cards_layout)

        # Charts
        charts_layout = QHBoxLayout()
        self.status_chart = MplChartWidget()
        self.ressalvas_chart = MplChartWidget()
        self.resp_chart = MplChartWidget()
        charts_layout.addWidget(self.create_chart_card("Status Geral", self.status_chart))
        charts_layout.addWidget(self.create_chart_card("Atividades c/ Ressalva", self.ressalvas_chart))
        charts_layout.addWidget(self.create_chart_card("Atividades por Responsável", self.resp_chart))
        layout.addLayout(charts_layout)
        
        # Agenda
        self.agenda_widget = QWidget()
        self.agenda_layout = QHBoxLayout(self.agenda_widget)
        layout.addWidget(self.create_chart_card("Agenda de Prioridades", self.agenda_widget))

        # Tabela
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_view.clicked.connect(self.on_table_cell_clicked)
        layout.addWidget(self.create_chart_card("Detalhes da Atividade", self.table_view))
        
        self.main_stack_layout.addWidget(self.dashboard_widgets)

    def create_stat_card(self, title, value_label):
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setObjectName("cardDescription")
        value_label.setObjectName("cardValue")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card
        
    def create_chart_card(self, title, content_widget):
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        layout.addWidget(title_label)
        layout.addWidget(content_widget)
        return card

    def toggle_sidebar(self):
        self.sidebar.setHidden(not self.sidebar.isHidden())

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Abrir Arquivo Excel", "", "Excel Files (*.xlsx *.xls)")
        if file_path:
            self.file_name_label.setText(file_path.split('/')[-1])
            self.dashboard_widgets.setHidden(True)
            self.initial_message.setText("Processando arquivo...")
            self.initial_message.setHidden(False)
            self.fileRequested.emit(file_path)

    @Slot()
    def on_filters_changed(self):
        filters = {
            'sheet': self.sheet_combo.currentText(),
            'responsible': self.responsavel_combo.currentText(),
            'status': self.status_combo.currentText(),
            'ressalva': self.ressalva_combo.currentText(),
        }
        self.filtersChanged.emit(filters)

    @Slot(list)
    def update_combo_boxes(self, sheet_names):
        # Responsavel combo
        responsibles = self.controller.model.all_data['RESPONSÁVEL'].dropna().unique()
        self.responsavel_combo.blockSignals(True)
        self.responsavel_combo.clear()
        self.responsavel_combo.addItems(["Todos"] + sorted(responsibles))
        self.responsavel_combo.blockSignals(False)
        
        # Sheet combo
        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()
        self.sheet_combo.addItems(["Consolidado"] + sheet_names)
        self.sheet_combo.blockSignals(False)

    @Slot(dict)
    def update_dashboard(self, data):
        self.initial_message.setHidden(True)
        self.dashboard_widgets.setHidden(False)

        stats = data['stats']
        priorities = data['priorities']
        
        # Cards
        self.total_card_value.setText(str(stats['total_activities']))
        self.resp_card_value.setText(str(stats['unique_responsibles']))

        # Charts
        self.status_chart.plot_pie(
            [stats['status_counts']['pendente'], stats['status_counts']['concluido']],
            ['Pendente', 'Concluído'], ['#ffc107', '#198754']
        )
        self.ressalvas_chart.plot_pie(
            [stats['ressalvas']['com'], stats['ressalvas']['sem']],
            ['Com Ressalvas', 'Sem Ressalvas'], ['#ffc107', '#0d6efd']
        )
        self.resp_chart.plot_stacked_bar(stats['responsible_chart'])
        
        # Agenda
        self.update_agenda(priorities)
        
        # Tabela
        self.update_table(data['table_data'])

    def update_agenda(self, categories):
        # Limpa layout anterior
        while self.agenda_layout.count():
            child = self.agenda_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        configs = {
            'overdue': ('Atrasadas', '#dc3545'), 'today': ('Para Hoje', '#0d6efd'),
            'next7days': ('Próximos 7 Dias', '#0dcaf0'), 'next30days': ('Próximos 30 Dias', '#6c757d')
        }
        
        for key, (title, color) in configs.items():
            col_widget = QWidget()
            col_layout = QVBoxLayout(col_widget)
            
            title_label = QLabel(f"{title} ({len(categories[key])})")
            title_label.setStyleSheet(f"color: {color}; font-weight: bold;")
            col_layout.addWidget(title_label)
            
            list_widget = QTableWidget()
            list_widget.setColumnCount(2)
            list_widget.setRowCount(len(categories[key]))
            list_widget.setShowGrid(False)
            list_widget.verticalHeader().hide()
            list_widget.horizontalHeader().hide()
            list_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

            for i, item in enumerate(categories[key]):
                list_widget.setItem(i, 0, QTableWidgetItem(item['ATIVIDADES']))
                list_widget.setItem(i, 1, QTableWidgetItem(item['PREVISÃO DE TÉRMINO_FORMATADA']))
            
            col_layout.addWidget(list_widget)
            self.agenda_layout.addWidget(col_widget)

    def update_table(self, df):
        cols_to_show = ['ORIGEM', 'STATUS', 'ATIVIDADES', 'RESPONSÁVEL', 'PREVISÃO DE TÉRMINO_FORMATADA', 'DIAS ÚTEIS', 'TEMPO TOTAL', 'OBSERVAÇÃO']
        df_display = df[[col for col in cols_to_show if col in df.columns]].copy()
        
        self.pandas_model = PandasModel(df_display)
        self.table_view.setModel(self.pandas_model)

    def on_table_cell_clicked(self, index):
        col_name = self.pandas_model._data.columns[index.column()]
        if col_name == 'PREVISÃO DE TÉRMINO_FORMATADA':
            activity_id = self.pandas_model._data.iloc[index.row()]['ID']
            self.dateCellClicked.emit(activity_id)

# --- Controller ---
class AppController(QObject):
    def __init__(self, model, view):
        super().__init__()
        self.model = model
        self.view = view
        self.view.controller = self # Give view a reference to controller
        
        # Conexões
        self.view.fileRequested.connect(self.load_file)
        self.view.filtersChanged.connect(self.model.apply_filters)
        self.model.dataLoaded.connect(self.view.update_combo_boxes)
        self.model.processingFinished.connect(self.view.update_dashboard)
        self.view.dateCellClicked.connect(self.show_calendar_modal)
        
    def load_file(self, file_path):
        self.model.load_workbook(file_path)

    def show_calendar_modal(self, activity_id):
        activity = next((row for _, row in self.model.all_data.iterrows() if row['ID'] == activity_id), None)
        if activity is not None and activity['dueDate'] is not None:
            activities_in_month = self.model.get_activities_for_month(activity['dueDate'])
            dialog = CalendarDialog(activity, activities_in_month, self.view)
            dialog.exec()

# --- Dialog do Calendário ---
class CalendarDialog(QDialog):
    def __init__(self, selected_activity, month_activities, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Timeline da Atividade")
        self.setMinimumSize(800, 600)
        self.selected_activity = selected_activity
        self.month_activities = month_activities
        
        layout = QVBoxLayout(self)
        
        self.calendar = QCalendarWidget()
        self.details_label = QLabel("Selecione um dia para ver os detalhes.")
        self.details_label.setWordWrap(True)
        self.details_label.setObjectName("modal-activity-details")
        self.details_label.setAlignment(Qt.AlignTop)
        
        layout.addWidget(self.calendar)
        layout.addWidget(self.details_label)
        
        self.setup_calendar()
        self.calendar.selectionChanged.connect(self.update_details_for_selection)

    def setup_calendar(self):
        self.calendar.setSelectedDate(self.selected_activity['dueDate'])
        
        date_format = QTextCharFormat()
        date_format.setBackground(QColor("#cfe2ff"))
        
        for activity in self.month_activities:
            if activity['dueDate']:
                self.calendar.setDateTextFormat(activity['dueDate'], date_format)

        self.update_details(self.selected_activity['dueDate'])

    def update_details_for_selection(self):
        selected_date = self.calendar.selectedDate().toPython()
        self.update_details(selected_date)

    def update_details(self, date_obj):
        activities_on_day = [
            act for act in self.month_activities if act['dueDate'] and act['dueDate'].date() == date_obj.date()
        ]
        
        if not activities_on_day:
            self.details_label.setText("Nenhuma atividade para este dia.")
            return

        details_html = ""
        for i, activity in enumerate(activities_on_day):
            if i > 0:
                details_html += "<hr>"
            
            status_badge_color = 'green' if activity['STATUS'] == 'Concluído' else 'orange'
            details_html += f"""
                <p><b>Atividade:</b> {activity['ATIVIDADES']}</p>
                <p><b>Responsável:</b> {activity.get('RESPONSÁVEL', 'N/D')} | <b>Status:</b> <span style='color:{status_badge_color};'>{activity['STATUS']}</span></p>
                <p><b>Dias Úteis:</b> {activity['DIAS ÚTEIS']} | <b>Tempo Total:</b> {activity.get('TEMPO TOTAL', 'N/A')}</p>
                <p><b>Observação:</b> {activity.get('OBSERVAÇÃO', 'N/A')}</p>
            """
        self.details_label.setText(details_html)


# --- Ponto de Entrada da Aplicação ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    model = DataModel()
    view = MainWindow()
    controller = AppController(model, view)
    
    view.show()
    sys.exit(app.exec())
