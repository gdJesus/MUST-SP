/*
 * Lógica Principal (Client-Side) para o Dashboard de Atividades
 */

// --- CONSTANTES GLOBAIS ---
const LOCAL_STORAGE_KEY = 'dashboardAppState_v5_planner'; // Chave atualizada

// --- MODELO ---
class DataModel {
    constructor() {
        this.excelData = { all: [], filtered: [], sheetNames: [], fileName: "Nenhum arquivo." };
        // Ferramentas manuais
        this.eisenhowerState = { important_urgent: [], important_not_urgent: [], not_important_urgent: [], not_important_not_urgent: [] };
        this.prosConsState = { pros: [], contras: [] };
        // NOVO ESTADO: Planejador
        this.plannerState = {
            unassigned: [],
            monday: [], tuesday: [], wednesday: [],
            thursday: [], friday: [], saturday: [], sunday: []
        };
    }
    
    // --- Helper para buscar o estado da ferramenta ---
    getToolState(toolType) {
        if (toolType === 'eisenhower') return this.eisenhowerState;
        if (toolType === 'prosCons') return this.prosConsState;
        if (toolType === 'planner') return this.plannerState;
        console.warn(`getToolState: Tipo de ferramenta desconhecido: ${toolType}`);
        return null;
    }


    // --- Métodos de Parse/Format/Cálculo ---
    parseDate(d){ if(d instanceof Date){ d.setHours(0,0,0,0); return d } if(typeof d === 'number' && d > 0){ try { const excelEpoch = new Date(Date.UTC(1899, 11, 30)); const date = new Date(excelEpoch.getTime() + d * 24 * 60 * 60 * 1000); if (!isNaN(date)) { date.setHours(0,0,0,0); return date; } } catch(e){ console.warn("Error parsing excel date number", e); } } if("string"!=typeof d||""===d.trim())return null; const t=d.trim(); let e=null; let a=t.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/); if(a)e=new Date(parseInt(a[1]),parseInt(a[2])-1,parseInt(a[3])); else if(a=t.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$/)){ const n=parseInt(a[1]),s=parseInt(a[2]),i=parseInt(a[3]); e=n>12?new Date(i,s-1,n):new Date(i,s-1,n) } return e&&!isNaN(e.getTime())?(e.setHours(0,0,0,0),e):null }
    formatDate(d){ return d instanceof Date&&!isNaN(d.getTime())?d.toLocaleDateString("pt-BR",{day:'2-digit', month:'2-digit', year:'numeric'}):"" }
    calculateWorkdays(d){ if(!(d instanceof Date)||isNaN(d.getTime()))return null; let t=new Date; t.setHours(0,0,0,0); if(d.getTime()===t.getTime())return 0; let e=0,a=new Date(t); if(d>t){ a.setDate(a.getDate()+1); for(;a<=d;){ const n=a.getDay(); 0!==n&&6!==n&&e++,a.setDate(a.getDate()+1) } }else for(;a>d;){ a.setDate(a.getDate()-1); const s=a.getDay(); 0!==s&&6!==s&&e-- } return e }

    // Carrega dados do arquivo Excel/CSV
     async loadWorkbook(file) {
         console.log(`Loading workbook: ${file.name}`);
         const data = await file.arrayBuffer();
         let workbook;
         let isCSV = file.name.toLowerCase().endsWith('.csv');

         try { // Leitura do arquivo (Excel ou CSV)
             if (isCSV) {
                 const textDecoder = new TextDecoder('utf-8'); let csvText = textDecoder.decode(data);
                 if (!/[\u00C0-\u017F]/.test(csvText)) {
                    try { const latin1Decoder = new TextDecoder('iso-8859-1'); csvText = latin1Decoder.decode(data); console.log("Decoded CSV as iso-8859-1"); } catch { console.warn("Failed decode as iso-8859-1"); }
                 } else { console.log("Decoded CSV as utf-8"); }
                 workbook = XLSX.read(csvText, { type: 'string', raw: true });
             } else {
                 workbook = XLSX.read(data, { type: 'array', cellDates: true }); console.log("Decoded Excel file");
             }
         } catch (error) { console.error("Error reading file:", error); throw new Error("Não foi possível ler o arquivo."); }

        this.excelData.sheetNames = workbook.SheetNames;
        this.excelData.fileName = file.name;
        console.log(`Sheets found: ${this.excelData.sheetNames}`);

        // Processa os dados
        const newAllData = [];
        this.excelData.sheetNames.forEach(name => {
            const worksheet = workbook.Sheets[name]; if (!worksheet) return;
            let sheetData;
            try { sheetData = XLSX.utils.sheet_to_json(worksheet, { raw: false, defval: "", dateNF:'dd/mm/yyyy'}); }
            catch (error) { console.error(`Error processing sheet "${name}":`, error); alert(`Erro ao processar aba "${name}".`); return; }

            sheetData.forEach((row, index) => {
                const findKey = (p) => { for (const n of p) { for (const c in row) { if (c && c.trim().toLowerCase() === n.toLowerCase()) return c; } } return null; };
                const atividadeKey = findKey(['atividade', 'atividades', 'descrição', 'description', 'task']);
                const responsavelKey = findKey(['responsável', 'responsavel', 'owner', 'assigned to']);
                const previsaoKey = findKey(['previsão de término', 'previsao de termino', 'prazo', 'due date', 'data final']);
                const observacaoKey = findKey(['observação', 'observacao', 'obs', 'comments', 'notas', 'notes']);
                const statusKey = findKey(['status', 'situação', 'situacao']);
                const tempoTotalKey = findKey(['tempo total']);

                const newRow = { ID: `${name.replace(/[^a-zA-Z0-9]/g, '')}-${index}`, ORIGEM: name };
                let statusValue = statusKey ? String(row[statusKey] || '').trim().toLowerCase() : '';
                const concluidoTerms = ['concluído', 'concluido', 'feito', 'ok', 'finalizado', 'concluded', 'done'];
                newRow.STATUS = (!statusValue && name.toLowerCase().includes('concluído')) || concluidoTerms.some(term => statusValue.includes(term)) ? 'Concluído' : 'Pendente';
                newRow.dueDate = this.parseDate(previsaoKey ? row[previsaoKey] : null);
                newRow['PREVISÃO DE TÉRMINO_FORMATADA'] = this.formatDate(newRow.dueDate);
                newRow['DIAS ÚTEIS'] = newRow.dueDate ? this.calculateWorkdays(newRow.dueDate) : '';
                newRow['ATIVIDADES'] = atividadeKey ? row[atividadeKey] || '' : `Item ${index+1}`;
                newRow['RESPONSÁVEL'] = responsavelKey ? row[responsavelKey] || '' : '';
                newRow['OBSERVAÇÃO'] = observacaoKey ? row[observacaoKey] || '' : '';
                newRow['TEMPO TOTAL'] = tempoTotalKey ? row[tempoTotalKey] || '' : '';
                newAllData.push(newRow);
            });
            console.log(`Processed sheet "${name}", added ${sheetData.length} rows.`);
        });
        this.excelData.all = newAllData;
        console.log("Workbook loading finished.");
    }


    // Aplica os filtros selecionados aos dados do Excel
    applyFilters({ sheet, responsible, status, ressalva }) {
        console.log("Applying filters:", { sheet, responsible, status, ressalva });
        let data = [...this.excelData.all];
        if (sheet && sheet !== 'Consolidado') data = data.filter(r => r.ORIGEM === sheet);
        if (responsible && responsible !== 'Todos') data = data.filter(r => r['RESPONSÁVEL'] === responsible);
        if (status === 'Pendente') data = data.filter(r => r.STATUS === 'Pendente');
        if (status === 'Concluído') data = data.filter(r => r.STATUS === 'Concluído');
        if (ressalva === 'Com Ressalvas') data = data.filter(r => r['OBSERVAÇÃO'] && String(r['OBSERVAÇÃO']).trim() !== '');
        if (ressalva === 'Sem Ressalvas') data = data.filter(r => !r['OBSERVAÇÃO'] || String(r['OBSERVAÇÃO']).trim() === '');
        this.excelData.filtered = data;
        console.log(`Filtering complete. ${this.excelData.filtered.length} rows remaining.`);
    }

    // Calcula estatísticas para os cards (baseado nos dados filtrados do Excel)
    getStats() {
        const data = this.excelData.filtered;
        const total = data.length;
        const comRessalvas = data.filter(r => r['OBSERVAÇÃO'] && String(r['OBSERVAÇÃO']).trim() !== '').length;
        const statusCounts = { pendente: data.filter(r => r.STATUS === 'Pendente').length, concluido: data.filter(r => r.STATUS === 'Concluído').length };
        const respChartData = {};
        data.forEach(r => {
            const resp = r['RESPONSÁVEL'] || 'Não atribuído';
            if (!respChartData[resp]) respChartData[resp] = { 'Pendente': 0, 'Concluído': 0 };
            if (r.STATUS === 'Pendente' || r.STATUS === 'Concluído') { respChartData[resp][r.STATUS]++; }
        });
        return { total, responsibleCount: new Set(data.map(r => r['RESPONSÁVEL']).filter(Boolean)).size, ressalvas: { com: comRessalvas, sem: total - comRessalvas }, statusCounts, respChartData };
    }

    // Retorna dados para o Kanban (apenas tarefas pendentes do Excel filtrado)
     getKanbanExcelData() {
         const tasks = this.excelData.filtered.filter(task => task.STATUS === 'Pendente');
         // Separa as tarefas pendentes pela categoria salva (se existir)
         const groupedTasks = { todo: [], inprogress: [], done: [] }; // done sempre vazio aqui
         tasks.forEach(task => {
             const category = task._kanbanCategory || 'todo'; // Default 'todo'
             if (groupedTasks[category]) {
                 groupedTasks[category].push(task);
             } else {
                 groupedTasks.todo.push(task); // Fallback para 'todo' se categoria inválida
             }
         });
         console.log("Grouped Kanban Excel data:", groupedTasks);
         return groupedTasks;
     }


    // Obtém dados para as matrizes MANUAIS e o NOVO PLANEJADOR
    getAnalysisData() {
        return {
            eisenhower: this.eisenhowerState,
            prosCons: this.prosConsState,
            planner: this.plannerState // Adiciona o estado do planejador
        };
    }

    // Obtém atividades do Excel de um mês específico (para o modal calendário)
    getActivitiesForMonth(date) {
        const year = date.getFullYear(), month = date.getMonth();
        return this.excelData.filtered.filter(r => r.dueDate && r.dueDate.getFullYear() === year && r.dueDate.getMonth() === month);
    }

    // Retorna lista única de responsáveis (baseado em todos os dados do Excel)
    getUniqueResponsibles() { return [...new Set(this.excelData.all.map(r => r['RESPONSÁVEL']).filter(Boolean))].sort(); }

     // --- Métodos para ATUALIZAR ESTADO ---

     // Atualiza o STATUS de uma tarefa do Excel (na memória)
    updateExcelActivityStatus(itemId, newStatus, newKanbanCategory = null) {
        let changed = false;
        let itemFound = null;
        // Atualiza em allData
        const itemAll = this.excelData.all.find(item => item.ID === itemId);
        if (itemAll) {
            itemFound = itemAll; // Guarda a referência
            if (itemAll.STATUS !== newStatus) {
                itemAll.STATUS = newStatus;
                console.log(`Updated status in allData for ${itemId} to ${newStatus}`);
                changed = true;
            }
            if (newKanbanCategory && newStatus === 'Pendente') { 
                itemAll._kanbanCategory = newKanbanCategory;
                console.log(`Set _kanbanCategory=${newKanbanCategory} for ${itemId}`);
            } else {
                delete itemAll._kanbanCategory;
                 console.log(`Removed _kanbanCategory for ${itemId}`);
            }
        }
        // Atualiza em filteredData (se existir lá)
        const itemFiltered = this.excelData.filtered.find(item => item.ID === itemId);
         if (itemFiltered) {
            if (itemFiltered.STATUS !== newStatus) {
                itemFiltered.STATUS = newStatus;
                console.log(`Updated status in filteredData for ${itemId} to ${newStatus}`);
                changed = true; 
            }
            if (newKanbanCategory && newStatus === 'Pendente') {
                itemFiltered._kanbanCategory = newKanbanCategory;
            } else {
                delete itemFiltered._kanbanCategory;
            }
         }

        if (changed) this.saveState(); // Salva se houve mudança
        return changed;
    }

    // Adiciona item manual (para Eisenhower, ProsCons, ou Planner)
    addManualItem(toolType, category, itemText) {
        const state = this.getToolState(toolType); // Usa o helper
        if (!state) return;
        
        const newItem = { id: `manual-${toolType}-${Date.now()}`, text: itemText };
        if (!state[category]) { state[category] = []; }
        state[category].push(newItem);
        console.log(`Added item to ${toolType}/${category}`);
        this.saveState();
    }

    // Remove item manual (para Eisenhower, ProsCons, ou Planner)
    removeManualItem(toolType, category, itemId) {
        const state = this.getToolState(toolType);
        if (!state) return false;
        
        if (state[category]) {
            const initialLength = state[category].length;
            state[category] = state[category].filter(item => item.id !== itemId);
            if(state[category].length < initialLength) {
                 console.log(`Removed item ${itemId} from ${toolType}/${category}`);
                 this.saveState();
                 return true;
            }
        }
         console.warn(`Item ${itemId} not found in ${toolType}/${category}`);
         return false;
    }

    // Atualiza texto de item manual (para Eisenhower, ProsCons, ou Planner)
    updateManualItem(toolType, itemId, newText) {
        const state = this.getToolState(toolType);
        if (!state) return false;
        
         for (const category in state) {
             if (!state[category]) continue; // Garante que a categoria existe
             const item = state[category].find(i => i.id === itemId);
             if (item) {
                 if (item.text !== newText) {
                    item.text = newText;
                    console.log(`Updated item ${itemId} text in ${toolType}/${category}`);
                    this.saveState();
                 }
                 return true;
             }
         }
         console.warn(`Item ${itemId} not found in ${toolType} state for update`);
         return false;
    }

     // Move item manual ENTRE categorias (para Eisenhower, ProsCons, ou Planner)
    moveManualItem(toolType, itemId, targetCategory) {
         const state = this.getToolState(toolType);
         if (!state) return false;
         
         let itemToMove = null;
         let oldCategory = null;
         // Encontra e remove da categoria antiga
         for(const category in state) {
             if (!state[category]) continue; 
            const index = state[category].findIndex(item => item.id === itemId);
            if (index !== -1) {
                itemToMove = state[category].splice(index, 1)[0];
                oldCategory = category;
                break;
            }
         }
         // Adiciona na nova categoria
         if (itemToMove) {
            if (!state[targetCategory]) { state[targetCategory] = []; }
            state[targetCategory].unshift(itemToMove); // Adiciona no início
            console.log(`Moved manual item ${itemId} from ${oldCategory} to ${targetCategory} in ${toolType}`);
            this.saveState();
            return true;
         }
         console.warn(`Manual item ${itemId} not found for moving in ${toolType}.`);
         return false;
    }


     // Salva o estado atual no localStorage
     saveState() {
        try {
            const stateToSave = {
                excelData: {
                     sheetNames: this.excelData.sheetNames,
                     fileName: this.excelData.fileName,
                     all: this.excelData.all
                },
                eisenhowerState: this.eisenhowerState,
                prosConsState: this.prosConsState,
                plannerState: this.plannerState // Salva o planejador
            };
            localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(stateToSave));
            console.log("Application state saved to localStorage.");
        } catch (e) {
            console.error("Error saving state to localStorage:", e);
        }
    }

     // Carrega o estado do localStorage
    loadState() {
        const savedState = localStorage.getItem(LOCAL_STORAGE_KEY);
        if (savedState) {
            try {
                const parsedState = JSON.parse(savedState);
                console.log("Loading state from localStorage:", parsedState);

                // Restaura estado das ferramentas manuais
                this.eisenhowerState = parsedState.eisenhowerState || { important_urgent: [], important_not_urgent: [], not_important_urgent: [], not_important_not_urgent: [] };
                this.prosConsState = parsedState.prosConsState || { pros: [], contras: [] };
                // Restaura estado do planejador
                this.plannerState = parsedState.plannerState || { unassigned: [], monday: [], tuesday: [], wednesday: [], thursday: [], friday: [], saturday: [], sunday: [] };


                // Restaura informações E dados do último arquivo Excel
                if (parsedState.excelData && parsedState.excelData.all) {
                    this.excelData.sheetNames = parsedState.excelData.sheetNames || [];
                    this.excelData.fileName = parsedState.excelData.fileName || "Nenhum arquivo.";
                    this.excelData.all = parsedState.excelData.all.map(row => ({
                        ...row,
                        dueDate: row.dueDate ? new Date(row.dueDate) : null
                    }));
                     const fileNameEl = document.getElementById('file-name');
                     if (fileNameEl) fileNameEl.textContent = this.excelData.fileName;
                     console.log(`Restored ${this.excelData.all.length} rows from saved Excel data.`);
                } else {
                     console.log("No saved Excel data found.");
                     this.excelData = { all: [], filtered: [], sheetNames: [], fileName: "Nenhum arquivo." };
                }
                console.log("State loaded successfully.");
                return true;

            } catch (e) {
                console.error("Error parsing saved state:", e);
                localStorage.removeItem(LOCAL_STORAGE_KEY);
                this.excelData = { all: [], filtered: [], sheetNames: [], fileName: "Nenhum arquivo." };
                return false;
            }
        }
        console.log("No saved state found.");
        this.excelData = { all: [], filtered: [], sheetNames: [], fileName: "Nenhum arquivo." };
        return false;
    }
}

