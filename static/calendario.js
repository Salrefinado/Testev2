document.addEventListener('DOMContentLoaded', () => {

    const calendarEl = document.getElementById('calendar-container');
    const btnTodos = document.getElementById('btn-todos');
    const btnVisitas = document.getElementById('btn-visitas');
    const btnInstalacoes = document.getElementById('btn-instalacoes');

    const modalOverlay = document.getElementById('modal-overlay');
    const modalEvento = document.getElementById('modal-evento');
    const modalEventoTitulo = document.getElementById('modal-evento-titulo');
    const modalEventoBody = document.getElementById('modal-evento-body');
    const modalEventoFechar = document.getElementById('modal-evento-fechar');

    // === INÍCIO: NOVAS FUNÇÕES DE PREVISÃO DO TEMPO ===
    
    // Cache para a previsão geral
    let generalWeatherForecast = null;

    /**
     * Mapeia os códigos WMO (Open-Meteo) para ícones.
     * https://open-meteo.com/en/docs#weathervariables
     */
    function getWeatherIcon(code) {
        if ([0, 1].includes(code)) return '☀️'; // Sol
        if ([2].includes(code)) return '🌤️'; // Parcialmente nublado
        if ([3].includes(code)) return '☁️'; // Nublado
        if ([45, 48].includes(code)) return '🌫️'; // Nevoeiro
        if ([51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return '🌧️'; // Chuva/Chuvisco
        if ([71, 73, 75, 77, 85, 86].includes(code)) return '❄️'; // Neve
        if ([95, 96, 99].includes(code)) return '⛈️'; // Tempestade
        return ''; // Nenhum ícone
    }

    /**
     * Busca a previsão geral para Curitiba e armazena no cache.
     */
    async function fetchGeneralForecast() {
        if (generalWeatherForecast) {
            return generalWeatherForecast; // Retorna do cache se já tiver
        }
        
        try {
            const response = await fetch('/api/previsao/curitiba');
            if (!response.ok) {
                console.error('Falha ao buscar previsão geral.');
                generalWeatherForecast = { error: 'Falha ao buscar previsão' }; // Salva erro no cache
                return generalWeatherForecast;
            }
            const data = await response.json();
            
            // Transforma o array em um mapa para busca rápida por data
            // ex: { "2025-11-12": "☀️", "2025-11-13": "🌧️" }
            const forecastMap = data.reduce((acc, day) => {
                acc[day.date] = getWeatherIcon(day.condition_code);
                return acc;
            }, {});
            
            generalWeatherForecast = forecastMap;
            return generalWeatherForecast;

        } catch (error) {
            console.error('Erro ao buscar previsão geral:', error);
            generalWeatherForecast = { error: 'Falha na requisição' };
            return generalWeatherForecast;
        }
    }
    
    // === FIM: NOVAS FUNÇÕES DE PREVISÃO DO TEMPO ===


    if (!calendarEl || !btnTodos || !btnVisitas || !btnInstalacoes || !modalEvento) {
        console.error("Elementos essenciais do calendário ou modal não encontrados.");
        return;
    }

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        locale: 'pt-br',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,listWeek'
        },
        buttonText: {
            today: 'Hoje',
            month: 'Mês',
            week: 'Semana',
            list: 'Lista'
        },
        height: 'auto',
        eventTimeFormat: {
            hour: '2-digit',
            minute: '2-digit',
            meridiem: false,
            hour12: false
        },
        eventClick: function(info) {
            info.jsEvent.preventDefault();
            const props = info.event.extendedProps;
            showEventoModal(props);
        },
        
        // === INÍCIO: NOVO EVENTO PARA ADICIONAR ÍCONES ===
        /**
         * Chamado quando cada célula de dia é renderizada no calendário.
         */
        dayCellDidMount: function(info) {
            if (!generalWeatherForecast || generalWeatherForecast.error) {
                return; // Não faz nada se a previsão falhou
            }
            
            // Formata a data da célula para "YYYY-MM-DD"
            const dateStr = info.date.toISOString().split('T')[0];
            
            // Busca o ícone no nosso mapa de previsão
            const icon = generalWeatherForecast[dateStr];
            
            if (icon) {
                // Cria o elemento do ícone
                const iconEl = document.createElement('div');
                iconEl.className = 'calendar-weather-icon';
                iconEl.textContent = icon;
                
                // Adiciona o ícone ao canto superior direito da célula do dia
                // (O 'daygrid-day-top' é a área onde fica o número do dia)
                const dayTopEl = info.el.querySelector('.fc-daygrid-day-top');
                if (dayTopEl) {
                    dayTopEl.appendChild(iconEl);
                }
            }
        }
        // === FIM: NOVO EVENTO PARA ADICIONAR ÍCONES ===
    });

    /**
     * Busca eventos da API e atualiza o calendário
     */
    async function loadEvents(tipo) {
        try {
            calendarEl.innerHTML = '<p style="text-align:center; padding: 40px;">Carregando eventos...</p>';
            
            // --- ATUALIZADO: Garante que a previsão do tempo seja buscada ANTES de carregar eventos ---
            if (!generalWeatherForecast) {
                await fetchGeneralForecast();
            }
            // --- FIM DA ATUALIZAÇÃO ---

            const response = await fetch(`/api/calendario/eventos?tipo=${tipo}`);
            if (!response.ok) {
                throw new Error('Falha ao buscar eventos da API');
            }
            const events = await response.json();

            calendarEl.innerHTML = '';
            
            calendar.removeAllEventSources();
            calendar.addEventSource(events);
            
            if (calendar.view) {
                calendar.render();
            } else {
                calendar.render();
            }

        } catch (error) {
            console.error('Erro ao carregar eventos:', error);
            calendarEl.innerHTML = `<p style="text-align:center; color: red; padding: 40px;">${error.message}</p>`;
        }
    }
    
    // --- Funções do Modal (Sem alteração) ---
    function showEventoModal(props) {
        if (!props) return;
        
        modalEventoTitulo.textContent = `${props.tipo}: ${props.numero} - ${props.cliente}`;
        
        const itensFormatados = props.itens.split(',').map(item => item.trim()).join('\n');
        
        modalEventoBody.innerHTML = `
            <p><strong>Status:</strong> ${props.etapa}</p>
            <p><strong>Data:</strong> ${props.data_hora}</p>
            <p><strong>Equipe/Responsável:</strong> ${props.quem_vai}</p>
            <p><strong>Agendado Por:</strong> ${props.quem_agendou}</p>
            <p><strong>Itens Relacionados:</strong></p>
            <textarea readonly>${itensFormatados}</textarea>
        `;
        modalOverlay.classList.remove('hidden');
        modalEvento.classList.remove('hidden');
    }

    function hideEventoModal() {
        modalOverlay.classList.add('hidden');
        modalEvento.classList.add('hidden');
    }

    // --- Event Listeners (Sem alteração) ---
    
    btnTodos.addEventListener('click', () => {
        btnTodos.classList.add('active');
        btnVisitas.classList.remove('active');
        btnInstalacoes.classList.remove('active');
        loadEvents('todos');
    });

    btnVisitas.addEventListener('click', () => {
        btnTodos.classList.remove('active');
        btnVisitas.classList.add('active');
        btnInstalacoes.classList.remove('active');
        loadEvents('visitas');
    });

    btnInstalacoes.addEventListener('click', () => {
        btnTodos.classList.remove('active');
        btnVisitas.classList.remove('active');
        btnInstalacoes.classList.add('active');
        loadEvents('instalacoes');
    });

    modalEventoFechar.addEventListener('click', hideEventoModal);
    modalOverlay.addEventListener('click', hideEventoModal);

    // --- CARGA INICIAL ---
    loadEvents('todos'); // Carrega "Todos" por padrão
});