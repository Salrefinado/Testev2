document.addEventListener('DOMContentLoaded', () => {
    
    const board = document.getElementById('workflow-board');
    const fileInput = document.getElementById('zip-upload');
    const btnCriarManual = document.getElementById('btn-criar-manual');

    // Elementos de Busca
    const globalSearchInput = document.getElementById('global-search-input');
    const globalSearchResults = document.getElementById('global-search-results');
    let searchTimeout;

    // Templates
    const grupoTemplate = document.getElementById('grupo-template');
    const rowTemplateStatus = document.getElementById('row-template-status');
    const rowTemplateProducao = document.getElementById('row-template-producao');
    const rowTemplateFinal = document.getElementById('row-template-final');
    const tarefaTemplate = document.getElementById('tarefa-producao-template');

    // Mapeamento de cabeçalhos das tabelas por grupo
    const groupHeaders = {
        'Entrada de Orçamento': ['Orçamento', 'Link', 'Arquivos', 'Status'],
        'Visitas e Medidas': ['Orçamento', 'Link', 'Arquivos', 'Status', 'Data Visita', 'Responsável'],
        'Projetar': ['Orçamento', 'Link', 'Arquivos', 'Status'],
        'Linha de Produção': ['Orçamento', 'Link', 'Arquivos', 'Data Entrada', 'Data Limite', 'Tarefas de Produção'],
        'Prontos': ['Orçamento', 'Link', 'Arquivos', 'Status', 'Itens Prontos', 'Data Pronto', 'Data Instalação', 'Responsável Inst.'],
        'StandBy': ['Orçamento', 'Link', 'Arquivos', 'Status', 'Motivo'],
        'Instalados': ['Orçamento', 'Link', 'Arquivos', 'Status Final']
    };

    // Opções de status para o dropdown de Orçamento
    const statusOptionsByGroup = {
        'Entrada de Orçamento': ['Orçamento Aprovado', 'Agendar Visita', 'Mandar para Produção', 'Standby'],
        'Visitas e Medidas': ['Agendar Visita', 'Visita Agendada', 'Mandar para Produção', 'Standby'],
        'Projetar': ['Em Desenho', 'Aprovado para Produção', 'Desenhar', 'StandBy'],
        'Linha de Produção': ['Não Iniciado', 'Iniciou a Produção', 'Fase de Acabamento', 'Aguardando Vidro / Pedra', 'Reforma em Andamento', 'StandBy'],
        'Prontos': ['Agendar Instalação/Entrega', 'Instalação Agendada', 'Entregue', 'StandBy', 'Instalado'],
        'StandBy': ['Standby', 'Agendar visita', 'Mandar para Produção', 'Instalar'],
        'Instalados': ['Instalado']
    };
    
    // Opções de status para o dropdown de Tarefa
    const statusOptionsTarefa = [
        'Não Iniciado', 
        'Iniciou a Produção', 
        'Fase de Acabamento', 
        'Produção Finalizada', 
        'Aguardando Vidro / Pedra', 
        'Reforma em Andamento', 
        'StandBy'
    ];

    // Elementos do Modal (Principais)
    const modalOverlay = document.getElementById('modal-overlay');
    const modalCriarOrcamento = document.getElementById('modal-criar-orcamento');
    const modalVisita = document.getElementById('modal-visita');
    const modalInstalacao = document.getElementById('modal-instalacao');
    const modalInstalado = document.getElementById('modal-instalado');
    const modalStandby = document.getElementById('modal-standby');
    const modalAddTarefa = document.getElementById('modal-add-tarefa');
    const modalTarefaSave = document.getElementById('modal-tarefa-save');
    const modalTarefaCancel = document.getElementById('modal-tarefa-cancel');
    const modalConfirmarCancelamento = document.getElementById('modal-confirmar-cancelamento');
    const modalAnexarProjeto = document.getElementById('modal-anexar-projeto');

    // Modais de Arquivo
    const modalUploadArquivo = document.getElementById('modal-upload-arquivo');
    const modalFileList = document.getElementById('modal-file-list');
    const modalConfirmarDeleteArquivo = document.getElementById('modal-confirmar-delete-arquivo');

    // Modais de Edição
    const modalDetalhesOrcamento = document.getElementById('modal-detalhes-orcamento');
    const modalEditSimples = document.getElementById('modal-edit-simples');

    // Modal de Movimentação
    const modalConfirmarMovimentacao = document.getElementById('modal-confirmar-movimentacao');
    
    // Variáveis de estado
    let projectFilesToUpload = [];
    let currentUploadOrcamentoId = null;
    let weatherForecastData = {};
    let weatherFetchController = null;
    let openGroupIdOnLoad = null; 
    let dragOverThrottle = null;
    
    // NOVO: Conjunto para armazenar IDs de orçamentos expandidos na Linha de Produção
    let expandedProductionRows = new Set();

    // Elementos do Modal de Criação
    const itemSearchInput = document.getElementById('item-search-input');
    const itemSearchResults = document.getElementById('item-search-results');
    const btnAddItem = document.getElementById('btn-add-item');
    const addedItemsEtapa1List = document.getElementById('added-items-etapa1');
    const addedItemsEtapa2List = document.getElementById('added-items-etapa2');
    const hiddenItemsEtapa1 = document.getElementById('hidden-items-etapa1');
    const hiddenItemsEtapa2 = document.getElementById('hidden-items-etapa2');

    // Lista de itens mestra
    const MASTER_ITEM_LIST = [
        "Coifa", "Coifa Epoxi", "Exaustor", "Chaminé", "Chapéu Aletado", "Chapéu Canhão", "Caixa Braseiro",
        "Porta Guilhotina Vidro L", "Porta Guilhotina Vidro U", "Porta Guilhotina Vidro F",
        "Porta Guilhotina Inox F", "Porta Guilhotina Pedra F",
        "Revestimento Base", "Placa cimenticia Porta", "Isolamento Coifa",
        "Tampa Inox", "Tampa Epoxi", "Revestimento",
        "Sistema de Elevar Manual 2 3/16", "Sistema de Elevar Manual 1/8 e 3/16",
        "Sistema de Elevar Manual Arg. e 3/16", "Sistema de Elevar Manual Arg. e 1/8",
        "Sistema de Elevar Motor 2 3/16", "Sistema de Elevar Motor 1/8 e 3/16",
        "Sistema de Elevar Motor Arg e 3/16", "Sistema de Elevar Motor Arg e 1/8",
        "Giratório 1L 4E", "Giratório 1L 5E", "Giratório 2L 5E", "Giratório 2L 6E",
        "Giratório 2L 7E", "Giratório 2L 8E",
        "Cooktop + Bifeteira", "Cooktop", "Bifeteira grill",
        "Balanço 2", "Balanço 3", "Balanço 4",
        "Kit 6 Espetos", "Regulagem Comum 2", "Regulagem Comum 3", "Regulagem Comum 4", "Regulagem Comum 5",
        "Gavetão Inox", "Gavetão Epóxi", "Moldura Área de fogo", "Grelha de descanso", "Tampa de vidro",
        "KAM600", "KAM700", "KAM800", "KAM900", "KAM1000", "KAM1100", "KAM1200",
        "KAM VITRO", "LYON", "ARGON", "GAB1000",
        "Chaminé inox", "Chaminé Aço Carbono"
    ];

    const ETAPA1_ITEMS = [
        "Coifa", "Coifa Epoxi", "Exaustor", "Chaminé", "Chapéu Aletado", "Chapéu Canhão", "Caixa Braseiro",
        "Porta Guilhotina Vidro L", "Porta Guilhotina Vidro U", "Porta Guilhotina Vidro F",
        "Porta Guilhotina Inox F", "Porta Guilhotina Pedra F",
        "Revestimento Base", "Placa cimenticia Porta", "Isolamento Coifa"
    ];

    function formatTimeAgo(isoDateString) {
        if (!isoDateString) return "";
        const date = new Date(isoDateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        if (seconds < 60) return "Agora mesmo";
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `há ${minutes} min`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return hours === 1 ? "há 1h" : `há ${hours}h`;
        const days = Math.floor(hours / 24);
        if (days < 7) return days === 1 ? "Ontem" : `há ${days} dias`;
        const weeks = Math.floor(days / 7);
        if (weeks <= 4) return weeks === 1 ? "há 1 semana" : `há ${weeks} semanas`;
        const months = Math.floor(days / 30.44); 
        if (months < 12) return months === 1 ? "há 1 mês" : `há ${months} meses`;
        const years = Math.floor(days / 365.25);
        return years === 1 ? "há 1 ano" : `há ${years} anos`;
    }

    function updateTimestamps() {
        const timeElements = document.querySelectorAll('.last-updated-info[data-timestamp]');
        timeElements.forEach(el => {
            const timestamp = el.dataset.timestamp;
            const nome = el.dataset.nome;
            if (timestamp && nome) {
                const timeAgo = formatTimeAgo(timestamp);
                el.textContent = `${nome}: ${timeAgo}`;
            }
        });
    }

    async function loadWorkflow() {
        const groupIdToOpen = openGroupIdOnLoad;
        openGroupIdOnLoad = null; 
        
        // Recupera grupos abertos para manter estado (opcional, mas bom para UX)
        const previouslyOpenGroups = Array.from(document.querySelectorAll('.monday-group:not(.collapsed)'))
            .map(g => g.dataset.groupId);

        try {
            const response = await fetch('/api/workflow');
            if (response.status === 401) {
                window.location.href = '/login?error=Sua sessão expirou.';
                return;
            }
            if (!response.ok) throw new Error('Falha ao carregar workflow');
            
            const grupos = await response.json();
            board.innerHTML = '';
            
            grupos.forEach(grupo => {
                const grupoElement = renderGrupo(grupo);
                const tbody = grupoElement.querySelector('.monday-tbody');
                
                grupo.orcamentos.forEach(orcamento => {
                    const rowElement = renderOrcamentoRow(orcamento);
                    if (rowElement) {
                        tbody.appendChild(rowElement);
                    }
                });
                
                board.appendChild(grupoElement);
            });
            
            initDragAndDrop();
            updateTimestamps(); 

            // Lógica de restauração de estado dos grupos
            if (groupIdToOpen) {
                // Se houve uma ação explicita que requer abrir um grupo
                const groupToOpen = document.querySelector(`.monday-group[data-group-id="${groupIdToOpen}"]`);
                if (groupToOpen) groupToOpen.classList.remove('collapsed');
            } else if (previouslyOpenGroups.length > 0) {
                // Restaura os que estavam abertos
                previouslyOpenGroups.forEach(gid => {
                    const g = document.querySelector(`.monday-group[data-group-id="${gid}"]`);
                    if (g) g.classList.remove('collapsed');
                });
            } else {
                // Padrão: abre o primeiro
                const firstGroup = document.querySelector('.monday-group');
                if (firstGroup) firstGroup.classList.remove('collapsed');
            }

        } catch (error) {
            console.error('Erro ao carregar workflow:', error);
        }
    }

    function renderGrupo(grupo) {
        const clone = grupoTemplate.content.cloneNode(true);
        const grupoSection = clone.querySelector('.monday-group');
        grupoSection.dataset.groupId = grupo.id;
        
        grupoSection.querySelector('.group-title').textContent = grupo.nome;
        
        const thead = clone.querySelector('.monday-thead');
        const headerRow = document.createElement('tr');
        const headers = groupHeaders[grupo.nome] || ['Orçamento', 'Detalhes'];
        
        headers.forEach(text => {
            const th = document.createElement('th');
            th.textContent = text;
            
            if (text === 'Data Limite' && grupo.nome === 'Linha de Produção') {
                th.textContent = 'Data Limite'; 
                const sortBtn = document.createElement('button');
                sortBtn.className = 'btn-sort-date';
                sortBtn.innerHTML = '↕'; 
                sortBtn.title = 'Ordenar por Data Limite';
                sortBtn.dataset.sortDirection = 'asc'; 
                th.appendChild(sortBtn);
            }
            if (text === 'Motivo') th.style.width = '250px';
            if (text === 'Link') {
                th.style.width = '40px';
                th.style.minWidth = '40px';
            }
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        
        return grupoSection;
    }

    function renderOrcamentoRow(orcamento) {
        const grupoNome = orcamento.grupo_nome;
        if (grupoNome === 'Linha de Produção') {
            return renderRowProducao(orcamento);
        } 
        // A condição 'Instalados' foi removida para usar o padrão abaixo
        else if (statusOptionsByGroup[grupoNome]) {
            return renderRowStatus(orcamento); 
        }
        console.warn('Nenhum template de linha encontrado para o grupo:', grupoNome);
        return null;
    }

    function formatarData(dataISO, dateOnly = false) {
        if (!dataISO) return '---';
        try {
            if (dataISO.length === 10 && !dataISO.includes('T')) {
                const [year, month, day] = dataISO.split('-');
                const dataLocal = new Date(year, month - 1, day);
                const dia = String(dataLocal.getDate()).padStart(2, '0');
                const mes = String(dataLocal.getMonth() + 1).padStart(2, '0');
                const ano = dataLocal.getFullYear();
                return `${dia}/${mes}/${ano}`;
            }
            const dataLocal = new Date(dataISO);
            const dia = String(dataLocal.getDate()).padStart(2, '0');
            const mes = String(dataLocal.getMonth() + 1).padStart(2, '0');
            const ano = dataLocal.getFullYear();
            if (dateOnly) return `${dia}/${mes}/${ano}`;
            const hora = String(dataLocal.getHours()).padStart(2, '0');
            const min = String(dataLocal.getMinutes()).padStart(2, '0');
            return `${dia}/${mes}/${ano} ${hora}:${min}`;
        } catch (e) {
            console.warn("Erro ao formatar data:", dataISO, e);
            if (typeof dataISO === 'string' && dataISO.length >= 10) {
                 return dataISO.substring(0, 10).split('-').reverse().join('/');
            }
            return 'Data inválida';
        }
    }
    
    function renderArquivosCell(arquivos, orcamentoId) {
        const td = document.createElement('td');
        td.className = 'col-arquivos';
        const button = document.createElement('button');
        button.className = 'file-pdf-icon-button';
        button.style.backgroundImage = `url('/static/pdf.png')`; 
        button.dataset.orcamentoId = orcamentoId;
        button.dataset.arquivos = JSON.stringify(arquivos); 
        if (arquivos.length > 0) {
            button.classList.add('has-files');
            button.title = `${arquivos.length} arquivo(s) anexado(s). Clique para ver.`;
        } else {
            button.title = 'Nenhum arquivo anexado. Clique para adicionar.';
        }
        button.dataset.action = 'open-file-list';
        td.appendChild(button);
        return td;
    }

    function renderPublicLinkCell(orcamento, row) {
        const td = row.querySelector('.col-public-link');
        const publicLinkEl = td.querySelector('.public-link-icon');
        if (orcamento.public_id) {
            publicLinkEl.href = `/track/${orcamento.public_id}`;
            publicLinkEl.style.display = 'inline-block';
        } else {
            publicLinkEl.style.display = 'none';
        }
        return td;
    }
    
    function renderOrcamentoCell(orcamento, row) {
        const td = row.querySelector('.col-orcamento');
        const wrapper = td.querySelector('.editable-cell-wrapper');
        wrapper.dataset.orcamentoId = orcamento.id; 
        wrapper.querySelector('.orc-numero').textContent = orcamento.numero;
        wrapper.querySelector('.orc-cliente').textContent = orcamento.cliente;

        const lastUpdatedEl = wrapper.querySelector('.last-updated-info');
        if (orcamento.last_updated_at && orcamento.last_updated_by_nome) {
            lastUpdatedEl.dataset.timestamp = orcamento.last_updated_at;
            lastUpdatedEl.dataset.nome = orcamento.last_updated_by_nome;
            lastUpdatedEl.textContent = `${orcamento.last_updated_by_nome}: ...`; 
        } else {
            lastUpdatedEl.textContent = '';
        }
        
        const standbyInfoEl = wrapper.querySelector('.standby-info-icon');
        if (orcamento.grupo_nome === 'StandBy' && orcamento.standby_details) {
            standbyInfoEl.title = `Motivo: ${orcamento.standby_details}`;
            standbyInfoEl.style.display = 'inline';
        } else {
            standbyInfoEl.style.display = 'none';
        }
        return td;
    }

    function renderStatusCell(orcamento) {
        const clone = rowTemplateStatus.content.querySelector('.col-status').cloneNode(true);
        const statusSelector = clone.querySelector('.status-selector');
        const options = statusOptionsByGroup[orcamento.grupo_nome] || [];
        const currentStatus = orcamento.status_atual;
        populateStatusSelector(statusSelector, options, currentStatus);
        return clone;
    }
    
    function populateStatusSelector(selectorElement, optionsList, currentStatus) {
        const display = selectorElement.querySelector('.status-display');
        const dropdown = selectorElement.querySelector('.status-dropdown');
        display.textContent = currentStatus || 'Selecione';
        display.dataset.statusValue = currentStatus || '';
        dropdown.innerHTML = ''; 
        optionsList.forEach(optValue => {
            const option = document.createElement('div');
            option.className = 'status-option';
            option.dataset.value = optValue;
            option.dataset.action = 'select-status-option'; 
            option.textContent = optValue;
            if (optValue === currentStatus) {
                option.classList.add('selected');
            }
            dropdown.appendChild(option);
        });
    }

    function renderDataCell(texto, isDateColumn = false, isLongText = false, editAction = null) {
         const td = document.createElement('td');
         const textoFormatado = texto || '---';
         if (editAction) {
             const span = document.createElement('span');
             span.className = 'editable-cell';
             span.dataset.action = editAction;
             span.textContent = textoFormatado;
             td.appendChild(span);
         } else {
             td.textContent = textoFormatado;
         }
         if (isLongText) {
            td.className = 'col-data-long-text';
         } else {
            td.className = isDateColumn ? 'col-data-date' : 'col-data';
         }
         return td;
    }
    
    function renderStandbyCell(orcamento) {
        const td = document.createElement('td');
        td.className = 'col-data-long-text';
        const span = document.createElement('span');
        span.className = 'editable-cell';
        span.dataset.action = 'edit-standby_details';
        span.textContent = orcamento.standby_details || '---';
        td.appendChild(span);
        return td;
    }

    // NOVA FUNÇÃO: Renderiza botão "Agendar" ou a data da visita (Igual ao Prontos)
    function renderVisitaCell(orcamento) {
        const td = document.createElement('td');
        td.className = 'col-data-date'; 
        
        if (orcamento.data_visita_agendada) {
            const span = document.createElement('span');
            span.className = 'editable-cell';
            span.dataset.action = 'edit-data_visita';
            span.textContent = formatarData(orcamento.data_visita_agendada);
            td.appendChild(span);
        } else {
            const button = document.createElement('button');
            button.className = 'btn-agendar';
            button.textContent = 'Agendar';
            button.dataset.orcamentoId = orcamento.id;
            button.dataset.action = 'agendar-visita';
            td.appendChild(button);
        }
        return td;
    }

    function renderInstalacaoCell(orcamento) {
        const td = document.createElement('td');
        td.className = 'col-data';
        if (orcamento.data_instalacao_agendada) { 
            const span = document.createElement('span');
            span.className = 'editable-cell';
            span.dataset.action = 'edit-data_instalacao'; 
            span.textContent = formatarData(orcamento.data_instalacao_agendada); 
            td.appendChild(span);
        } else {
            const button = document.createElement('button');
            button.className = 'btn-agendar';
            button.textContent = 'Agendar';
            button.dataset.orcamentoId = orcamento.id;
            button.dataset.action = 'agendar-instalacao'; 
            td.appendChild(button);
        }
        return td;
    }

    function renderRowStatus(orcamento) {
        const clone = rowTemplateStatus.content.cloneNode(true);
        const row = clone.querySelector('tr');
        row.dataset.orcamentoId = orcamento.id;
        row.dataset.etapaConcluida = orcamento.etapa_concluida; 
        row.dataset.dataVisita = orcamento.data_visita_agendada || ''; 
        row.dataset.dataInstalacao = orcamento.data_instalacao_agendada || '';
        row.dataset.standbyDetails = orcamento.standby_details || '';

        const orcamentoCell = row.querySelector('.col-orcamento');
        const linkCell = row.querySelector('.col-public-link'); 
        row.innerHTML = ''; 
        row.appendChild(orcamentoCell); 
        row.appendChild(linkCell); 
        
        renderOrcamentoCell(orcamento, row);
        renderPublicLinkCell(orcamento, row);
        
        row.appendChild(renderArquivosCell(orcamento.arquivos, orcamento.id));
        const statusCell = renderStatusCell(orcamento);
        row.appendChild(statusCell);
        
        if (orcamento.grupo_nome === 'Visitas e Medidas') {
            // ALTERADO: Usa renderVisitaCell para mostrar botão ou data
            row.appendChild(renderVisitaCell(orcamento));
            row.appendChild(renderDataCell(
                orcamento.responsavel_visita, 
                false, false, 'edit-responsavel_visita'
            ));
        } else if (orcamento.grupo_nome === 'Prontos') {
             row.appendChild(renderDataCell(
                orcamento.itens_prontos, 
                false, true, 'edit-itens_prontos'
            ));
            row.appendChild(renderDataCell(
                formatarData(orcamento.data_pronto), 
                true, false, 'edit-data_pronto'
            ));
            row.appendChild(renderInstalacaoCell(orcamento));
            row.appendChild(renderDataCell(
                orcamento.responsavel_instalacao, 
                false, false, 'edit-responsavel_instalacao'
            ));
        } else if (orcamento.grupo_nome === 'StandBy') {
            row.appendChild(renderStandbyCell(orcamento));
        }
        return row;
    }
    
    // Renderização específica para Linha de Produção
    function renderRowProducao(orcamento) {
        const clone = rowTemplateProducao.content.cloneNode(true);
        const row = clone.querySelector('tr');
        row.dataset.orcamentoId = orcamento.id;
        
        let dataLimiteProd = null;
        if (orcamento.etapa_concluida == 0) {
            dataLimiteProd = orcamento.data_limite_etapa1;
        } else {
            dataLimiteProd = orcamento.data_limite_etapa2;
        }
        row.dataset.dataLimite = dataLimiteProd || ''; 
        
        renderOrcamentoCell(orcamento, row); 
        row.appendChild(renderPublicLinkCell(orcamento, row));
        row.appendChild(renderArquivosCell(orcamento.arquivos, orcamento.id));
        
        // Data Entrada (Editável)
        row.appendChild(renderDataCell(
            formatarData(orcamento.data_entrada_producao, true), 
            true, false, 'edit-data_entrada_producao'
        ));
        // Data Limite (Editável)
        row.appendChild(renderDataCell(
            formatarData(dataLimiteProd, true), 
            true, false, 'edit-data_limite'
        ));

        // Tarefas (Serviços)
        const tarefasCell = document.createElement('td');
        tarefasCell.className = 'col-tarefas-producao';
        tarefasCell.dataset.tarefas = JSON.stringify(orcamento.tarefas); 
        
        // ATUALIZAÇÃO: Verifica se o orçamento está na lista de expandidos
        if (expandedProductionRows.has(String(orcamento.id))) {
            renderTarefasExpanded(orcamento.tarefas, orcamento.id, tarefasCell);
        } else {
            renderTarefasCompressed(orcamento.tarefas, orcamento.id, tarefasCell);
        }
        
        row.appendChild(tarefasCell);
        return row;
    }

    function renderTarefasCompressed(tarefas, orcamentoId, cell) {
        let hasStarted = tarefas.some(t => t.status !== 'Não Iniciado');
        let aggregateStatus = hasStarted ? 'Em Produção' : 'Não Iniciado';
        
        cell.innerHTML = '';
        const container = document.createElement('div');
        container.className = 'tarefas-compressed';

        const statusButton = document.createElement('button');
        statusButton.className = 'btn-status-expand'; 
        statusButton.textContent = aggregateStatus;
        statusButton.dataset.statusValue = aggregateStatus; 
        statusButton.dataset.action = 'expand';
        
        container.appendChild(statusButton);
        cell.appendChild(container);
    }

    function renderTarefasExpanded(tarefas, orcamentoId, cell) {
        cell.innerHTML = '';
        const expandedContainer = document.createElement('div');
        expandedContainer.className = 'tarefas-expanded';

        const agrupado = tarefas.reduce((acc, tarefa) => {
            if (!acc[tarefa.colaborador]) {
                acc[tarefa.colaborador] = [];
            }
            acc[tarefa.colaborador].push(tarefa);
            return acc;
        }, {});

        for (const colaborador in agrupado) {
            const header = document.createElement('div');
            header.className = 'tarefa-colaborador-header';
            header.innerHTML = `<strong>${colaborador}</strong>`;
            expandedContainer.appendChild(header);
            
            const items = agrupado[colaborador]; 
            const combined_description = items.map(t => t.item_descricao).join(', ');
            
            let representative_status = 'Não Iniciado';
            const statusPriority = statusOptionsTarefa; 
            let currentPriority = -1;
            
            for (const item of items) {
                let priority = statusPriority.indexOf(item.status);
                if (priority > currentPriority) {
                    currentPriority = priority;
                    representative_status = item.status;
                }
            }
            
            const all_tarefa_ids = items.map(t => t.id);
            const virtualTarefa = {
                id: all_tarefa_ids.join(','), 
                item_descricao: combined_description,
                status: representative_status
            };
            
            const tarefaEl = renderTarefa(virtualTarefa);
            expandedContainer.appendChild(tarefaEl);
        }
        
        cell.appendChild(expandedContainer);
        const actionsContainer = document.createElement('div');
        actionsContainer.className = 'tarefas-actions';
        actionsContainer.innerHTML = `
            <button class="btn-toggle-tarefas" data-action="collapse">Recolher</button>
            <button class="btn-add-tarefa" data-action="add-tarefa">+ Adicionar Tarefa</button>
        `;
        cell.appendChild(actionsContainer);
    }
    
    function renderRowFinal(orcamento) {
        const clone = rowTemplateFinal.content.cloneNode(true);
        const row = clone.querySelector('tr');
        row.dataset.orcamentoId = orcamento.id;

        renderOrcamentoCell(orcamento, row);
        row.appendChild(renderPublicLinkCell(orcamento, row));
        row.appendChild(renderArquivosCell(orcamento.arquivos, orcamento.id));
        
        return row;
    }

    function renderTarefa(tarefa) {
        const clone = tarefaTemplate.content.cloneNode(true);
        const tarefaDiv = clone.querySelector('.tarefa-producao');
        
        tarefaDiv.dataset.tarefaIds = tarefa.id; 
        
        tarefaDiv.querySelector('.tarefa-item').textContent = tarefa.item_descricao;
        
        const statusSelector = tarefaDiv.querySelector('.status-selector');
        populateStatusSelector(statusSelector, statusOptionsTarefa, tarefa.status);
        
        return tarefaDiv;
    }
    
    async function handleUpload() {
        const file = fileInput.files[0];
        if (!file) return alert('Por favor, selecione um arquivo .zip.');
        const formData = new FormData();
        formData.append('file', file);
        try {
            const response = await fetch('/api/upload', { method: 'POST', body: formData });
            if (response.status === 401) { window.location.href = '/login'; return; }
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            await loadWorkflow();
            fileInput.value = ''; 
        } catch (error) {
            console.error('Erro no upload:', error);
            alert(`Erro no upload: ${error.message}`);
        }
    }
    
    function toInputDate(date) {
        const offset = date.getTimezoneOffset();
        const localDate = new Date(date.getTime() - (offset*60*1000));
        return localDate.toISOString().split('T')[0];
    }
    
    function parseInputDate(dateStr) {
        if (!dateStr) return null;
        if (dateStr.includes(' ')) {
            dateStr = dateStr.split(' ')[0].split('/').reverse().join('-');
        }
        const [year, month, day] = dateStr.split('-');
        return new Date(year, month - 1, day);
    }

    function parseInputDateTime(dateTimeStr) {
        if (!dateTimeStr) return null;
        if (dateTimeStr.includes('/')) {
            const [datePart, timePart] = dateTimeStr.split(' ');
            const [day, month, year] = datePart.split('/');
            const [hour, minute] = timePart.split(':');
            return new Date(year, month - 1, day, hour, minute);
        }
        return new Date(dateTimeStr);
    }

    function toInputDateTime(date) {
        if (!date) return "";
        const offset = date.getTimezoneOffset();
        const localDate = new Date(date.getTime() - (offset*60*1000));
        return localDate.toISOString().slice(0, 16); 
    }
    
    function showModal(modal) {
        modalOverlay.classList.remove('hidden');
        modal.classList.remove('hidden');
    }
    
    function hideModals() {
        modalOverlay.classList.add('hidden');
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.add('hidden');
        });
        document.getElementById('form-criar-manual').reset();
        const fileUploadText = document.getElementById('file-upload-text');
        const fileUploadLabel = fileUploadText.closest('label');
        if (fileUploadText) fileUploadText.textContent = 'Escolher arquivo...';
        if (fileUploadLabel) fileUploadLabel.classList.remove('file-selected');
        addedItemsEtapa1List.innerHTML = '';
        addedItemsEtapa2List.innerHTML = '';
        hiddenItemsEtapa1.value = '[]';
        hiddenItemsEtapa2.value = '[]';
        itemSearchInput.value = '';
        itemSearchResults.innerHTML = '';
        itemSearchResults.classList.add('hidden');
        document.getElementById('modal-criar-etapa1-finalizada').value = '';
        modalCriarOrcamento.querySelectorAll('.btn-item-select.selected').forEach(btn => {
            btn.classList.remove('selected');
        });
        // Reset visual state for Etapa 1 buttons (in case it was disabled)
        const etapa1Wrapper = document.getElementById('etapa1-finalizada-wrapper');
        if(etapa1Wrapper) {
            etapa1Wrapper.style.opacity = '1';
            etapa1Wrapper.style.pointerEvents = 'auto';
        }
        
        document.getElementById('form-detalhes-orcamento').reset();
        document.getElementById('form-edit-simples').reset();
        document.getElementById('modal-standby-motivo').value = '';
        document.getElementById('modal-tarefa-item').value = '';
        document.querySelectorAll('#modal-tarefa-colaborador-list .btn-item-select.selected').forEach(btn => {
            btn.classList.remove('selected');
        });
        document.getElementById('modal-projeto-arquivo').value = ''; 
        document.getElementById('modal-projeto-file-list').innerHTML = ''; 
        document.getElementById('modal-projeto-data-visita').value = ''; 
        projectFilesToUpload = []; 
        document.getElementById('modal-confirmar-movimentacao').classList.add('hidden');
        document.getElementById('modal-upload-arquivo-input').value = '';
        document.getElementById('modal-upload-file-list').innerHTML = '';
        document.getElementById('file-list-modal-body').innerHTML = '';
        document.getElementById('modal-file-list-input').value = '';
        document.getElementById('modal-file-list-preview').innerHTML = '';
        currentUploadOrcamentoId = null;
        document.getElementById('modal-visita-weather').classList.add('hidden');
        document.getElementById('modal-instalacao-weather').classList.add('hidden');
        document.getElementById('modal-visita-data').removeEventListener('input', handleWeatherCheck);
        document.getElementById('modal-instalacao-data').removeEventListener('input', handleWeatherCheck);
        if (weatherFetchController) weatherFetchController.abort();
        weatherForecastData = {};
    }

    function formatarTelefone(event) {
        const input = event.target;
        let valor = input.value.replace(/\D/g, ''); 
        valor = valor.substring(0, 11); 
        if (valor.length > 10) {
            valor = valor.replace(/^(\d{2})(\d{5})(\d{4}).*/, '($1) $2-$3');
        } else if (valor.length > 6) {
            valor = valor.replace(/^(\d{2})(\d{4})(\d{0,4}).*/, '($1) $2-$3');
        } else if (valor.length > 2) {
            valor = valor.replace(/^(\d{2})(\d{0,5}).*/, '($1) $2');
        } else if (valor.length > 0) {
            valor = valor.replace(/^(\d*)/, '($1');
        }
        input.value = valor;
    }

    function debounceSearch(func, delay) {
        let timeout;
        return function(...args) {
            const context = this;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), delay);
        };
    }

    function handleItemSearch() {
        const query = itemSearchInput.value.toLowerCase().trim();
        itemSearchResults.innerHTML = '';
        if (query.length === 0) {
            itemSearchResults.classList.add('hidden');
            return;
        }
        const filteredItems = MASTER_ITEM_LIST.filter(item => 
            item.toLowerCase().includes(query)
        );
        if (filteredItems.length > 0) {
            filteredItems.forEach(item => {
                const div = document.createElement('div');
                div.className = 'search-result-item-modal';
                const isEtapa1 = ETAPA1_ITEMS.includes(item);
                const etapaHint = isEtapa1 ? "Etapa 1" : "Etapa 2";
                div.innerHTML = `<strong>${item}</strong> <span>(${etapaHint})</span>`;
                div.dataset.item = item;
                div.onclick = () => {
                    itemSearchInput.value = item; 
                    itemSearchResults.classList.add('hidden'); 
                    itemSearchInput.focus();
                };
                itemSearchResults.appendChild(div);
            });
            itemSearchResults.classList.remove('hidden');
        } else {
            itemSearchResults.classList.add('hidden');
        }
    }
    
    function handleAddItem() {
        const itemText = itemSearchInput.value.trim();
        if (!itemText) return;
        const allAddedItems = [
            ...Array.from(addedItemsEtapa1List.querySelectorAll('li')),
            ...Array.from(addedItemsEtapa2List.querySelectorAll('li'))
        ];
        const isDuplicate = allAddedItems.some(li => li.dataset.item.toLowerCase() === itemText.toLowerCase());
        if (isDuplicate) {
            alert('Este item já foi adicionado.');
            return;
        }
        let targetList;
        const masterItemMatch = MASTER_ITEM_LIST.find(masterItem => masterItem.toLowerCase() === itemText.toLowerCase());
        if (masterItemMatch) {
            if (ETAPA1_ITEMS.includes(masterItemMatch)) {
                targetList = addedItemsEtapa1List;
            } else {
                targetList = addedItemsEtapa2List;
            }
        } else {
            targetList = addedItemsEtapa1List;
        }
        const li = document.createElement('li');
        li.dataset.item = itemText;
        li.textContent = itemText;
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.textContent = 'x';
        removeBtn.className = 'btn-remove-added-item';
        removeBtn.onclick = () => {
            li.remove();
            updateHiddenItemInputs();
        };
        li.appendChild(removeBtn);
        targetList.appendChild(li);
        updateHiddenItemInputs(); 
        itemSearchInput.value = '';
        itemSearchResults.innerHTML = '';
        itemSearchResults.classList.add('hidden');
        itemSearchInput.focus();
    }
    
    function updateHiddenItemInputs() {
        const items1 = Array.from(addedItemsEtapa1List.querySelectorAll('li')).map(li => li.dataset.item);
        const items2 = Array.from(addedItemsEtapa2List.querySelectorAll('li')).map(li => li.dataset.item);
        hiddenItemsEtapa1.value = JSON.stringify(items1);
        hiddenItemsEtapa2.value = JSON.stringify(items2);
    }

    function openCriarModal() {
        return new Promise((resolve, reject) => {
            showModal(modalCriarOrcamento);
            hideModals(); 
            showModal(modalCriarOrcamento); 
            document.getElementById('modal-criar-cancel').onclick = () => {
                hideModals(); reject(new Error('Cancelado pelo usuário'));
            };
            const etapaHiddenInput = document.getElementById('modal-criar-etapa1-finalizada');
            const etapaBtnGroup = document.getElementById('etapa1-finalizada-group');
            etapaBtnGroup.querySelectorAll('.btn-item-select.selected').forEach(btn => {
                btn.classList.remove('selected');
            });
            etapaBtnGroup.querySelectorAll('.btn-item-select').forEach(btn => {
                btn.onclick = () => {
                    etapaBtnGroup.querySelector('.btn-item-select.selected')?.classList.remove('selected');
                    btn.classList.add('selected');
                    etapaHiddenInput.value = btn.dataset.value;
                };
            });
            
            // --- NOVA LÓGICA: Monitora Prazo Etapa 2 para desabilitar "Etapa 1 Finalizada?" ---
            const prazo2Input = document.getElementById('modal-criar-prazo-dias2');
            const etapa1Wrapper = document.getElementById('etapa1-finalizada-wrapper');

            prazo2Input.addEventListener('input', function() {
                const val = parseInt(this.value);
                if (!isNaN(val) && val === 0) {
                    // Se for 0, desabilita e limpa
                    etapa1Wrapper.style.opacity = '0.5';
                    etapa1Wrapper.style.pointerEvents = 'none';
                    etapaBtnGroup.querySelectorAll('.btn-item-select.selected').forEach(btn => btn.classList.remove('selected'));
                    etapaHiddenInput.value = ''; 
                } else {
                    // Se for > 0 ou vazio, habilita
                    etapa1Wrapper.style.opacity = '1';
                    etapa1Wrapper.style.pointerEvents = 'auto';
                }
            });
            // -----------------------------------------------------------------------------------

            modalCriarOrcamento.querySelectorAll('.btn-quick-day').forEach(btn => {
                btn.onclick = () => {
                    const dias = btn.dataset.dias;
                    const targetInputId = btn.dataset.diasTarget; 
                    const targetInput = document.getElementById(targetInputId);
                    if (targetInput) {
                        targetInput.value = dias;
                        // Dispara o evento input para atualizar a lógica acima se for o input da etapa 2
                        targetInput.dispatchEvent(new Event('input'));
                    }
                };
            });
            itemSearchInput.addEventListener('input', debounceSearch(handleItemSearch, 200));
            btnAddItem.addEventListener('click', handleAddItem);
            itemSearchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault(); 
                    const firstResult = itemSearchResults.querySelector('.search-result-item-modal');
                    if (firstResult && !itemSearchResults.classList.contains('hidden')) {
                        itemSearchInput.value = firstResult.dataset.item;
                        itemSearchResults.classList.add('hidden');
                    }
                    handleAddItem(); 
                }
            });
            document.addEventListener('click', (e) => {
                if (!e.target.closest('.item-search-container')) {
                    itemSearchResults.classList.add('hidden');
                }
            });
            document.getElementById('modal-criar-numero-cliente').addEventListener('input', formatarTelefone);
            document.getElementById('modal-criar-outro-numero').addEventListener('input', formatarTelefone);
            const fileInput = document.getElementById('modal-criar-arquivo');
            const fileUploadText = document.getElementById('file-upload-text');
            const fileUploadLabel = fileUploadText.closest('label');
            fileInput.addEventListener('change', () => {
                if (fileInput.files.length > 0) {
                    fileUploadText.textContent = fileInput.files[0].name;
                    fileUploadLabel.classList.add('file-selected');
                } else {
                    fileUploadText.textContent = 'Escolher arquivo...';
                    fileUploadLabel.classList.remove('file-selected');
                }
            });
        });
    }

    async function handleCriarManualSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        const arquivo = formData.get('arquivo');
        if (!arquivo || arquivo.size === 0) {
            alert('O anexo de arquivo é obrigatório.');
            return;
        }
        const etapaFinalizada = formData.get('etapa1_finalizada');
        if (!formData.get('numero_orcamento') || !formData.get('nome_cliente')) {
            alert('Número do Orçamento e Nome do Cliente são obrigatórios.'); return;
        }
        if (!formData.get('prazo_dias_etapa1') || formData.get('prazo_dias_etapa2') === "") {
            alert('Os Prazos (em dias) da Etapa 1 e Etapa 2 são obrigatórios.'); return;
        }
        
        // --- ATUALIZAÇÃO VALIDAÇÃO: Só exige "Etapa 1 Finalizada" se Prazo 2 > 0 ---
        const prazo2 = parseInt(formData.get('prazo_dias_etapa2'));
        if (prazo2 > 0 && !etapaFinalizada) {
            alert('Por favor, selecione se a Etapa 1 já foi finalizada (Sim ou Não).'); return;
        }
        // ---------------------------------------------------------------------------

        try {
            const response = await fetch('/api/orcamento/create_manual', { method: 'POST', body: formData });
            if (response.status === 401) { window.location.href = '/login'; return; }
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            hideModals();
            await loadWorkflow();
        } catch (error) {
            console.error('Erro ao criar orçamento:', error);
            alert(`Erro ao salvar: ${error.message}`);
        }
    }

    function debounce(func, delay) {
        let timeout;
        return function(...args) {
            const context = this;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), delay);
        };
    }

    async function fetchWeather(orcamentoId) {
        if (weatherForecastData[orcamentoId] && weatherForecastData[orcamentoId] !== 'loading') {
            return weatherForecastData[orcamentoId];
        }
        if (weatherForecastData[orcamentoId] === 'loading') return null;
        weatherForecastData[orcamentoId] = 'loading';
        if (weatherFetchController) weatherFetchController.abort();
        weatherFetchController = new AbortController();
        const signal = weatherFetchController.signal;
        try {
            const response = await fetch(`/api/previsao/orcamento/${orcamentoId}`, { signal });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Erro de rede');
            }
            const data = await response.json();
            weatherForecastData[orcamentoId] = data;
            return data;
        } catch (error) {
            if (error.name === 'AbortError') return null;
            console.error("Erro ao buscar previsão:", error.message);
            weatherForecastData[orcamentoId] = { error: error.message };
            return weatherForecastData[orcamentoId];
        }
    }

    async function checkWeatherForecast(orcamentoId, dateInputEl, weatherDisplayEl) {
        const selectedDateTime = dateInputEl.value;
        const weatherIconEl = weatherDisplayEl.querySelector('.weather-icon');
        const weatherTextEl = weatherDisplayEl.querySelector('.weather-text');
        if (!selectedDateTime || !selectedDateTime.includes('T')) {
            weatherDisplayEl.classList.add('hidden');
            weatherDisplayEl.classList.remove('bad-weather');
            weatherTextEl.textContent = '';
            return;
        }
        weatherDisplayEl.classList.remove('hidden');
        weatherDisplayEl.classList.remove('bad-weather');
        weatherIconEl.textContent = '🔄';
        weatherTextEl.textContent = 'Verificando previsão...';
        const forecastData = await fetchWeather(orcamentoId);
        if (!forecastData || forecastData === 'loading') {
            if (forecastData !== 'loading') weatherTextEl.textContent = '...';
            return; 
        }
        if (forecastData.error) {
            weatherDisplayEl.classList.add('bad-weather');
            weatherIconEl.textContent = '⚠️';
            weatherTextEl.textContent = forecastData.error;
            return;
        }
        const locationName = forecastData.location_name || "Local";
        const forecastDays = forecastData.forecast_days || [];
        const [selectedDate, selectedTime] = selectedDateTime.split('T');
        const selectedHour = parseInt(selectedTime.split(':')[0]);
        const dayData = forecastDays.find(day => day.date === selectedDate);
        if (!dayData) {
            weatherDisplayEl.classList.remove('bad-weather');
            weatherIconEl.textContent = 'ℹ️';
            weatherTextEl.textContent = 'Sem previsão disponível para esta data.';
            return;
        }
        const relevantHours = dayData.hour.filter(h => {
            const hour = new Date(h.time).getHours();
            return hour >= selectedHour && hour <= 18;
        });
        const rainyHours = relevantHours.filter(h => h.will_it_rain === 1);
        if (rainyHours.length > 0) {
            const firstRainHour = new Date(rainyHours[0].time).getHours();
            const lastRainHour = new Date(rainyHours[rainyHours.length - 1].time).getHours();
            const horaInicioStr = `${String(firstRainHour).padStart(2, '0')}:00`;
            const horaFimStr = `${String(lastRainHour + 1).padStart(2, '0')}:00`;
            weatherDisplayEl.classList.add('bad-weather');
            weatherIconEl.textContent = '🌧️';
            weatherTextEl.textContent = `Atenção: Previsão de chuva em ${locationName}. ⌚ Horário: Das ${horaInicioStr} às ${horaFimStr}.`;
        } else {
            weatherDisplayEl.classList.remove('bad-weather');
            weatherIconEl.textContent = '☀️';
            weatherTextEl.textContent = `Tempo firme previsto em ${locationName}.`;
        }
    }
    const debouncedWeatherCheck = debounce(checkWeatherForecast, 500);
    function handleWeatherCheck(event) {
        const dateInputEl = event.target;
        const modal = dateInputEl.closest('.modal');
        const orcamentoId = modal.dataset.orcamentoId;
        let weatherDisplayEl;
        if (modal.id === 'modal-visita') {
            weatherDisplayEl = document.getElementById('modal-visita-weather');
        } else if (modal.id === 'modal-instalacao') {
            weatherDisplayEl = document.getElementById('modal-instalacao-weather');
        }
        if (orcamentoId && weatherDisplayEl) {
            debouncedWeatherCheck(orcamentoId, dateInputEl, weatherDisplayEl);
        }
    }

    function openVisitaModal(orcamentoId, dataVisita = '', responsavelVisita = '') {
        return new Promise((resolve, reject) => {
            modalVisita.dataset.orcamentoId = orcamentoId;
            showModal(modalVisita);
            const dataInput = document.getElementById('modal-visita-data');
            const respInput = document.getElementById('modal-visita-responsavel');
            dataInput.value = dataVisita ? toInputDateTime(parseInputDateTime(dataVisita)) : '';
            respInput.value = responsavelVisita || '';
            modalVisita.querySelectorAll('.modal-quick-days button[data-name]').forEach(btn => {
                btn.onclick = () => { respInput.value = btn.dataset.name; };
            });
            modalVisita.querySelectorAll('.modal-quick-days button[data-time]').forEach(btn => {
                btn.onclick = () => { setDateTimeTime(dataInput, btn.dataset.time); };
            });
            dataInput.addEventListener('input', handleWeatherCheck);
            if (dataInput.value) dataInput.dispatchEvent(new Event('input'));
            document.getElementById('modal-visita-save').onclick = () => {
                const data = {
                    data_visita: dataInput.value,
                    responsavel_visita: respInput.value
                };
                if (!data.data_visita || !data.responsavel_visita) {
                    return alert('Por favor, preencha a data e o responsável.');
                }
                hideModals();
                resolve(data);
            };
            document.getElementById('modal-visita-cancel').onclick = () => {
                hideModals();
                reject(new Error('Cancelado pelo usuário'));
            };
        });
    }

    function openInstalacaoModal(orcamentoId, etapaConcluida = '0', dataInstalacao = '', responsavelInstalacao = '') {
         return new Promise((resolve, reject) => {
            modalInstalacao.dataset.orcamentoId = orcamentoId;
            showModal(modalInstalacao);
            const dataInput = document.getElementById('modal-instalacao-data');
            const respInput = document.getElementById('modal-instalacao-responsavel');
            dataInput.value = dataInstalacao ? toInputDateTime(parseInputDateTime(dataInstalacao)) : '';
            respInput.value = responsavelInstalacao || '';
            if (!respInput.value) respInput.value = (etapaConcluida == '0') ? 'Renato' : 'Paulo';
            modalInstalacao.querySelectorAll('.modal-quick-days button[data-time]').forEach(btn => {
                btn.onclick = () => { setDateTimeTime(dataInput, btn.dataset.time); };
            });
            dataInput.addEventListener('input', handleWeatherCheck);
            if (dataInput.value) dataInput.dispatchEvent(new Event('input'));
            document.getElementById('modal-instalacao-save').onclick = () => {
                const data = {
                    data_instalacao: dataInput.value,
                    responsavel_instalacao: respInput.value
                };
                 if (!data.data_instalacao || !data.responsavel_instalacao) {
                    return alert('Por favor, preencha a data e o responsável.');
                }
                hideModals();
                resolve(data);
            };
            document.getElementById('modal-instalacao-cancel').onclick = () => {
                hideModals();
                reject(new Error('Cancelado pelo usuário'));
            };
        });
    }
    
    function openInstaladoModal() {
        return new Promise((resolve, reject) => {
            showModal(modalInstalado);
            document.getElementById('modal-instalado-etapa1').onclick = () => {
                hideModals(); resolve({ etapa_instalada: 'Etapa 1' });
            };
            document.getElementById('modal-instalado-etapa2').onclick = () => {
                hideModals(); resolve({ etapa_instalada: 'Etapa 2' });
            };
            document.getElementById('modal-instalado-cancel').onclick = () => {
                hideModals(); reject(new Error('Cancelado pelo usuário'));
            };
        });
    }
    
    function openStandbyModal(motivoAtual = '') {
        return new Promise((resolve, reject) => {
            showModal(modalStandby);
            const motivoInput = document.getElementById('modal-standby-motivo');
            motivoInput.value = motivoAtual || ''; 
            document.getElementById('modal-standby-save').onclick = () => {
                const motivo = motivoInput.value;
                if (!motivo) return alert('Por favor, informe o motivo.');
                hideModals();
                resolve({ standby_details: motivo });
            };
            document.getElementById('modal-standby-cancel').onclick = () => {
                hideModals();
                reject(new Error('Cancelado pelo usuário'));
            };
        });
    }

    function openConfirmarCancelamentoModal(tipo) {
        return new Promise((resolve) => { 
            const texto = document.getElementById('modal-confirmar-texto');
            if (tipo === 'visita') {
                texto.textContent = 'Já existe uma visita agendada. Deseja cancelá-la?';
            } else if (tipo === 'instalacao') {
                texto.textContent = 'Já existe uma instalação agendada. Deseja cancelá-la?';
            } else {
                texto.textContent = 'Deseja realmente cancelar o agendamento atual?';
            }
            showModal(modalConfirmarCancelamento);
            document.getElementById('modal-confirmar-save').onclick = () => {
                hideModals(); resolve(true); 
            };
            document.getElementById('modal-confirmar-cancel').onclick = () => {
                hideModals(); resolve(false); 
            };
        });
    }

    function openConfirmarMovimentacaoModal(grupoAntigoNome, grupoNovoNome) {
        return new Promise((resolve) => {
            const texto = document.getElementById('modal-confirmar-movimentacao-texto');
            texto.innerHTML = `Tem certeza que deseja mover o item de <strong>${grupoAntigoNome}</strong> para <strong>${grupoNovoNome}</strong>?`;
            showModal(modalConfirmarMovimentacao);
            document.getElementById('modal-confirmar-movimentacao-save').onclick = () => {
                hideModals(); 
                resolve(true); 
            };
            document.getElementById('modal-confirmar-movimentacao-cancel').onclick = () => {
                hideModals(); 
                resolve(false); 
            };
        });
    }

    function openUploadModal(orcamentoId) {
        currentUploadOrcamentoId = orcamentoId;
        projectFilesToUpload = [];
        document.getElementById('modal-upload-file-list').innerHTML = ''; 
        showModal(modalUploadArquivo);
    }
    function openFileListModal(orcamentoId, arquivosJson) {
        currentUploadOrcamentoId = orcamentoId;
        projectFilesToUpload = [];
        const arquivos = JSON.parse(arquivosJson);
        const listBody = document.getElementById('file-list-modal-body');
        listBody.innerHTML = '';
        if (arquivos.length === 0) {
            listBody.innerHTML = '<li>Nenhum arquivo encontrado.</li>';
        } else {
            arquivos.forEach(arquivo => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <a href="${arquivo.url}" target="_blank">${arquivo.nome_arquivo}</a>
                    <button class="btn-remove-manual-item" data-arquivo-id="${arquivo.id}" data-arquivo-nome="${arquivo.nome_arquivo}" data-orcamento-id="${orcamentoId}">x</button>
                `;
                listBody.appendChild(li);
            });
        }
        document.getElementById('modal-file-list-preview').innerHTML = ''; 
        showModal(modalFileList);
    }
    function openConfirmDeleteModal(arquivoId, nomeArquivo, orcamentoId) {
        const saveBtn = document.getElementById('modal-confirmar-delete-save');
        saveBtn.dataset.arquivoId = arquivoId;
        saveBtn.dataset.orcamentoId = orcamentoId;
        const texto = document.getElementById('modal-confirmar-delete-texto');
        texto.textContent = `Tem certeza que deseja excluir o arquivo "${nomeArquivo}"? Esta ação não pode ser desfeita.`;
        modalFileList.classList.add('hidden');
        showModal(modalConfirmarDeleteArquivo);
    }
    async function handleUploadArquivos(orcamentoId, filesArray) {
        if (!filesArray || filesArray.length === 0) return;
        const saveBtnUpload = document.getElementById('modal-upload-save');
        const saveBtnList = document.getElementById('modal-file-list-upload-save');
        if(saveBtnUpload) { saveBtnUpload.textContent = 'Enviando...'; saveBtnUpload.disabled = true; }
        if(saveBtnList) { saveBtnList.textContent = 'Enviando...'; saveBtnList.disabled = true; }
        for (const file of filesArray) {
            const formData = new FormData();
            formData.append('file', file);
            try {
                const response = await fetch(`/api/orcamento/${orcamentoId}/add_file`, { method: 'POST', body: formData });
                if (response.status === 401) { window.location.href = '/login'; return; }
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || `Falha ao enviar ${file.name}`);
            } catch (error) {
                console.error('Erro ao anexar arquivo:', error);
                alert(`Erro ao anexar arquivo ${file.name}: ${error.message}`);
            }
        }
        if(saveBtnUpload) { saveBtnUpload.textContent = 'Anexar Arquivos'; saveBtnUpload.disabled = false; }
        if(saveBtnList) { saveBtnList.textContent = 'Anexar Novos'; saveBtnList.disabled = false; }
        hideModals();
        await loadWorkflow();
    }
    async function handleDeleteArquivo(arquivoId, orcamentoId) {
        if (!arquivoId || !orcamentoId) return;
        try {
            const response = await fetch(`/api/orcamento/${orcamentoId}/delete_file/${arquivoId}`, { method: 'DELETE' });
            if (response.status === 401) { window.location.href = '/login'; return; }
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            hideModals();
            await loadWorkflow();
        } catch (error) {
            console.error('Erro ao deletar arquivo:', error);
            alert(`Erro: ${error.message}`);
            hideModals();
            await loadWorkflow();
        }
    }

    function openAnexarProjetoModal() {
        return new Promise((resolve, reject) => {
            showModal(modalAnexarProjeto);
            projectFilesToUpload = []; 
            const dropZone = document.getElementById('modal-projeto-dropzone');
            const fileInput = document.getElementById('modal-projeto-arquivo');
            const fileList = document.getElementById('modal-projeto-file-list');
            const dataVisitaInput = document.getElementById('modal-projeto-data-visita');
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, e => { e.preventDefault(); e.stopPropagation(); }, false);
            });
            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, () => dropZone.classList.add('drag-over'), false);
            });
            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, () => dropZone.classList.remove('drag-over'), false);
            });
            fileInput.onchange = (e) => handleAddFiles_ProjetoModal(e.target.files);
            dropZone.ondrop = (e) => handleAddFiles_ProjetoModal(e.dataTransfer.files);
            
            function handleAddFiles_ProjetoModal(files) {
                Array.from(files).forEach(file => {
                    projectFilesToUpload.push(file);
                    renderFileList_ProjetoModal();
                });
            }
            function renderFileList_ProjetoModal() {
                fileList.innerHTML = '';
                projectFilesToUpload.forEach((file, index) => {
                    const li = document.createElement('li');
                    li.innerHTML = `
                        <span class="file-name">${file.name}</span>
                        <button type="button" class="file-remove-btn" data-index="${index}">&times;</button>
                    `;
                    fileList.appendChild(li);
                });
            }
            fileList.onclick = (e) => {
                if (e.target.classList.contains('file-remove-btn')) {
                    const index = parseInt(e.target.dataset.index);
                    projectFilesToUpload.splice(index, 1);
                    renderFileList_ProjetoModal();
                }
            };
            document.getElementById('modal-projeto-save').onclick = () => {
                const dataVisita = dataVisitaInput.value;
                if (!dataVisita) {
                    return alert('A "Data da Visita (Obrigatório)" deve ser preenchida.');
                }
                if (projectFilesToUpload.length === 0) {
                    return alert('É obrigatório anexar pelo menos um arquivo de projeto.');
                }
                const data = { files: projectFilesToUpload, data_visita: dataVisita };
                hideModals();
                resolve(data);
            };
            document.getElementById('modal-projeto-cancel').onclick = () => {
                hideModals();
                reject(new Error('Cancelado pelo usuário'));
            };
        });
    }

    function openAddTarefaModal(buttonEl) {
        const orcamentoId = buttonEl.closest('.monday-row').dataset.orcamentoId;
        document.getElementById('modal-tarefa-orcamento-id').value = orcamentoId;
        showModal(modalAddTarefa);
    }
    
    async function handleAddTarefaSubmit() {
        const orcamentoId = document.getElementById('modal-tarefa-orcamento-id').value;
        const selectedBtn = document.querySelector('#modal-tarefa-colaborador-list .btn-item-select.selected');
        const colaborador = selectedBtn ? selectedBtn.dataset.colab : null;
        const item_descricao = document.getElementById('modal-tarefa-item').value;
        if (!colaborador || !item_descricao) {
            return alert('Colaborador e Item são obrigatórios.');
        }
        try {
            const response = await fetch(`/api/orcamento/${orcamentoId}/add_tarefa`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    colaborador: colaborador,
                    item_descricao: item_descricao
                })
            });
            if (response.status === 401) { window.location.href = '/login'; return; }
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            hideModals();
            await loadWorkflow(); 
        } catch (error) {
            console.error('Erro ao adicionar tarefa:', error);
            alert(`Erro: ${error.message}`);
        }
    }

    async function processOrcamentoStatusChange(orcamentoId, novoStatus, etapaConcluida) {
        try {
            let dados_adicionais = {};
            const row = document.querySelector(`tr[data-orcamento-id="${orcamentoId}"]`);
            const currentGroupName = row.closest('.monday-group').querySelector('.group-title').textContent;

            // --- LÓGICA DE FLUXO SIMPLIFICADA ---

            if (currentGroupName === 'Entrada de Orçamento') {
                // Se for "Mandar para Produção", apenas atualiza status (vai para Projetar)
                // SEM pedir modal de arquivos/data.
                if (novoStatus === 'Standby') {
                    dados_adicionais = await openStandbyModal();
                }
            }
            else if (currentGroupName === 'Visitas e Medidas') {
                // Se for "Mandar para Produção", apenas atualiza status (vai para Projetar)
                // Limpa data de visita se existir
                if (novoStatus === 'Mandar para Produção') {
                     if (row.dataset.dataVisita && row.dataset.dataVisita !== 'null') {
                        dados_adicionais.data_visita = null; 
                        dados_adicionais.responsavel_visita = null;
                    }
                }
                else if (novoStatus === 'Agendar Visita') {
                    const dataVisitaAtual = row.dataset.dataVisita;
                    if (dataVisitaAtual && dataVisitaAtual !== 'null') {
                        const confirmed = await openConfirmarCancelamentoModal('visita');
                        if (confirmed) {
                            dados_adicionais.data_visita = null;
                            dados_adicionais.responsavel_visita = null;
                        } else {
                            throw new Error('Cancelado pelo usuário');
                        }
                    }
                }
                else if (novoStatus === 'Visita Agendada') {
                    dados_adicionais = await openVisitaModal(orcamentoId, row.dataset.dataVisita, row.dataset.responsavelVisita);
                }
                else if (novoStatus === 'Standby') {
                    dados_adicionais = await openStandbyModal(row.dataset.standbyDetails);
                }
            }
            else if (currentGroupName === 'Projetar') {
                 // AQUI SIM: Se sair de Projetar para "Aprovado para Produção" (vai para Linha de Produção)
                 // Deve pedir o modal com arquivos e data.
                 if (novoStatus === 'Aprovado para Produção') {
                    const dados_com_arquivos = await openAnexarProjetoModal();
                    await handleUploadArquivos(orcamentoId, dados_com_arquivos.files);
                    dados_adicionais.data_visita = dados_com_arquivos.data_visita;
                }
                else if (novoStatus === 'StandBy') {
                     dados_adicionais = await openStandbyModal(row.dataset.standbyDetails);
                }
            }
            else if (novoStatus === 'Agendar Instalação/Entrega') {
                const dataInstalacaoAtual = row.dataset.dataInstalacao;
                if (dataInstalacaoAtual && dataInstalacaoAtual !== 'null') {
                    const confirmed = await openConfirmarCancelamentoModal('instalacao');
                    if (confirmed) {
                        dados_adicionais.data_instalacao = null;
                        dados_adicionais.responsavel_instalacao = null;
                    } else {
                        throw new Error('Cancelado pelo usuário');
                    }
                }
            }
            else if (novoStatus === 'Instalação Agendada') {
                dados_adicionais = await openInstalacaoModal(orcamentoId, etapaConcluida, row.dataset.dataInstalacao, row.dataset.responsavelInstalacao);
            } else if (novoStatus === 'Instalado' || novoStatus === 'Entregue') {
                dados_adicionais = await openInstaladoModal();
            } else if (novoStatus === 'Standby' || novoStatus === 'StandBy') {
                 if (currentGroupName !== 'Entrada de Orçamento') {
                    dados_adicionais = await openStandbyModal(row.dataset.standbyDetails);
                 }
            }
            await updateStatus(orcamentoId, novoStatus, dados_adicionais);
        } catch (error) {
            if (error.message === 'Cancelado pelo usuário') {
                console.log('Operação cancelada.');
                loadWorkflow(); 
            } else {
                console.error('Erro no fluxo de atualização:', error);
                loadWorkflow(); 
            }
        }
    }
    
    async function processTarefaStatusChange(tarefaIdsString, novoStatus) {
        const tarefaIds = tarefaIdsString.split(',');
        if (!tarefaIds || tarefaIds.length === 0) return;
        
        const firstTarefaId = tarefaIds[0]; 
        try {
            const response = await fetch(`/api/tarefa/${firstTarefaId}/status`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: novoStatus })
            });
            if (response.status === 401) { window.location.href = '/login'; return; }
            const result = await response.json(); 
            if (!response.ok) throw new Error(result.error);
            
            const orcamentoId = result.id;
            const row = document.querySelector(`tr[data-orcamento-id="${orcamentoId}"]`);
            const grupoAntigoId = row.closest('.monday-group').dataset.groupId;
            
            if (result.grupo_id != grupoAntigoId) {
                if(row) row.classList.add('row-moving');
                await new Promise(resolve => setTimeout(resolve, 500)); 
                loadWorkflow();
            } else {
                loadWorkflow(); 
            }
            if (novoStatus === 'StandBy') {
                 await updateStatus(result.id, 'StandBy');
            }
        } catch (error) {
            console.error('Erro ao atualizar status da tarefa:', error);
            loadWorkflow(); 
        }
    }

    async function updateStatus(orcamentoId, novoStatus, dados_adicionais = {}) {
        const row = document.querySelector(`tr[data-orcamento-id="${orcamentoId}"]`);
        let grupoAntigoId = null;
        if (row) {
            grupoAntigoId = row.closest('.monday-group').dataset.groupId;
        }
        try {
            const response = await fetch(`/api/orcamento/${orcamentoId}/status`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    novo_status: novoStatus,
                    dados_adicionais: dados_adicionais 
                })
            });
            if (response.status === 401) { window.location.href = '/login'; return; }
            const result = await response.json(); 
            if (!response.ok) throw new Error(result.error);
            if (row && grupoAntigoId && result.grupo_id != grupoAntigoId) {
                row.classList.add('row-moving');
                await new Promise(resolve => setTimeout(resolve, 500)); 
            }
            await loadWorkflow();
        } catch (error) {
            console.error('Erro ao atualizar status:', error);
            alert(`Erro: ${error.message}`);
            await loadWorkflow();
        }
    }
    
    function handleSortByDate(sortBtn) {
        const tbody = sortBtn.closest('.monday-group').querySelector('.monday-tbody');
        if (!tbody) return;
        const currentDirection = sortBtn.dataset.sortDirection; 
        const newDirection = currentDirection === 'desc' ? 'asc' : 'desc';
        sortBtn.dataset.sortDirection = newDirection;
        if (newDirection === 'desc') {
            sortBtn.innerHTML = '▼'; 
        } else {
            sortBtn.innerHTML = '▲'; 
        }
        const rows = Array.from(tbody.querySelectorAll('.monday-row'));
        rows.sort((rowA, rowB) => {
            const dateStrA = rowA.dataset.dataLimite;
            const dateStrB = rowB.dataset.dataLimite;
            if (!dateStrA && !dateStrB) return 0;
            if (!dateStrA) return 1; 
            if (!dateStrB) return -1; 
            const dateA = new Date(dateStrA + "T00:00:00").getTime();
            const dateB = new Date(dateStrB + "T00:00:00").getTime();
            if (newDirection === 'desc') {
                return dateB - dateA;
            } else {
                return dateA - dateB;
            }
        });
        rows.forEach(row => tbody.appendChild(row));
    }
    
    function handleDragOverGroup(e) {
        if (dragOverThrottle) return;
        dragOverThrottle = setTimeout(() => {
            dragOverThrottle = null;
        }, 200); 
        const title = e.target.closest('.group-title');
        if (title) {
            const group = title.closest('.monday-group');
            if (group && group.classList.contains('collapsed')) {
                // ATUALIZADO: Não fecha mais os outros grupos
                group.classList.remove('collapsed');
            }
        }
    }

    function handleToggleTarefas(buttonEl) {
        const action = buttonEl.dataset.action;
        const cell = buttonEl.closest('.col-tarefas-producao');
        const orcamentoId = buttonEl.closest('.monday-row').dataset.orcamentoId;
        const tarefas = JSON.parse(cell.dataset.tarefas);
        
        if (action === 'expand') {
            // Adiciona ao conjunto de expandidos
            expandedProductionRows.add(String(orcamentoId));
            renderTarefasExpanded(tarefas, orcamentoId, cell);
        } else {
            // Remove do conjunto de expandidos
            expandedProductionRows.delete(String(orcamentoId));
            renderTarefasCompressed(tarefas, orcamentoId, cell);
        }
    }
    
    function handleGroupToggle(e) {
        if (e.target.classList.contains('group-title')) {
            const group = e.target.closest('.monday-group');
            if (group) {
                // ATUALIZADO: Simplesmente alterna a classe 'collapsed'
                // Não fecha mais os outros grupos
                group.classList.toggle('collapsed');
            }
        }
    }

    function closeAllStatusDropdowns(exceptThisOne = null) {
        document.querySelectorAll('.status-selector.active').forEach(selector => {
            if (selector !== exceptThisOne) {
                selector.classList.remove('active');
                const tableWrapper = selector.closest('.table-wrapper');
                if (tableWrapper) tableWrapper.classList.remove('table-wrapper-dropdown-active');
                const parentGroup = selector.closest('.monday-group');
                if (parentGroup) parentGroup.classList.remove('group-z-index-lift');
                const parentRow = selector.closest('.monday-row');
                if (parentRow) parentRow.classList.remove('row-z-index-lift');
            }
        });
    }
    
    function initDragAndDrop() {
        document.removeEventListener('dragover', handleDragOverGroup);
        const tbodys = document.querySelectorAll('.monday-tbody');
        tbodys.forEach(tbody => {
            new Sortable(tbody, {
                group: 'workflow-board',
                animation: 150,
                handle: '.monday-row',
                ghostClass: 'sortable-ghost',
                chosenClass: 'sortable-chosen',
                onStart: function() {
                    document.addEventListener('dragover', handleDragOverGroup);
                },
                onEnd: async (evt) => {
                    document.removeEventListener('dragover', handleDragOverGroup);
                    const orcamentoId = evt.item.dataset.orcamentoId;
                    const novoGrupoId = evt.to.closest('.monday-group').dataset.groupId;
                    const grupoAntigoId = evt.from.closest('.monday-group').dataset.groupId;
                    if (novoGrupoId !== grupoAntigoId) {
                        let dados_adicionais = {};
                        const grupoAntigoNome = evt.from.closest('.monday-group').querySelector('.group-title').textContent;
                        const grupoNovoNome = evt.to.closest('.monday-group').querySelector('.group-title').textContent;
                        const moveConfirmed = await openConfirmarMovimentacaoModal(grupoAntigoNome, grupoNovoNome);
                        if (!moveConfirmed) {
                            loadWorkflow();
                            return;
                        }
                        const dataVisitaAtual = evt.item.dataset.dataVisita;
                        const dataInstalacaoAtual = evt.item.dataset.dataInstalacao;
                        if (dataVisitaAtual && dataVisitaAtual !== 'null') {
                            const confirmed = await openConfirmarCancelamentoModal('visita');
                            if (confirmed) {
                                dados_adicionais.cancel_existing_dates = true;
                            } else {
                                loadWorkflow();
                                return;
                            }
                        } else if (dataInstalacaoAtual && dataInstalacaoAtual !== 'null') {
                             const confirmed = await openConfirmarCancelamentoModal('instalacao');
                            if (confirmed) {
                                dados_adicionais.cancel_existing_dates = true;
                            } else {
                                loadWorkflow();
                                return;
                            }
                        }
                        
                        // Verifica se está entrando em Linha de Produção (de qualquer lugar)
                        // para pedir os dados (arquivos/data)
                        if (grupoNovoNome === 'Linha de Produção') {
                             try {
                                const dados_modal = await openAnexarProjetoModal();
                                await handleUploadArquivos(orcamentoId, dados_modal.files);
                                dados_adicionais.data_visita = dados_modal.data_visita;
                            } catch (e) {
                                console.log('Movimentação cancelada.');
                                loadWorkflow(); 
                                return;
                            }
                        } else if (grupoNovoNome === 'StandBy') {
                             try {
                                const motivo_standby = await openStandbyModal(evt.item.dataset.standbyDetails);
                                dados_adicionais = { ...dados_adicionais, ...motivo_standby };
                            } catch (e) {
                                console.log('Movimentação cancelada.');
                                loadWorkflow();
                                return;
                            }
                        }
                        handleManualMove(orcamentoId, novoGrupoId, grupoAntigoId, dados_adicionais);
                    }
                }
            });
        });
    }
    
    async function handleManualMove(orcamentoId, novoGrupoId, grupoAntigoId, dados_adicionais = {}) {
        const row = document.querySelector(`tr[data-orcamento-id="${orcamentoId}"]`);
        if(row) {
            row.classList.add('row-moving');
            await new Promise(resolve => setTimeout(resolve, 500)); 
        }
        try {
            const body = { 
                novo_grupo_id: novoGrupoId, 
                ...dados_adicionais 
            };
            const response = await fetch(`/api/orcamento/${orcamentoId}/move`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            if (response.status === 401) { window.location.href = '/login'; return; }
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            openGroupIdOnLoad = novoGrupoId;
            await loadWorkflow();
        } catch (error) {
             console.error('Erro ao mover orçamento:', error);
             alert(`Erro ao mover: ${error.message}`);
             loadWorkflow();
        }
    }

    function renderSearchResults(results) {
        globalSearchResults.innerHTML = '';
        if (results.length === 0) {
            globalSearchResults.innerHTML = '<div class="search-result-no-match">Nenhum resultado encontrado.</div>';
        } else {
            results.forEach(result => {
                const item = document.createElement('div');
                item.className = 'search-result-item';
                item.dataset.orcamentoId = result.id;
                item.innerHTML = `<strong>${result.numero} - ${result.cliente}</strong><span>${result.grupo_nome}</span>`;
                globalSearchResults.appendChild(item);
            });
        }
        globalSearchResults.classList.remove('hidden');
    }

    async function performSearch(query) {
        if (query.length < 2) {
            globalSearchResults.classList.add('hidden');
            return;
        }
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error('Falha na busca da API');
            const results = await response.json();
            renderSearchResults(results);
        } catch (error) {
            console.error('Erro na busca:', error);
            globalSearchResults.innerHTML = '<div class="search-result-no-match">Erro ao buscar.</div>';
            globalSearchResults.classList.remove('hidden');
        }
    }

    const debouncedSearch = debounce(performSearch, 300);

    globalSearchInput.addEventListener('input', (e) => {
        debouncedSearch(e.target.value.trim());
    });

    globalSearchInput.addEventListener('focus', (e) => {
        if (e.target.value.trim().length >= 2) {
            debouncedSearch(e.target.value.trim());
        }
    });

    globalSearchResults.addEventListener('click', (e) => {
        const item = e.target.closest('.search-result-item');
        if (!item) return;
        const orcamentoId = item.dataset.orcamentoId;
        const row = document.querySelector(`tr[data-orcamento-id="${orcamentoId}"]`);
        if (row) {
            const group = row.closest('.monday-group');
            if (group) group.classList.remove('collapsed');
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });
            row.classList.remove('row-highlight');
            void row.offsetWidth;
            row.classList.add('row-highlight');
            setTimeout(() => {
                row.classList.remove('row-highlight');
            }, 1500);
        } else {
            alert('Não foi possível encontrar o item na tela. Tente rolar manualmente.');
        }
        globalSearchResults.classList.add('hidden');
        globalSearchInput.value = '';
    });

    async function openDetalhesModal(orcamentoId) {
        showModal(modalDetalhesOrcamento);
        try {
            const response = await fetch(`/api/orcamento/${orcamentoId}/detalhes`);
            if (!response.ok) throw new Error('Falha ao carregar detalhes');
            const data = await response.json();
            document.getElementById('detalhes-orcamento-id').value = data.id;
            document.getElementById('detalhes-numero').value = data.numero || '';
            document.getElementById('detalhes-cliente').value = data.cliente || '';
            document.getElementById('detalhes-endereco').value = data.endereco || '';
            document.getElementById('detalhes-etapa1-concluida').value = data.etapa_concluida || 0;
            document.getElementById('detalhes-data-limite1').value = data.data_limite_etapa1 ? data.data_limite_etapa1.split('T')[0] : '';
            document.getElementById('detalhes-data-limite2').value = data.data_limite_etapa2 ? data.data_limite_etapa2.split('T')[0] : '';
            document.getElementById('detalhes-data-visita-etapa1').value = data.data_visita_etapa1 ? data.data_visita_etapa1.split('T')[0] : '';
            document.getElementById('detalhes-data-visita-etapa2').value = data.data_visita_etapa2 ? data.data_visita_etapa2.split('T')[0] : '';
            document.getElementById('detalhes-data-instalacao').value = data.data_instalacao ? data.data_instalacao.split('T')[0] : '';
            document.getElementById('detalhes-itens-etapa1').value = data.etapa1_descricao || '';
            document.getElementById('detalhes-itens-etapa2').value = data.etapa2_descricao || '';
        } catch (error) {
            console.error("Erro ao carregar detalhes:", error);
            hideModals();
            alert("Não foi possível carregar os detalhes do orçamento.");
        }
    }

    async function handleDetalhesSubmit(e) {
        e.preventDefault();
        const orcamentoId = document.getElementById('detalhes-orcamento-id').value;
        const data = {
            numero: document.getElementById('detalhes-numero').value,
            cliente: document.getElementById('detalhes-cliente').value,
            endereco: document.getElementById('detalhes-endereco').value,
            etapa_concluida: parseInt(document.getElementById('detalhes-etapa1-concluida').value, 10),
            data_limite_etapa1: document.getElementById('detalhes-data-limite1').value || null,
            data_limite_etapa2: document.getElementById('detalhes-data-limite2').value || null,
            data_visita_etapa1: document.getElementById('detalhes-data-visita-etapa1').value || null,
            data_visita_etapa2: document.getElementById('detalhes-data-visita-etapa2').value || null,
            data_instalacao: document.getElementById('detalhes-data-instalacao').value || null,
            etapa1_descricao: document.getElementById('detalhes-itens-etapa1').value,
            etapa2_descricao: document.getElementById('detalhes-itens-etapa2').value,
        };
        try {
            const response = await fetch(`/api/orcamento/${orcamentoId}/update_detalhes`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (response.status === 401) { window.location.href = '/login'; return; }
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            hideModals();
            await loadWorkflow(); 
        } catch (error) {
            console.error('Erro ao salvar detalhes:', error);
            alert(`Erro ao salvar: ${error.message}`);
        }
    }
    
    function openEditSimplesModal(orcamentoId, campo, valorAtual, titulo, tipoInput = 'text') {
        return new Promise((resolve, reject) => {
            document.getElementById('modal-edit-simples-titulo').textContent = titulo;
            document.getElementById('modal-edit-simples-label').textContent = titulo;
            document.getElementById('edit-simples-orcamento-id').value = orcamentoId;
            document.getElementById('edit-simples-campo').value = campo;

            const inputText = document.getElementById('edit-simples-valor-text');
            const inputDate = document.getElementById('edit-simples-valor-date');
            const inputTextarea = document.getElementById('edit-simples-valor-textarea');

            inputText.style.display = 'none';
            inputDate.style.display = 'none';
            inputTextarea.style.display = 'none';

            let inputAtivo;

            if (tipoInput === 'date') {
                inputAtivo = inputDate;
                inputAtivo.value = valorAtual ? toInputDate(parseInputDate(valorAtual)) : '';
            } else if (tipoInput === 'textarea') {
                inputAtivo = inputTextarea;
                inputAtivo.value = valorAtual.replace('---','') || '';
            } else {
                inputAtivo = inputText;
                inputAtivo.value = valorAtual.replace('---','') || '';
            }
            inputAtivo.style.display = 'block';
            showModal(modalEditSimples);
            inputAtivo.focus();
            const saveBtn = document.getElementById('modal-edit-simples-save');
            const cancelBtn = document.getElementById('modal-edit-simples-cancel');
            
            const saveHandler = (e) => {
                e.preventDefault();
                removeListeners();
                hideModals();
                resolve({
                    campo: campo,
                    valor: inputAtivo.value
                });
            };
            const cancelHandler = () => {
                removeListeners();
                hideModals();
                reject(new Error('Cancelado pelo usuário'));
            };
            function removeListeners() {
                saveBtn.removeEventListener('click', saveHandler);
                cancelBtn.removeEventListener('click', cancelHandler);
            }
            saveBtn.addEventListener('click', saveHandler);
            cancelBtn.addEventListener('click', cancelHandler);
        });
    }

    async function handleEditSimplesSubmit(orcamentoId, campo, valor) {
        try {
            const response = await fetch(`/api/orcamento/${orcamentoId}/edit_campo`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ campo, valor })
            });
            if (response.status === 401) { window.location.href = '/login'; return; }
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            hideModals();
            await loadWorkflow(); 
        } catch (error) {
            console.error(`Erro ao editar campo ${campo}:`, error);
            alert(`Erro ao salvar: ${error.message}`);
        }
    }
    
    fileInput.addEventListener('change', handleUpload);
    
    btnCriarManual.addEventListener('click', () => {
        openCriarModal().catch(err => {
            if (err.message === 'Cancelado pelo usuário') console.log('Criação manual cancelada.');
        });
    });

    document.getElementById('form-criar-manual').addEventListener('submit', handleCriarManualSubmit);
    document.getElementById('form-detalhes-orcamento').addEventListener('submit', handleDetalhesSubmit);
    document.getElementById('modal-detalhes-cancel').addEventListener('click', hideModals);

    modalTarefaSave.addEventListener('click', handleAddTarefaSubmit);
    modalTarefaCancel.addEventListener('click', hideModals);
    
    document.querySelectorAll('#modal-tarefa-colaborador-list .btn-item-select').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#modal-tarefa-colaborador-list .btn-item-select.selected').forEach(selectedBtn => {
                if (selectedBtn !== btn) selectedBtn.classList.remove('selected');
            });
            btn.classList.toggle('selected');
        });
    });

    board.addEventListener('click', async (e) => {
        const target = e.target;
        const actionTarget = target.closest('[data-action]');
        
        if (!actionTarget) {
            handleGroupToggle(e);
            return;
        }

        if (actionTarget.dataset.action === 'open-public-link') {
            console.log('Link público clicado.');
            e.stopPropagation(); 
            return;
        }
        
        const action = actionTarget.dataset.action;
        const row = actionTarget.closest('.monday-row');
        const orcamentoId = row ? row.dataset.orcamentoId : null;
        const etapaConcluida = row ? row.dataset.etapaConcluida : '0';

        try {
            switch (action) {
                case 'open-detalhes': {
                    if (orcamentoId) await openDetalhesModal(orcamentoId);
                    break;
                }
                case 'agendar-visita': {
                    // Abre o modal de visita vazio
                    const dados = await openVisitaModal(orcamentoId);
                    // Salva e muda o status para "Visita Agendada"
                    await updateStatus(orcamentoId, 'Visita Agendada', dados);
                    break;
                }
                case 'edit-data_visita': {
                    const dataVisita = row.dataset.dataVisita; 
                    const respVisita = row.querySelector('[data-action="edit-responsavel_visita"]')?.textContent || '';
                    const dados = await openVisitaModal(orcamentoId, dataVisita, respVisita.replace('---',''));
                    await handleEditSimplesSubmit(orcamentoId, 'data_visita', dados.data_visita);
                    await handleEditSimplesSubmit(orcamentoId, 'responsavel_visita', dados.responsavel_visita);
                    break;
                }
                case 'edit-responsavel_visita': {
                    const respVisita = actionTarget.textContent.replace('---','');
                    const dados = await openEditSimplesModal(orcamentoId, 'responsavel_visita', respVisita, 'Editar Responsável Visita');
                    await handleEditSimplesSubmit(orcamentoId, dados.campo, dados.valor);
                    break;
                }
                case 'edit-data_entrada_producao': {
                    const dataEntrada = actionTarget.textContent.replace('---','');
                    const dados = await openEditSimplesModal(orcamentoId, 'data_entrada_producao', dataEntrada, 'Editar Data Entrada Produção', 'date');
                    await handleEditSimplesSubmit(orcamentoId, dados.campo, dados.valor);
                    break;
                }
                case 'edit-data_limite': {
                    const dataLimite = actionTarget.textContent.replace('---','');
                    const dados = await openEditSimplesModal(orcamentoId, 'data_limite', dataLimite, `Editar Data Limite (Etapa ${parseInt(etapaConcluida) + 1})`, 'date');
                    await handleEditSimplesSubmit(orcamentoId, dados.campo, dados.valor);
                    break;
                }
                case 'edit-itens_prontos': {
                    const itens = actionTarget.textContent.replace('---','');
                    const dados = await openEditSimplesModal(orcamentoId, 'itens_prontos', itens, 'Editar Itens Prontos', 'textarea');
                    await handleEditSimplesSubmit(orcamentoId, dados.campo, dados.valor);
                    break;
                }
                case 'edit-data_pronto': {
                    const dataPronto = actionTarget.textContent.replace('---','');
                    const dados = await openEditSimplesModal(orcamentoId, 'data_pronto', dataPronto, 'Editar Data Pronto', 'date');
                    await handleEditSimplesSubmit(orcamentoId, dados.campo, dados.valor);
                    break;
                }
                case 'edit-data_instalacao': {
                    const dataInst = row.dataset.dataInstalacao; 
                    const respInst = row.querySelector('[data-action="edit-responsavel_instalacao"]')?.textContent || '';
                    const dados = await openInstalacaoModal(orcamentoId, etapaConcluida, dataInst, respInst.replace('---',''));
                    await handleEditSimplesSubmit(orcamentoId, 'data_instalacao', dados.data_instalacao);
                    await handleEditSimplesSubmit(orcamentoId, 'responsavel_instalacao', dados.responsavel_instalacao);
                    break;
                }
                 case 'edit-responsavel_instalacao': {
                    const respInst = actionTarget.textContent.replace('---','');
                    const dados = await openEditSimplesModal(orcamentoId, 'responsavel_instalacao', respInst, 'Editar Responsável Instalação');
                    await handleEditSimplesSubmit(orcamentoId, dados.campo, dados.valor);
                    break;
                }
                case 'edit-standby_details': {
                    const motivo = actionTarget.textContent.replace('---','');
                    const dados = await openEditSimplesModal(orcamentoId, 'standby_details', motivo, 'Editar Motivo Standby', 'textarea');
                    await handleEditSimplesSubmit(orcamentoId, dados.campo, dados.valor);
                    break;
                }
                case 'agendar-instalacao': {
                    const dados = await openInstalacaoModal(orcamentoId, etapaConcluida);
                    await updateStatus(orcamentoId, 'Instalação Agendada', dados);
                    break;
                }
                case 'open-file-list': {
                    const arquivosJson = actionTarget.dataset.arquivos;
                    const arquivos = JSON.parse(arquivosJson);
                    if (arquivos.length === 0) {
                        openUploadModal(actionTarget.dataset.orcamentoId);
                    } else {
                        openFileListModal(actionTarget.dataset.orcamentoId, arquivosJson);
                    }
                    break;
                }
                case 'expand':
                case 'collapse':
                    handleToggleTarefas(actionTarget);
                    break;
                case 'add-tarefa':
                    openAddTarefaModal(actionTarget);
                    break;
                
                case 'select-status-option': {
                    const selector = actionTarget.closest('.status-selector');
                    const novoStatus = actionTarget.dataset.value;
                    const currentStatus = selector.querySelector('.status-display').dataset.statusValue;
                    
                    if (novoStatus === currentStatus) {
                        closeAllStatusDropdowns();
                        return; 
                    }

                    const type = selector.dataset.type;
                    if (type === 'orcamento') {
                        const display = selector.querySelector('.status-display');
                        display.textContent = novoStatus;
                        display.dataset.statusValue = novoStatus;
                        closeAllStatusDropdowns();
                        await processOrcamentoStatusChange(orcamentoId, novoStatus, etapaConcluida);

                    } else if (type === 'tarefa') {
                        // CORREÇÃO: Adicionada lógica para atualizar status da tarefa (serviço)
                        const tarefaDiv = actionTarget.closest('.tarefa-producao'); 
                        const tarefaIdsString = tarefaDiv.dataset.tarefaIds; 
                        const display = selector.querySelector('.status-display');
                        display.textContent = novoStatus;
                        display.dataset.statusValue = novoStatus;
                        closeAllStatusDropdowns();
                        await processTarefaStatusChange(tarefaIdsString, novoStatus);
                    }
                    break;
                }
                case 'open-status-dropdown': {
                    const selector = actionTarget.closest('.status-selector');
                    const isActive = selector.classList.contains('active');
                    const tableWrapper = selector.closest('.table-wrapper');
                    const parentGroup = selector.closest('.monday-group');
                    const parentRow = selector.closest('.monday-row');

                    closeAllStatusDropdowns(selector); 

                    if (!isActive) {
                        selector.classList.add('active');
                        if (tableWrapper) tableWrapper.classList.add('table-wrapper-dropdown-active');
                        if (parentGroup) parentGroup.classList.add('group-z-index-lift');
                        if (parentRow) parentRow.classList.add('row-z-index-lift');
                    }
                    break;
                }
            }
        } catch (error) {
            if (error.message === 'Cancelado pelo usuário') {
                console.log('Ação cancelada pelo usuário.');
                loadWorkflow(); 
            } else {
                console.error('Erro na delegação de clique:', error);
            }
        }
    });

    board.addEventListener('change', (e) => {
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.status-selector')) {
            closeAllStatusDropdowns(); 
        }
        if (!e.target.closest('.header-search-container')) {
            globalSearchResults.classList.add('hidden');
        }
        if (!e.target.closest('.item-search-container')) {
            if(itemSearchResults) itemSearchResults.classList.add('hidden');
        }
    });

    const uploadDropZone = document.getElementById('modal-upload-dropzone');
    const uploadFileInput = document.getElementById('modal-upload-arquivo-input');
    const uploadFileList = document.getElementById('modal-upload-file-list');
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadDropZone.addEventListener(eventName, e => { e.preventDefault(); e.stopPropagation(); }, false);
    });
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadDropZone.addEventListener(eventName, () => uploadDropZone.classList.add('drag-over'), false);
    });
    ['dragleave', 'drop'].forEach(eventName => {
        uploadDropZone.addEventListener(eventName, () => uploadDropZone.classList.remove('drag-over'), false);
    });
    uploadFileInput.onchange = (e) => handleAddUploadFiles_MainModal(e.target.files);
    uploadDropZone.ondrop = (e) => handleAddUploadFiles_MainModal(e.dataTransfer.files);
    function handleAddUploadFiles_MainModal(files) {
        Array.from(files).forEach(file => {
            projectFilesToUpload.push(file);
            renderUploadFileList_MainModal();
        });
    }
    function renderUploadFileList_MainModal() {
        uploadFileList.innerHTML = '';
        projectFilesToUpload.forEach((file, index) => {
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="file-name">${file.name}</span>
                <button type="button" class="file-remove-btn" data-index="${index}">&times;</button>
            `;
            uploadFileList.appendChild(li);
        });
    }
    uploadFileList.onclick = (e) => {
        if (e.target.classList.contains('file-remove-btn')) {
            const index = parseInt(e.target.dataset.index);
            projectFilesToUpload.splice(index, 1);
            renderUploadFileList_MainModal();
        }
    };
    document.getElementById('modal-upload-save').onclick = async () => {
        if (projectFilesToUpload.length === 0) return alert('Nenhum arquivo selecionado.');
        if (!currentUploadOrcamentoId) return alert('Erro: ID do orçamento não encontrado.');
        await handleUploadArquivos(currentUploadOrcamentoId, projectFilesToUpload);
    };
    document.getElementById('modal-upload-cancel').onclick = hideModals;

    const fileListDropZone = document.getElementById('modal-file-list-dropzone');
    const fileListFileInput = document.getElementById('modal-file-list-input');
    const fileListFilePreview = document.getElementById('modal-file-list-preview');
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileListDropZone.addEventListener(eventName, e => { e.preventDefault(); e.stopPropagation(); }, false);
    });
    ['dragenter', 'dragover'].forEach(eventName => {
        fileListDropZone.addEventListener(eventName, () => fileListDropZone.classList.add('drag-over'), false);
    });
    ['dragleave', 'drop'].forEach(eventName => {
        fileListDropZone.addEventListener(eventName, () => fileListDropZone.classList.remove('drag-over'), false);
    });
    fileListFileInput.onchange = (e) => handleAddUploadFiles_FileListModal(e.target.files);
    fileListDropZone.ondrop = (e) => handleAddUploadFiles_FileListModal(e.dataTransfer.files);
    function handleAddUploadFiles_FileListModal(files) {
        Array.from(files).forEach(file => {
            projectFilesToUpload.push(file);
            renderUploadFileList_FileListModal();
        });
    }
    function renderUploadFileList_FileListModal() {
        fileListFilePreview.innerHTML = '';
        projectFilesToUpload.forEach((file, index) => {
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="file-name">${file.name}</span>
                <button type="button" class="file-remove-btn" data-index="${index}">&times;</button>
            `;
            fileListFilePreview.appendChild(li);
        });
    }
    fileListFilePreview.onclick = (e) => {
        if (e.target.classList.contains('file-remove-btn')) {
            const index = parseInt(e.target.dataset.index);
            projectFilesToUpload.splice(index, 1);
            renderUploadFileList_FileListModal();
        }
    };
    document.getElementById('modal-file-list-close').onclick = hideModals;
    document.getElementById('modal-file-list-upload-save').onclick = async () => {
        if (projectFilesToUpload.length === 0) return alert('Nenhum arquivo novo selecionado para anexar.');
        if (!currentUploadOrcamentoId) return alert('Erro: ID do orçamento não encontrado.');
        await handleUploadArquivos(currentUploadOrcamentoId, projectFilesToUpload);
    };
    document.getElementById('file-list-modal-body').onclick = (e) => {
        const deleteBtn = e.target.closest('.btn-remove-manual-item');
        if (deleteBtn) {
            const arquivoId = deleteBtn.dataset.arquivoId;
            const nomeArquivo = deleteBtn.dataset.arquivoNome;
            const orcamentoId = deleteBtn.dataset.orcamentoId;
            openConfirmDeleteModal(arquivoId, nomeArquivo, orcamentoId);
        }
    };
    document.getElementById('modal-confirmar-delete-save').onclick = (e) => {
        const btn = e.target;
        const arquivoId = btn.dataset.arquivoId;
        const orcamentoId = btn.dataset.orcamentoId;
        handleDeleteArquivo(arquivoId, orcamentoId);
    };
    document.getElementById('modal-confirmar-delete-cancel').onclick = () => {
        hideModals();
        if (currentUploadOrcamentoId) {
             const row = document.querySelector(`tr[data-orcamento-id="${currentUploadOrcamentoId}"]`);
             if(row) {
                 const fileButton = row.querySelector('.file-pdf-icon-button');
                 if(fileButton) {
                    const arquivosJson = fileButton.dataset.arquivos;
                    openFileListModal(currentUploadOrcamentoId, arquivosJson);
                 }
             }
        }
    };

    loadWorkflow();
    
    setInterval(updateTimestamps, 30000); 
});