// --- VISÃO (View) ---
class DashboardView {
    constructor() {
        this.getElements(); // Busca elementos do DOM
        this.charts = {}; // Armazena instâncias dos gráficos
    }

    // Busca e atribui elementos do DOM
    getElements() {
        Object.assign(this, {
            loader: document.getElementById('loader-overlay'),
            sidebar: document.getElementById('sidebar'),
            sidebarToggle: document.getElementById('sidebar-toggle'),
            fileNameEl: document.getElementById('file-name'),
            sheetSelector: document.getElementById('sheet-selector'),
            responsavelFilter: document.getElementById('responsavel-filter'),
            statusGeralFilter: document.getElementById('status-geral-filter'),
            ressalvaFilter: document.getElementById('ressalva-filter'),
            dashboardContent: document.getElementById('dashboard-content'),
            initialMessage: document.getElementById('initial-message'), 
            dashboardViewContent: document.getElementById('dashboard-view-content'),
            statsCardsContainer: document.getElementById('stats-cards'),
            dataTableContainer: document.getElementById('data-table-container'),
            statusChartCanvas: document.getElementById('statusChart'),
            ressalvasChartCanvas: document.getElementById('ressalvasChart'),
            responsavelChartCanvas: document.getElementById('responsavelChart'),
            exportButton: document.getElementById('export-button'),
            // Containers das ferramentas
            kanbanExcelContainer: document.getElementById('kanban-excel-container'),
            eisenhowerContainer: document.getElementById('eisenhower-matrix-container'),
            prosConsContainer: document.getElementById('pros-cons-container'),
            plannerContainer: document.getElementById('planner-container') // Novo container
        });
         if (!this.dashboardContent || !this.initialMessage || !this.dashboardViewContent) {
             console.error("Elementos essenciais do DOM não encontrados!");
         }
    }


