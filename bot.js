// bot.js
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const http = require('http'); // Para fazer a requisição ao app.py

// Configuração
// IMPORTANTE: O seu app.py DEVE estar rodando na porta 5001
const PYTHON_API_HOST = 'http://127.0.0.1:5001'; // Host base da API

// Lista de números autorizados (deve ser a MESMA lista do app.py)
// O formato @c.us é como o whatsapp-web.js identifica usuários
const AUTHORIZED_BOT_NUMBERS = [
    "554188368319@c.us", // SEU NÚMERO (Exemplo)
    "554100000000@c.us", // PAULO (exemplo)
    "554187831513@c.us", // RENATO (exemplo)
    "554192078542@c.us", // NOVO NÚMERO ADICIONADO
];

console.log('Iniciando cliente do WhatsApp...');

const client = new Client({
    authStrategy: new LocalAuth(), // Salva a sessão para não escanear sempre
    puppeteer: {
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
    }
});

// Evento 1: Gerar o QR Code
client.on('qr', (qr) => {
    console.log('QR Code recebido, escaneie com seu celular:');
    qrcode.generate(qr, { small: true });
});

// Evento 2: Autenticado com sucesso
client.on('ready', () => {
    console.log('Cliente conectado e pronto!');
    console.log('Ouvindo mensagens...');
});