    // Mostra/Esconde o overlay de carregamento
    toggleLoading(show) { if(this.loader) this.loader.classList.toggle('d-none', !show); }

    // Habilita/Desabilita a interface principal (Dashboard) vs inicial
     toggleDashboardContentVisibility(show) {
         if (this.dashboardViewContent) this.dashboardViewContent.classList.toggle('d-none', !show);
         if (this.initialMessage) this.initialMessage.classList.toggle('d-none', show);
    }

    // Atualiza o nome do arquivo exibido no sidebar
    updateFileName(name) { if(this.fileNameEl) this.fileNameEl.textContent = name; }

    // Popula os seletores de filtro com opções
    populateFilters(sheetNames, responsibles) {
         if (!this.sheetSelector || !this.responsavelFilter) return;
         this.sheetSelector.innerHTML = '<option value="Consolidado">Consolidado</option>';
         this.responsavelFilter.innerHTML = '<option value="Todos">Todos</option>';
         (sheetNames || []).forEach(n => { const o=document.createElement('option');o.value=n;o.textContent=n;this.sheetSelector.appendChild(o); });
         (responsibles || []).forEach(r => { const o=document.createElement('option');o.value=r;o.textContent=r;this.responsavelFilter.appendChild(o); });
         const hasData = sheetNames && sheetNames.length > 0;
         [this.sheetSelector, this.responsavelFilter, this.statusGeralFilter, this.ressalvaFilter].forEach(el => {
             if(el) el.disabled = !hasData;
         });
    }


    // Renderiza os cards de estatísticas
    renderStatsCards({ total, responsibleCount }) {
        if (!this.statsCardsContainer) return;
        this.statsCardsContainer.innerHTML = `
            <div class="col-sm-6 col-lg-6"><div class="card"><div class="card-body"><h5>Total Atividades (Visão)</h5><h2 class="fw-bold">${total}</h2></div></div></div>
            <div class="col-sm-6 col-lg-6"><div class="card"><div class="card-body"><h5>Responsáveis (Visão)</h5><h2 class="fw-bold">${responsibleCount}</h2></div></div></div>`;
    }

     // Renderiza o Kanban conectado ao Excel
     renderKanbanExcel(tasksByStatus, handlers) {
         if (!this.kanbanExcelContainer) { console.error("Container Kanban Excel não encontrado!"); return; }
         const config = { todo: { t: 'A Fazer' }, inprogress: { t: 'Em Andamento' }, done: { t: 'Concluído' } };
         let html = '<div class="row g-3">';

         for (const key in config) {
             const tasks = tasksByStatus[key] || [];
             html += `<div class="col-lg-4 col-md-6 d-flex flex-column">
                         <h6 class="text-secondary column-title"><i class="bi bi-list-task me-2"></i>${config[key].t} (${tasks.length})</h6>
                         <div class="kanban-column flex-grow-1" data-category="${key}" style="min-height: 400px; max-height: 600px; overflow-y: auto;">`;
             tasks.forEach(task => {
                 html += `<div class="kanban-card" draggable="true" data-id="${task.ID}">
                             <p class="mb-1 small fw-bold">${this.escapeHtml(task['ATIVIDADES'] || 'N/A')}</p>
                             <small class="text-muted">${this.escapeHtml(task['RESPONSÁVEL'] || 'N/D')}</small>
                          </div>`;
             });
             html += '</div></div>';
         }
         this.kanbanExcelContainer.innerHTML = html + '</div>';
         this._addManualDragDropListeners(this.kanbanExcelContainer, '.kanban-column', '.kanban-card', handlers);
     }


    // Renderiza Matriz Editável Genérica (usada por Eisenhower e Prós/Contras)
    _renderEditableMatrix(container, matrixData, sections, handlers, matrixType) {
         if (!container) { console.error(`Container da matriz "${matrixType}" não encontrado!`); return; }
         let html = `<div class="row g-3">`;
         sections.forEach(s => {
            const items = matrixData[s.id] || [];
            // Ajusta o número de colunas (lg) com base no número de seções
            const colClass = sections.length === 4 ? 'col-lg-3' : (sections.length === 2 ? 'col-lg-6' : 'col-lg-4');
            html += `<div class="${colClass} col-md-6 d-flex flex-column">
                        <div class="analysis-column flex-grow-1 ${s.bgClass || ''}" data-category="${s.id}">
                            <h6 class="column-title ${s.textClass || ''}" style="border-color: ${s.color};">
                                <span>${s.title} (${items.length})</span>
                                <i class="bi bi-plus-circle add-matrix-item" style="cursor:pointer;" data-quadrant="${s.id}" title="Adicionar Item"></i>
                            </h6>
                            <div class="items-container" style="max-height: 400px; overflow-y: auto;">
                                ${items.map(item => `
                                    <div class="manual-item" data-id="${item.id}" draggable="true">
                                        <p class="mb-0 small flex-grow-1 editable-text" contenteditable="true" data-task-id="${item.id}" style="min-height: 20px;">${this.escapeHtml(item.text) || ' '}</p>
                                        <button class="btn btn-sm btn-outline-danger delete-item ms-2 border-0 p-1" data-task-id="${item.id}" data-category="${s.id}" title="Remover Item"><i class="bi bi-x-lg"></i></button>
                                    </div>`).join('')}
                            </div>
                        </div>
                     </div>`;
         });
         html += `</div>`;
         container.innerHTML = html;

         container.querySelectorAll('.add-matrix-item').forEach(btn => btn.addEventListener('click', () => handlers.onAdd(btn.dataset.quadrant)));
         this._addManualEditDeleteListeners(container, handlers, matrixType);
         this._addManualDragDropListeners(container, '.analysis-column', '.manual-item', handlers);
    }


    renderEisenhower(data, handlers) {
        const quadrants = [ { id: 'important_urgent', title: 'Importante & Urgente', color: '#dc3545', textClass: 'text-danger' }, { id: 'important_not_urgent', title: 'Importante & Não Urgente', color: '#ffc107', textClass: 'text-warning' }, { id: 'not_important_urgent', title: 'Não Importante & Urgente', color: '#0dcaf0', textClass: 'text-info' }, { id: 'not_important_not_urgent', title: 'Não Importante & Não Urgente', color: '#6c757d', textClass: 'text-secondary' } ];
        this._renderEditableMatrix(this.eisenhowerContainer, data, quadrants, handlers, 'eisenhower');
    }

    renderProsCons(data, handlers) {
         const sections = [ { id: 'pros', title: 'Prós', color: '#198754', textClass: 'pros-title', bgClass: 'pros-column' }, { id: 'contras', title: 'Contras', color: '#dc3545', textClass: 'contras-title', bgClass: 'contras-column' } ];
         this._renderEditableMatrix(this.prosConsContainer, data, sections, handlers, 'prosCons');
    }
    
    // --- NOVO MÉTODO: Renderiza Planejador Semanal ---
    renderPlanner(data, handlers) {
        if (!this.plannerContainer) { console.error("Container do Planejador não encontrado!"); return; }
        
        const days = [
            { id: 'monday', title: 'Segunda-feira' }, { id: 'tuesday', title: 'Terça-feira' },
            { id: 'wednesday', title: 'Quarta-feira' }, { id: 'thursday', title: 'Quinta-feira' },
            { id: 'friday', title: 'Sexta-feira' }, { id: 'saturday', title: 'Sábado' },
            { id: 'sunday', title: 'Domingo' }
        ];
        const unassignedTasks = data.unassigned || [];
        
        let html = '<div class="planner-container">';
        
        // 1. Coluna de Tarefas Não Alocadas
        html += `<div class="planner-tasks-list" data-category="unassigned">
                    <h6 class="tasks-list-title">
                        <span><i class="bi bi-card-list me-2"></i>Não Alocadas (${unassignedTasks.length})</span>
                        <i class="bi bi-plus-circle add-matrix-item" style="cursor:pointer;" data-quadrant="unassigned" title="Adicionar Tarefa"></i>
                    </h6>
                    <div class="items-container">
                        ${unassignedTasks.map(item => `
                            <div class="planner-item" data-id="${item.id}" draggable="true">
                                <p class="mb-0 editable-text" contenteditable="true" data-task-id="${item.id}">${this.escapeHtml(item.text) || ' '}</p>
                                <button class="btn btn-sm btn-outline-danger delete-item ms-2 border-0 p-1" data-task-id="${item.id}" data-category="unassigned" title="Remover Item"><i class="bi bi-x-lg"></i></button>
                            </div>`).join('')}
                    </div>
                 </div>`;
        
        // 2. Colunas da Semana
        html += '<div class="planner-week-view">';
        days.forEach(day => {
            const dayTasks = data[day.id] || [];
            html += `<div class="planner-day-column" data-category="${day.id}">
                        <h6 class="day-title">${day.title} (${dayTasks.length})</h6>
                        <div class="items-container">
                            ${dayTasks.map(item => `
                                <div class="planner-item" data-id="${item.id}" draggable="true">
                                    <p class="mb-0 editable-text" contenteditable="true" data-task-id="${item.id}">${this.escapeHtml(item.text) || ' '}</p>
                                    <button class="btn btn-sm btn-outline-danger delete-item ms-2 border-0 p-1" data-task-id="${item.id}" data-category="${day.id}" title="Remover Item"><i class="bi bi-x-lg"></i></button>
                                </div>`).join('')}
                        </div>
                     </div>`;
        });
        html += '</div>'; // Fecha planner-week-view
        
        html += '</div>'; // Fecha planner-container
        this.plannerContainer.innerHTML = html;
        
        // 3. Adiciona todos os listeners
        this.plannerContainer.querySelectorAll('.add-matrix-item').forEach(btn => btn.addEventListener('click', () => handlers.onAdd(btn.dataset.quadrant)));
        this._addManualEditDeleteListeners(this.plannerContainer, handlers, 'planner');
        // Adiciona D&D para as colunas de tarefas E colunas de dias, para o item .planner-item
        this._addManualDragDropListeners(this.plannerContainer, '.planner-tasks-list, .planner-day-column', '.planner-item', handlers);
    }
    // --- FIM DO NOVO MÉTODO ---


    // Listeners para drag & drop MANUAL (Kanban E Matrizes)
    _addManualDragDropListeners(container, columnSelector, itemSelector, handlers) {
         if (!container) return;
         console.log(`Adding D&D listeners to ${container.id}`);
         const columns = container.querySelectorAll(columnSelector);
         const items = container.querySelectorAll(itemSelector);

         items.forEach(item => {
             item.removeEventListener('dragstart', this._handleDragStart);
             item.removeEventListener('dragend', this._handleDragEnd);
             item.addEventListener('dragstart', this._handleDragStart.bind(this));
             item.addEventListener('dragend', this._handleDragEnd.bind(this));
         });

         columns.forEach(column => {
              const oldDropHandler = column.__dropHandler;
              if (oldDropHandler) column.removeEventListener('drop', oldDropHandler);
              column.removeEventListener('dragover', this._handleDragOver);
              column.removeEventListener('dragleave', this._handleDragLeave);
              const dropHandler = (e) => this._handleDrop(e, handlers.onDrop);
              column.__dropHandler = dropHandler;
             column.addEventListener('dragover', this._handleDragOver);
             column.addEventListener('dragleave', this._handleDragLeave);
             column.addEventListener('drop', dropHandler);
         });
    }
     // --- Funções Helper para Drag & Drop (movidas para View) ---
     _handleDragStart(e) {
         const draggableElement = e.currentTarget;
         if (draggableElement.matches('.kanban-card, .manual-item, .planner-item')) { // Adiciona .planner-item
             e.dataTransfer.setData('text/plain', draggableElement.dataset.id);
             e.dataTransfer.effectAllowed = 'move';
             setTimeout(() => draggableElement.classList.add('dragging'), 0);
             console.log(`Drag Start: ID=${draggableElement.dataset.id}`);
         } else { e.preventDefault(); }
     }
     _handleDragEnd(e) { e.currentTarget.classList.remove('dragging'); console.log(`Drag End: ID=${e.currentTarget.dataset.id}`); }
     _handleDragOver(e) { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; e.currentTarget.classList.add('drag-over'); }
     _handleDragLeave(e) { e.currentTarget.classList.remove('drag-over'); }
     _handleDrop(e, onDropCallback) {
         e.preventDefault(); e.currentTarget.classList.remove('drag-over');
         const itemId = e.dataTransfer.getData('text/plain');
         const targetCategory = e.currentTarget.dataset.category;
         console.log(`Drop Event: ID=${itemId} -> Category=${targetCategory}`);
         if (itemId && targetCategory && onDropCallback) { onDropCallback(itemId, targetCategory); }
         else { console.warn("Drop event missing data", {itemId, targetCategory, onDropCallback}); }
     }