// Evento 3: Mensagem recebida
client.on('message', async (msg) => {
    const remetente = msg.from; // ex: "554188368319@c.us"
    const textoOriginal = msg.body.trim();
    const textoLower = textoOriginal.toLowerCase();

    console.log(`Mensagem recebida de ${remetente}: "${textoOriginal}"`);

    // 1. Verifica se é de um número autorizado
    if (!AUTHORIZED_BOT_NUMBERS.includes(remetente)) {
        console.log('Número não autorizado. Ignorando.');
        return;
    }

    // 2. Não responde a si mesmo ou a mensagens de grupo/status
    if (msg.isStatus || remetente === 'status@broadcast' || msg.type === 'call') {
        return;
    }
    
    try {
        const queryRemetente = encodeURIComponent(remetente);
        let url;
        let respostaPython;
        let jsonResposta;

        // --- INÍCIO DA LÓGICA DE COMANDOS ATUALIZADA ---
        
        if (textoLower === 'comandos') {
            // Comando "Comandos" - Resposta estática
            console.log(`[Comando] Executando "Comandos" para ${remetente}`);
            const respostaComandos = `*Lista de Comandos Disponíveis:*\n
*prontos*
Encaminha todos os orçamentos que estão prontos para instalação com data agendada ou não.

*agenda*
Encaminha todos os orçamentos com datas de visita ou instalação agendadas.

*entrada de orçamento*
Encaminha todos os orçamentos que estão nesse grupo.

*visitas e medidas*
Encaminha todos os orçamentos que estão nesse grupo.

*projetar*
Encaminha todos os orçamentos que estão nesse grupo.

*linha de produção*
Encaminha o resumo da fila de produção, ordenado por prazo, com a posição de largada de cada colaborador.

*standby*
Encaminha todos os orçamentos que estão nesse grupo.

*(Número ou Nome do cliente)*
Encaminha os detalhes de qual processo esta o orçamento.`;
            
            await client.sendMessage(remetente, respostaComandos);
            return; // Encerra a execução aqui

        } else if (textoLower === 'prontos') {
            // Comando "Prontos"
            console.log(`[Comando] Executando "Prontos" para ${remetente}`);
            url = `${PYTHON_API_HOST}/api/bot/prontos?remetente=${queryRemetente}`;
            
        } else if (textoLower === 'agenda') {
            // Comando "Agenda"
            console.log(`[Comando] Executando "Agenda" para ${remetente}`);
            url = `${PYTHON_API_HOST}/api/bot/agenda?remetente=${queryRemetente}`;

        } else if (textoLower.startsWith('atrasados')) {
            // Comando "Atrasados X dias"
            const parts = textoLower.split(' ');
            const dias = parseInt(parts[1]) || 7; // Padrão de 7 dias
            console.log(`[Comando] Executando "Atrasados ${dias} dias" para ${remetente}`);
            url = `${PYTHON_API_HOST}/api/bot/atrasados?dias=${dias}&remetente=${queryRemetente}`;

        // --- NOVOS COMANDOS DE GRUPO ---
        } else if (textoLower === 'entrada de orçamento') {
            console.log(`[Comando] Executando "Entrada de Orçamento" para ${remetente}`);
            url = `${PYTHON_API_HOST}/api/bot/grupo?nome_grupo=Entrada de Orçamento&remetente=${queryRemetente}`;
        
        } else if (textoLower === 'visitas e medidas') {
            console.log(`[Comando] Executando "Visitas e Medidas" para ${remetente}`);
            url = `${PYTHON_API_HOST}/api/bot/grupo?nome_grupo=Visitas e Medidas&remetente=${queryRemetente}`;

        } else if (textoLower === 'projetar') {
            console.log(`[Comando] Executando "Projetar" para ${remetente}`);
            url = `${PYTHON_API_HOST}/api/bot/grupo?nome_grupo=Projetar&remetente=${queryRemetente}`;
        
        // ==========================================================
        // === INÍCIO DA ALTERAÇÃO (Etapa 1 do seu plano) ===
        // ==========================================================
        } else if (textoLower === 'linha de produção') {
            console.log(`[Comando] Executando "Linha de Produção" (Nova Fila) para ${remetente}`);
            // Chama a nova rota que calcula a fila de produção
            url = `${PYTHON_API_HOST}/api/bot/fila_producao?remetente=${queryRemetente}`;
        // ==========================================================
        // === FIM DA ALTERAÇÃO (Etapa 1 do seu plano) ===
        // ==========================================================
        
        } else if (textoLower === 'standby') {
            console.log(`[Comando] Executando "Standby" para ${remetente}`);
            url = `${PYTHON_API_HOST}/api/bot/grupo?nome_grupo=StandBy&remetente=${queryRemetente}`;

        } else {
            // Lógica Padrão (Busca por número ou cliente)
            console.log(`[Busca] Procurando por "${textoOriginal}" para ${remetente}`);
            const queryTexto = encodeURIComponent(textoOriginal); // Usa o texto original
            url = `${PYTHON_API_HOST}/api/bot/query?texto=${queryTexto}&remetente=${queryRemetente}`;
        }
        
        // --- FIM DA LÓGICA DE COMANDOS ---

        respostaPython = await httpGet(url);
        jsonResposta = JSON.parse(respostaPython);

        // --- ALTERAÇÃO SOLICITADA (SUPORTE A MÚLTIPLAS MENSAGENS) ---
        
        if (jsonResposta.respostas) { 
            // É uma busca (pode ter 0, 1 ou muitas respostas)
            if (jsonResposta.respostas.length === 0) {
                console.log("Resposta da API (busca) vazia. Ignorando.");
            } else {
                console.log(`Enviando ${jsonResposta.respostas.length} respostas para ${remetente}`);
                for (const resposta of jsonResposta.respostas) {
                    // Envia cada resposta individualmente
                    await client.sendMessage(remetente, resposta);
                    // Adiciona um pequeno delay para garantir a ordem das mensagens
                    await new Promise(resolve => setTimeout(resolve, 500)); 
                }
            }
        } else if (jsonResposta.resposta && jsonResposta.resposta.trim() !== "") {
            // É um comando (prontos, agenda, atrasados, ou grupo) que retornou uma resposta singular
            console.log(`Enviando resposta (comando) para ${remetente}`);
            await client.sendMessage(remetente, jsonResposta.resposta);
        } else {
            // Comando não retornou nada, ou a busca falhou
            console.log("Resposta da API vazia ou mal formatada. Ignorando.");
        }
        // --- FIM DA ALTERAÇÃO ---

    } catch (error) {
        console.error('Erro ao processar a mensagem:', error);
        // Não envia resposta de erro ao usuário
    }
});

// Função helper para fazer a requisição HTTP para o app.py
function httpGet(url) {
    return new Promise((resolve, reject) => {
        http.get(url, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => resolve(data));
        }).on('error', (err) => reject(err));
    });
}

client.initialize();