     // Listeners para edição e deleção MANUAL
     _addManualEditDeleteListeners(container, handlers, toolType) {
         if (!container) return;
         console.log(`Adding Edit/Delete listeners (delegated) to ${container.id}`);

         const clickHandler = (e) => {
             const deleteButton = e.target.closest('.delete-item');
             if (deleteButton) {
                 const itemElement = deleteButton.closest('[data-id]');
                 if (itemElement) {
                     const itemId = itemElement.dataset.id;
                     const category = itemElement.closest('[data-category]')?.dataset.category;
                     console.log(`Delete clicked: ID=${itemId}, Cat=${category}, Type=${toolType}`);
                     handlers.onDelete(category, itemId);
                 }
             }
         };
         container.removeEventListener('click', container.__clickHandler);
         container.addEventListener('click', clickHandler);
         container.__clickHandler = clickHandler;

        const focusinHandler = (e) => {
            const editableP = e.target.closest('.editable-text');
            if (editableP === e.target && !editableP.dataset.originalText) {
                editableP.dataset.originalText = editableP.innerText;
                console.log(`Focus In: Stored original text for ${editableP.dataset.taskId}`);
            }
        };
         container.removeEventListener('focusin', container.__focusinHandler, true);
         container.addEventListener('focusin', focusinHandler, true);
         container.__focusinHandler = focusinHandler;

         const blurHandler = (e) => {
             const editableP = e.target.closest('.editable-text');
             if (editableP === e.target) {
                 const itemId = editableP.dataset.taskId;
                 const newText = editableP.innerText.trim();
                 const originalText = editableP.dataset.originalText;
                 console.log(`Blur on item ${itemId}`);
                 if (itemId) {
                     if (newText && newText !== originalText) {
                         handlers.onUpdate(itemId, newText);
                     } else { editableP.innerText = originalText || ''; }
                 }
                 delete editableP.dataset.originalText;
             }
         };
          container.removeEventListener('focusout', container.__blurHandler);
          container.addEventListener('focusout', blurHandler);
          container.__blurHandler = blurHandler;

         const keydownHandler = (e) => {
             const editableP = e.target.closest('.editable-text');
             if (editableP && editableP === e.target) {
                 if (e.key === 'Enter') { e.preventDefault(); editableP.blur(); }
                 else if (e.key === 'Escape') { editableP.innerText = editableP.dataset.originalText || ''; editableP.blur(); }
             }
         };
          container.removeEventListener('keydown', container.__keydownHandler);
          container.addEventListener('keydown', keydownHandler);
          container.__keydownHandler = keydownHandler;
     }


    // Renderiza a tabela de dados do Excel
    renderDataTable(data, onDateClick) {
        if (!this.dataTableContainer) return;
        if (!data || data.length === 0) { this.dataTableContainer.innerHTML = '<p class="text-center text-muted mt-3">Nenhum dado para exibir.</p>'; return; }

        const headers = ['ORIGEM', 'STATUS', 'ATIVIDADES', 'RESPONSÁVEL', 'PREVISÃO DE TÉRMINO', 'DIAS ÚTEIS', 'TEMPO TOTAL', 'OBSERVAÇÃO'];
        let tableHtml = '<table class="table table-striped table-hover table-sm table-resizable">';
        tableHtml += `<thead class="table-dark sticky-top"><tr>${headers.map(h => `<th>${this.escapeHtml(h)}<div class="resizer"></div></th>`).join('')}</tr></thead><tbody>`;

        data.forEach(row => {
            tableHtml += `<tr>${headers.map(header => {
                let value = '', className = '', extra = '';
                if (header === 'PREVISÃO DE TÉRMINO') {
                    value = this.escapeHtml(row['PREVISÃO DE TÉRMINO_FORMATADA']) || '';
                    if (value && row.ID) {
                        className = 'fw-bold date-cell';
                        extra = `data-activity-id='${this.escapeHtml(row.ID)}' style="cursor: pointer;" title="Clique para ver no calendário"`;
                        if (row.STATUS === 'Pendente' && row.dueDate && row.dueDate < new Date().setHours(0,0,0,0)) { className += ' table-danger'; }
                    }
                } else {
                    value = row[header] !== undefined && row[header] !== null ? this.escapeHtml(String(row[header])) : '';
                }
                if (header === 'DIAS ÚTEIS') { const num = parseInt(row[header], 10); if (!isNaN(num) && num < 0) { className = 'text-danger fw-bold'; } }
                if (header === 'OBSERVAÇÃO') {
                     const fullObs = String(row[header] || '');
                     if (fullObs.length > 100) { value = this.escapeHtml(fullObs.substring(0, 100)) + '...'; extra += ` title="${this.escapeHtml(fullObs).replace(/"/g, '&quot;')}"`; }
                }
                return `<td class="${className}" ${extra}>${value}</td>`;
            }).join('')}</tr>`;
        });

        this.dataTableContainer.innerHTML = tableHtml + '</tbody></table>';
        this.makeTableResizable();

        this.dataTableContainer.querySelectorAll('.date-cell').forEach(cell => {
             if (cell.__dateClickHandler) { cell.removeEventListener('click', cell.__dateClickHandler); }
            if (cell.dataset.activityId) {
                 const handler = () => onDateClick(cell.dataset.activityId);
                 cell.addEventListener('click', handler);
                 cell.__dateClickHandler = handler;
            }
        });
    }

    escapeHtml(unsafe) {
        if (typeof unsafe !== 'string') return unsafe;
        return unsafe.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }

    makeTableResizable() {
         if (!this.dataTableContainer) return;
         const thead = this.dataTableContainer.querySelector('thead');
         if (!thead) return;
         let currentTh = null; let startX, startWidth;
         const onMouseMove = (e) => { if (currentTh && startWidth !== null) { const newWidth = startWidth + e.clientX - startX; currentTh.style.width = `${Math.max(newWidth, 50)}px`; } };
         const onMouseUp = () => { currentTh = null; startWidth = null; window.removeEventListener('mousemove', onMouseMove); window.removeEventListener('mouseup', onMouseUp); document.body.style.cursor = 'default'; };
         thead.removeEventListener('mousedown', thead.__resizerMouseDownHandler);
         const mouseDownHandler = (e) => {
             if (e.target.classList.contains('resizer')) {
                 e.preventDefault(); currentTh = e.target.closest('th'); if (!currentTh) return;
                 startX = e.clientX; startWidth = currentTh.offsetWidth;
                 window.addEventListener('mousemove', onMouseMove); window.addEventListener('mouseup', onMouseUp);
                 document.body.style.cursor = 'col-resize';
             }
         };
         thead.addEventListener('mousedown', mouseDownHandler);
         thead.__resizerMouseDownHandler = mouseDownHandler;
    }


    renderCharts(stats) {
        this._renderPieChart('statusChart', this.statusChartCanvas, ['Pendente', 'Concluído'], [stats.statusCounts.pendente, stats.statusCounts.concluido], ['#ffc107', '#198754']);
        this._renderPieChart('ressalvasChart', this.ressalvasChartCanvas, ['Com Ressalvas', 'Sem Ressalvas'], [stats.ressalvas.com, stats.ressalvas.sem], ['#dc3545', '#0d6efd']);
        this._renderBarChart('responsavelChart', this.responsavelChartCanvas, stats.respChartData);
    }

    _renderPieChart(id, canvas, labels, data, colors) {
        if (!canvas) { console.warn(`Canvas element "${id}" not found.`); return; }
        if (this.charts[id]) { this.charts[id].destroy(); }
        try {
             this.charts[id] = new Chart(canvas, { type: 'pie', data: { labels, datasets: [{ data, backgroundColor: colors }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' } } } });
             console.log(`Rendered pie chart: ${id}`);
        } catch (error) { console.error(`Error rendering pie chart "${id}":`, error); }
    }

    _renderBarChart(id, canvas, data) {
         if (!canvas) { console.warn(`Canvas element "${id}" not found.`); return; }
         if (this.charts[id]) { this.charts[id].destroy(); }
         try {
            const labels = Object.keys(data);
            const pendenteData = labels.map(l => data[l]?.Pendente || 0);
            const concluidoData = labels.map(l => data[l]?.Concluído || 0);
            this.charts[id] = new Chart(canvas, { type: 'bar', data: { labels, datasets: [ { label: 'Pendente', data: pendenteData, backgroundColor: '#ffc107' }, { label: 'Concluído', data: concluidoData, backgroundColor: '#198754' } ] }, options: { responsive: true, maintainAspectRatio: false, scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } }, plugins: { tooltip: { mode: 'index', intersect: false } } } });
             console.log(`Rendered bar chart: ${id}`);
         } catch (error) { console.error(`Error rendering bar chart "${id}":`, error); }
    }

    switchView(targetViewId) {
        console.log(`Switching view to: ${targetViewId}`);
        let foundView = false;
        document.querySelectorAll('.view-container').forEach(div => {
            if (div.id === targetViewId) { div.classList.remove('d-none'); foundView = true; }
            else { div.classList.add('d-none'); }
        });
        if (!foundView) { console.error(`View container "${targetViewId}" not found!`); document.getElementById('main-dashboard-view')?.classList.remove('d-none'); targetViewId = 'main-dashboard-view'; }
        document.querySelectorAll('.nav-link[data-view]').forEach(item => item.classList.remove('active'));
        const activeLink = document.querySelector(`.nav-link[data-view="${targetViewId}"]`);
        if(activeLink) { activeLink.classList.add('active'); }
        else { console.warn(`Nav link for view "${targetViewId}" not found.`); }
    }
}

// --- CONTROLLER (App Logic) ---
class AppController {
    constructor(model, view) {
        this.model = model;
        this.view = view;
        this.modal = new bootstrap.Modal(document.getElementById('calendarModal'));
        this.currentView = 'main-dashboard-view'; // View inicial
    }


    // Inicializa a aplicação
    init() {
        console.log("Initializing AppController...");
        this.view.toggleLoading(true);
        const stateLoaded = this.model.loadState();
        this.setupEventListeners(); // Configura listeners GLOBAIS

        if (!this.view.initialMessage || !this.view.dashboardViewContent) {
             console.error("View elements not ready!"); this.view.getElements();
             if (!this.view.initialMessage || !this.view.dashboardViewContent) {
                 alert("Erro crítico: Interface não inicializada."); this.view.toggleLoading(false); return;
             }
        }

        const hasSavedExcelData = stateLoaded && this.model.excelData.all && this.model.excelData.all.length > 0;

        if (hasSavedExcelData) {
            console.log("Previous Excel data found, populating...");
            this.view.populateFilters(this.model.excelData.sheetNames, this.model.getUniqueResponsibles());
            this.model.applyFilters({}); // Aplica filtro padrão
            this.view.toggleDashboardContentVisibility(true); // Mostra dashboard
            this.view.exportButton.disabled = false;
        } else {
            console.log("No previous Excel data. Waiting for file upload.");
             this.view.toggleDashboardContentVisibility(false); // Mostra msg inicial
            this.view.populateFilters([], []); // Filtros vazios
        }
        
        // Define a view com base no hash da URL (ou padrão)
        this.handleRouteChange(); 
        
        this.view.toggleLoading(false);
        console.log("Initialization complete.");
    }
    
    // Detecta a view correta com base no Path (rota)
    handleRouteChange() {
        // Usa o 'pathname' da URL atual para decidir qual view mostrar
        const path = window.location.pathname;
        console.log("Handling route change:", path);
        
        let targetView = 'main-dashboard-view'; // Padrão
        if (path.endsWith('/kanban')) {
            targetView = 'kanban-view';
        } else if (path.endsWith('/eisenhower')) {
            targetView = 'eisenhower-view';
        } else if (path.endsWith('/pros-contras')) {
            targetView = 'swot-view';
        } else if (path.endsWith('/planejador')) { // NOVA ROTA
            targetView = 'planner-view';
        }
        // Se for / ou /dashboard, mantém 'main-dashboard-view'
        
        this.currentView = targetView;
        this.updateDashboard(); // Renderiza a view correta
    }


    // Configura os listeners de eventos GLOBAIS da interface
    setupEventListeners() {
        console.log("Setting up global event listeners...");
         const fileInput = document.getElementById('file-input');
         if(fileInput) fileInput.addEventListener('change', e => this.handleFileSelect(e));

        [this.view.sheetSelector, this.view.responsavelFilter, this.view.statusGeralFilter, this.view.ressalvaFilter].forEach(el => {
             if(el) el.addEventListener('change', () => this.handleFilterChange());
        });
        if(this.view.sidebarToggle) this.view.sidebarToggle.addEventListener('click', () => {
             if(this.view.sidebar) this.view.sidebar.classList.toggle('active');
        });
        if(this.view.exportButton) this.view.exportButton.addEventListener('click', () => this.handleExport());

        // Atualiza os links de navegação para usar a History API (SPA)
        document.querySelectorAll('[data-view]').forEach(item => {
            item.addEventListener('click', (e) => {
                 e.preventDefault(); // Impede o recarregamento da página
                 const newView = e.currentTarget.dataset.view;
                 const newPath = e.currentTarget.getAttribute('href'); // Pega o path do Flask
                 
                 if (newView !== this.currentView) {
                     console.log(`Nav clicked: ${newView}, Path: ${newPath}`);
                     this.currentView = newView;
                     // Atualiza a URL no navegador sem recarregar
                     window.history.pushState({view: newView}, "", newPath);
                     this.updateDashboard(); // Apenas troca a view no JS
                 }
            });
        });
        
        // Ouve o evento 'popstate' (botões voltar/avançar do navegador)
        window.addEventListener('popstate', (e) => {
             console.log("Popstate event triggered (back/forward button)");
             this.handleRouteChange(); // Re-avalia a rota e atualiza a view
        });
        
        console.log("Global event listeners set up.");
    }

    // Manipula a seleção de um novo arquivo
    async handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) { console.log("File selection cancelled."); return; }
        console.log(`File selected: ${file.name}`);
        this.view.toggleLoading(true);
        this.view.updateFileName(file.name);
        try {
            await this.model.loadWorkbook(file);
            this.model.saveState();
            this.view.populateFilters(this.model.excelData.sheetNames, this.model.getUniqueResponsibles());
            this.handleFilterChange(); // Chama o updateDashboard
        } catch (error) {
            console.error("Error loading workbook:", error);
            alert(`Erro ao carregar o arquivo "${file.name}":\n${error.message}`);
            const stateLoaded = this.model.loadState();
             const fileNameEl = document.getElementById('file-name');
             if (fileNameEl) { fileNameEl.textContent = this.model.excelData.fileName; }
            this.model.excelData = { all: [], filtered: [], sheetNames: [], fileName: this.model.excelData.fileName };
            this.view.populateFilters([], []);
            this.handleFilterChange();
        } finally {
            this.view.toggleLoading(false);
        }
    }

    // Manipula a mudança nos filtros
    handleFilterChange() {
         console.log("Filter change detected.");
         if (this.model.excelData.all && this.model.excelData.all.length > 0) {
             console.log("Applying filters...");
            this.model.applyFilters({
                sheet: this.view.sheetSelector.value,
                responsible: this.view.responsavelFilter.value,
                status: this.view.statusGeralFilter.value,
                ressalva: this.view.ressalvaFilter.value,
            });
            if (this.currentView === 'main-dashboard-view' || this.currentView === 'kanban-view') {
                this.updateDashboard();
            }
         } else {
             console.log("No Excel data, filter change ignored.");
             if(this.currentView === 'main-dashboard-view') this.view.toggleDashboardContentVisibility(false);
             if(this.currentView === 'kanban-view' && this.view.kanbanExcelContainer) this.view.kanbanExcelContainer.innerHTML = '<p class="text-muted text-center">Carregue um arquivo Excel/CSV.</p>';
         }
    }

    // Atualiza a interface com base na view atual e nos dados do modelo
    updateDashboard() {
         console.log(`Updating dashboard UI for view: ${this.currentView}`);
         this.view.switchView(this.currentView); // Garante que a view correta está visível

         try {
            if (this.currentView === 'main-dashboard-view') {
                const hasExcelData = this.model.excelData.all && this.model.excelData.all.length > 0;
                this.view.toggleDashboardContentVisibility(hasExcelData);
                if (hasExcelData) {
                    const stats = this.model.getStats();
                    this.view.renderStatsCards(stats);
                    this.view.renderCharts(stats);
                    this.view.renderDataTable(this.model.excelData.filtered, id => this.handleDateClick(id));
                }
            } else if (this.currentView === 'kanban-view') {
                 const tasksByStatus = this.model.getKanbanExcelData();
                this.view.renderKanbanExcel(tasksByStatus, {
                    onDrop: (id, cat) => this.handleKanbanDrop(id, cat)
                });
                this.view.toggleDashboardContentVisibility(false); 
            } else if (this.currentView === 'eisenhower-view') {
                this.view.renderEisenhower(this.model.getAnalysisData().eisenhower, {
                   onAdd: (q) => this.handleManualToolAddItem('eisenhower', q),
                   onUpdate: (itemId, newText) => this.handleManualToolUpdateItem('eisenhower', itemId, newText),
                   onDelete: (category, itemId) => this.handleManualToolDeleteItem('eisenhower', category, itemId),
                   onDrop: (itemId, targetCategory) => this.handleManualToolDrop('eisenhower', itemId, targetCategory)
                });
                this.view.toggleDashboardContentVisibility(false);
            } else if (this.currentView === 'swot-view') {
                 this.view.renderProsCons(this.model.getAnalysisData().prosCons, {
                   onAdd: (category) => this.handleManualToolAddItem('prosCons', category),
                   onUpdate: (itemId, newText) => this.handleManualToolUpdateItem('prosCons', itemId, newText),
                   onDelete: (category, itemId) => this.handleManualToolDeleteItem('prosCons', category, itemId),
                   onDrop: (itemId, targetCategory) => this.handleManualToolDrop('prosCons', itemId, targetCategory)
                });
                this.view.toggleDashboardContentVisibility(false);
            } else if (this.currentView === 'planner-view') { // NOVA LÓGICA
                 this.view.renderPlanner(this.model.getAnalysisData().planner, {
                   onAdd: (category) => this.handleManualToolAddItem('planner', category),
                   onUpdate: (itemId, newText) => this.handleManualToolUpdateItem('planner', itemId, newText),
                   onDelete: (category, itemId) => this.handleManualToolDeleteItem('planner', category, itemId),
                   onDrop: (itemId, targetCategory) => this.handleManualToolDrop('planner', itemId, targetCategory)
                 });
                this.view.toggleDashboardContentVisibility(false);
            }
         } catch (error) {
             console.error(`Error during updateDashboard for view ${this.currentView}:`, error);
             alert("Ocorreu um erro ao atualizar a visualização.");
         }
         
         // Habilita/desabilita botão Exportar
         const hasExcelDataForExport = this.model.excelData.all && this.model.excelData.all.length > 0;
         const hasManualData = Object.values(this.model.eisenhowerState).some(arr => arr.length > 0) ||
                              Object.values(this.model.prosConsState).some(arr => arr.length > 0) ||
                              Object.values(this.model.plannerState).some(arr => arr.length > 0); // Adiciona checagem do planner
         if (this.view.exportButton) this.view.exportButton.disabled = !(hasExcelDataForExport || hasManualData);

         console.log("Dashboard UI update complete.");
    }

    // --- Handlers para Ferramentas ---
    handleKanbanDrop(taskId, targetColumnName) {
        console.log(`Kanban Drop (Excel Task): ID='${taskId}', Target='${targetColumnName}'`);
        const newStatus = (targetColumnName === 'done') ? 'Concluído' : 'Pendente';
         const newKanbanCategory = (newStatus === 'Pendente') ? targetColumnName : null;
        const statusChanged = this.model.updateExcelActivityStatus(taskId, newStatus, newKanbanCategory);
        this.updateDashboard(); // Re-renderiza Kanban
        
        if (statusChanged) {
             this.model.applyFilters({ // Re-aplica filtros
                sheet: this.view.sheetSelector.value,
                responsible: this.view.responsavelFilter.value,
                status: this.view.statusGeralFilter.value,
                ressalva: this.view.ressalvaFilter.value,
            });
        }
    }

    // Renomeado para ser genérico
    handleManualToolAddItem(toolType, category) {
        const text = prompt(`Adicionar item para ${category.replace('_', ' ')}:`);
        if (!text || text.trim() === "") return;
        this.model.addManualItem(toolType, category, text.trim());
        this.updateDashboard(); // Re-renderiza a view atual
    }
    handleManualToolUpdateItem(toolType, itemId, newText) {
        this.model.updateManualItem(toolType, itemId, newText);
    }
    handleManualToolDeleteItem(toolType, category, itemId) {
        if (!confirm("Tem certeza que deseja apagar este item?")) return;
        if (this.model.removeManualItem(toolType, category, itemId)) {
            this.updateDashboard();
        }
    }
    handleManualToolDrop(toolType, itemId, targetCategory) {
         console.log(`Manual Tool Drop: Type=${toolType}, ID='${itemId}', Target='${targetCategory}'`);
         if(this.model.moveManualItem(toolType, itemId, targetCategory)) {
             this.updateDashboard();
         }
    }

    handleExport() {
         console.log("Export button clicked.");
        this.view.toggleLoading(true);
        try {
            const workbook = XLSX.utils.book_new();
            let hasDataToExport = false;

            // 1. Aba de dados do Excel
            if(this.model.excelData.all && this.model.excelData.all.length > 0) {
                console.log(`Exporting ${this.model.excelData.all.length} Excel rows.`);
                const excelExportData = this.model.excelData.all.map(row => {
                    const { ID, ORIGEM, dueDate, _kanbanCategory, ...rest } = row;
                    if(rest['PREVISÃO DE TÉRMINO_FORMATADA']) { rest['PREVISÃO DE TÉRMINO'] = rest['PREVISÃO DE TÉRMINO_FORMATADA']; }
                    delete rest['PREVISÃO DE TÉRMINO_FORMATADA'];
                    return rest;
                });
                const excelSheet = XLSX.utils.json_to_sheet(excelExportData);
                XLSX.utils.book_append_sheet(workbook, excelSheet, "Dados Atividades");
                hasDataToExport = true;
            } else { console.log("No Excel data to export."); }

            // 2. Aba Eisenhower
            const eisenhowerExport = [];
            Object.entries(this.model.eisenhowerState).forEach(([q, items]) => { (items || []).forEach(item => eisenhowerExport.push({ Quadrante: q.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()), Item: item.text })); });
             if(eisenhowerExport.length > 0) {
                console.log(`Exporting ${eisenhowerExport.length} Eisenhower items.`);
                const eisenhowerSheet = XLSX.utils.json_to_sheet(eisenhowerExport);
                XLSX.utils.book_append_sheet(workbook, eisenhowerSheet, "Matriz Eisenhower");
                hasDataToExport = true;
            } else { console.log("No Eisenhower data to export."); }

            // 3. Aba Prós/Contras
            const prosConsExport = [];
             Object.entries(this.model.prosConsState).forEach(([col, items]) => { (items || []).forEach(item => prosConsExport.push({ Tipo: col.toUpperCase(), Item: item.text })); });
             if(prosConsExport.length > 0) {
                console.log(`Exporting ${prosConsExport.length} Pros/Cons items.`);
                const prosConsSheet = XLSX.utils.json_to_sheet(prosConsExport);
                XLSX.utils.book_append_sheet(workbook, prosConsSheet, "Prós e Contras");
                hasDataToExport = true;
            } else { console.log("No Pros/Cons data to export."); }
            
            // 4. NOVA ABA: Planejador Semanal
            const plannerExport = [];
            Object.entries(this.model.plannerState).forEach(([col, items]) => {
                // Formata o nome da categoria para o Excel
                let colName = col.charAt(0).toUpperCase() + col.slice(1);
                if (col === 'unassigned') colName = 'Não Alocadas';
                if (col === 'monday') colName = 'Segunda-feira';
                if (col === 'tuesday') colName = 'Terça-feira';
                if (col === 'wednesday') colName = 'Quarta-feira';
                if (col === 'thursday') colName = 'Quinta-feira';
                if (col === 'friday') colName = 'Sexta-feira';
                if (col === 'saturday') colName = 'Sábado';
                if (col === 'sunday') colName = 'Domingo';
                
                 (items || []).forEach(item => plannerExport.push({ Categoria: colName, Tarefa: item.text }));
            });
             if(plannerExport.length > 0) {
                console.log(`Exporting ${plannerExport.length} Planner items.`);
                const plannerSheet = XLSX.utils.json_to_sheet(plannerExport, {header: ["Categoria", "Tarefa"]}); // Define ordem
                XLSX.utils.book_append_sheet(workbook, plannerSheet, "Planejador Semanal");
                hasDataToExport = true;
            } else { console.log("No Planner data to export."); }
            
            
            if(hasDataToExport) {
                XLSX.writeFile(workbook, "Dashboard_Completo_Exportado.xlsx");
                console.log("Export successful.");
            } else {
                alert("Não há dados para exportar.");
                console.log("Export cancelled, no data found.");
            }
        } catch(e) { console.error("Error exporting data:", e); alert(`Erro na exportação:\n${e.message}`); }
        finally { this.view.toggleLoading(false); }
    }

    handleDateClick(activityId) {
         console.log(`Date cell clicked: ${activityId}`);
        const activity = this.model.excelData.all.find(a => a.ID === activityId);
        if (!activity) { console.warn("Activity not found."); return; }
        if (!activity.dueDate) { alert(`A atividade "${activity['ATIVIDADES']}" não possui data.`); return; }
        const activitiesInMonth = this.model.getActivitiesForMonth(activity.dueDate);
        console.log(`Found ${activitiesInMonth.length} activities for calendar.`);
        this.renderCalendarModal(activity.dueDate, activitiesInMonth);
        this.modal.show();
    }

    renderCalendarModal(date, activities) {
         const calendarContainer = document.getElementById('calendar-container');
         const detailsContainer = document.getElementById('modal-activity-details');
         if (!calendarContainer || !detailsContainer) return;
        const render = (dayOfMonth) => {
            calendarContainer.innerHTML = this.generateCalendarHTML(date, activities, dayOfMonth);
            calendarContainer.querySelectorAll('.has-activity').forEach(cell => {
                cell.addEventListener('click', e => render(parseInt(e.currentTarget.textContent)) );
            });
            this.updateModalDetails(detailsContainer, activities.filter(a => a.dueDate && a.dueDate.getDate() === dayOfMonth));
        }
        render(date.getDate());
    }

    generateCalendarHTML(date, activitiesForMonth, selectedDay) {
        const month = date.getMonth(), year = date.getFullYear();
        const monthNames = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
        const dayNames = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
        const firstDayOfMonth = new Date(year, month, 1).getDay(); const daysInMonth = new Date(year, month + 1, 0).getDate();
        let html = `<h4 class="text-center mb-3">${monthNames[month]} de ${year}</h4>`;
        html += '<table class="table table-bordered text-center table-sm"><thead><tr>' + dayNames.map(d => `<th>${d}</th>`).join('') + '</tr></thead><tbody>';
        let day = 1;
        for (let i = 0; i < 6; i++) {
            html += '<tr>';
            for (let j = 0; j < 7; j++) {
                if ((i === 0 && j < firstDayOfMonth) || day > daysInMonth) { html += '<td></td>'; }
                else {
                    let cellClass = 'calendar-day';
                    if (activitiesForMonth.some(a => a.dueDate && a.dueDate.getDate() === day)) { cellClass += ' has-activity'; if (day === selectedDay) { cellClass += ' selected-day'; } }
                    html += `<td class="${cellClass}">${day++}</td>`;
                }
            } html += '</tr>'; if (day > daysInMonth) break;
        }
        return html + '</tbody></table>';
    }

    updateModalDetails(container, activities) {
         if (!container) return;
        if (!activities || activities.length === 0) { container.innerHTML = '<p class="text-muted text-center">Nenhuma atividade para este dia.</p>'; return; }
        container.innerHTML = activities.map((activity, index) => `
            ${index > 0 ? '<hr class="my-2">' : ''}
            <p class="mb-1"><strong>Atividade:</strong> ${this.view.escapeHtml(activity['ATIVIDADES']) || 'N/A'}</p>
            <div class="d-flex justify-content-between flex-wrap small">
                <span class="me-3"><strong>Responsável:</strong> ${this.view.escapeHtml(activity['RESPONSÁVEL']) || 'N/D'}</span>
                <span class="me-3"><strong>Status:</strong> <span class="badge ${activity.STATUS === 'Concluído' ? 'bg-success' : 'bg-warning text-dark'}">${this.view.escapeHtml(activity.STATUS) || 'N/A'}</span></span>
                <span class="me-3"><strong>Dias Úteis:</strong> ${activity['DIAS ÚTEIS'] !== null && activity['DIAS ÚTEIS'] !== undefined ? activity['DIAS ÚTEIS'] : 'N/A'}</span>
                <span class="me-3"><strong>Tempo Total:</strong> ${this.view.escapeHtml(activity['TEMPO TOTAL']) || 'N/A'}</span>
            </div>
            <p class="mb-0 mt-1 small"><strong>Observação:</strong> ${this.view.escapeHtml(activity['OBSERVAÇÃO']) || 'Nenhuma'}</p>
        `).join('');
    }
}

// --- INICIALIZAÇÃO DA APLICAÇÃO ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM fully loaded. Initializing application...");
    try {
        const model = new DataModel();
        const view = new DashboardView();
        const controller = new AppController(model, view);
        controller.init(); // Inicia o controller
    } catch (error) {
         console.error("Critical error during application initialization:", error);
         document.body.innerHTML = `<div class="alert alert-danger m-5"><h4>Erro Crítico!</h4><p>Falha ao iniciar: ${error.message}. Verifique o console (F12).</p></div>`;
    }
});

