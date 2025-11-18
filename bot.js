// bot.js
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const http = require('http'); // Para fazer a requisição GET ao app.py (Consultas)
const express = require('express'); // Para receber a requisição POST do app.py (Notificações)

// --- CONFIGURAÇÃO ---

// Porta onde o BOT vai escutar os pedidos do Python
const BOT_SERVER_PORT = 5000; 

// Host da API Python (app.py) para consultas de dados
const PYTHON_API_HOST = 'http://127.0.0.1:5001'; 

// ID do Grupo de Notificações e Comandos
const TARGET_GROUP_ID = '120363404624474162@g.us';

// Lista de números autorizados (Privados)
const AUTHORIZED_BOT_NUMBERS = [
    "554188368319@c.us", // SEU NÚMERO
    "554100000000@c.us", // PAULO
    "554187831513@c.us", // RENATO
    "554192078542@c.us", // NOVO NÚMERO
];

// --- INICIALIZAÇÃO DO SERVIDOR EXPRESS (RECEBER DO PYTHON) ---
const app = express();
app.use(express.json()); // Permite ler JSON no corpo da requisição

console.log('Iniciando cliente do WhatsApp...');

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
    }
});

// --- Rota para o app.py enviar notificações ---
app.post('/send_notification', async (req, res) => {
    const { message } = req.body;
    
    if (!message) {
        return res.status(400).json({ error: 'Mensagem vazia.' });
    }

    try {
        // Envia a mensagem diretamente para o GRUPO ALVO
        await client.sendMessage(TARGET_GROUP_ID, message);
        console.log(`[API] Notificação enviada para o grupo ${TARGET_GROUP_ID}`);
        return res.status(200).json({ status: 'success' });
    } catch (error) {
        console.error('[API] Erro ao enviar notificação:', error);
        return res.status(500).json({ error: 'Falha ao enviar mensagem no WhatsApp.' });
    }
});

// Inicia o servidor do Bot
app.listen(BOT_SERVER_PORT, () => {
    console.log(`Servidor do Bot rodando e ouvindo em http://127.0.0.1:${BOT_SERVER_PORT}`);
});


// --- LÓGICA DO WHATSAPP ---

client.on('qr', (qr) => {
    console.log('QR Code recebido, escaneie com seu celular:');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('Cliente WhatsApp conectado e pronto!');
});

client.on('message', async (msg) => {
    const remetente = msg.from; // Pode ser um usuário privado ou o ID do grupo
    const textoOriginal = msg.body.trim();
    const textoLower = textoOriginal.toLowerCase();

    // 1. Verifica permissão:
    // Aceita se for um número autorizado OU se a mensagem vier do GRUPO ALVO
    const isAuthorizedPrivate = AUTHORIZED_BOT_NUMBERS.includes(remetente);
    const isTargetGroup = remetente === TARGET_GROUP_ID;

    if (!isAuthorizedPrivate && !isTargetGroup) {
        // Ignora mensagens de desconhecidos e outros grupos
        return;
    }

    console.log(`Mensagem recebida de ${remetente}: "${textoOriginal}"`);

    // 2. Ignora status e calls
    if (msg.isStatus || remetente === 'status@broadcast' || msg.type === 'call') {
        return;
    }

    // Se a mensagem veio do grupo, precisamos saber QUEM mandou dentro do grupo (author)
    // Para a API Python, vamos passar o ID de quem mandou a mensagem, 
    // mas se for grupo, o 'remetente' na query string será o ID do grupo para fins de log/resposta
    const author = msg.author || remetente; 

    try {
        const queryRemetente = encodeURIComponent(author); // Identifica quem pediu
        let url;
        let respostaPython;
        let jsonResposta;

        // --- LÓGICA DE COMANDOS ---
        
        if (textoLower === 'comandos') {
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
Encaminha o resumo da fila de produção.

*standby*
Encaminha todos os orçamentos que estão nesse grupo.

*(Número ou Nome do cliente)*
Encaminha os detalhes de qual processo esta o orçamento.`;
            
            await client.sendMessage(remetente, respostaComandos);
            return;

        } else if (textoLower === 'prontos') {
            console.log(`[Comando] "Prontos" solicitado em ${remetente}`);
            url = `${PYTHON_API_HOST}/api/bot/prontos?remetente=${queryRemetente}`; // Vamos passar o author se precisar validar no python, mas o python valida lista.
            // Nota: Para simplificar, no python vamos adicionar o author à lista ou confiar na filtragem do bot aqui.
            // Para manter compatibilidade com o app.py atual, vamos "fingir" ser um admin na query se for do grupo,
            // ou você deve adicionar o ID do grupo na lista AUTHORIZED_BOT_NUMBERS do app.py.
            // VOU AJUSTAR A CHAMADA PARA USAR UM NÚMERO FIXO AUTORIZADO SE FOR DO GRUPO
            // para garantir que o Python responda.
            const authUser = isTargetGroup ? AUTHORIZED_BOT_NUMBERS[0] : remetente; 
            url = `${PYTHON_API_HOST}/api/bot/prontos?remetente=${encodeURIComponent(authUser)}`;
            
        } else if (textoLower === 'agenda') {
            console.log(`[Comando] "Agenda" solicitado em ${remetente}`);
            const authUser = isTargetGroup ? AUTHORIZED_BOT_NUMBERS[0] : remetente;
            url = `${PYTHON_API_HOST}/api/bot/agenda?remetente=${encodeURIComponent(authUser)}`;

        } else if (textoLower.startsWith('atrasados')) {
            const parts = textoLower.split(' ');
            const dias = parseInt(parts[1]) || 7;
            console.log(`[Comando] "Atrasados" solicitado em ${remetente}`);
            const authUser = isTargetGroup ? AUTHORIZED_BOT_NUMBERS[0] : remetente;
            url = `${PYTHON_API_HOST}/api/bot/atrasados?dias=${dias}&remetente=${encodeURIComponent(authUser)}`;

        } else if (textoLower === 'entrada de orçamento') {
            console.log(`[Comando] "Entrada de Orçamento" solicitado em ${remetente}`);
            const authUser = isTargetGroup ? AUTHORIZED_BOT_NUMBERS[0] : remetente;
            url = `${PYTHON_API_HOST}/api/bot/grupo?nome_grupo=Entrada de Orçamento&remetente=${encodeURIComponent(authUser)}`;
        
        } else if (textoLower === 'visitas e medidas') {
            console.log(`[Comando] "Visitas e Medidas" solicitado em ${remetente}`);
            const authUser = isTargetGroup ? AUTHORIZED_BOT_NUMBERS[0] : remetente;
            url = `${PYTHON_API_HOST}/api/bot/grupo?nome_grupo=Visitas e Medidas&remetente=${encodeURIComponent(authUser)}`;

        } else if (textoLower === 'projetar') {
            console.log(`[Comando] "Projetar" solicitado em ${remetente}`);
            const authUser = isTargetGroup ? AUTHORIZED_BOT_NUMBERS[0] : remetente;
            url = `${PYTHON_API_HOST}/api/bot/grupo?nome_grupo=Projetar&remetente=${encodeURIComponent(authUser)}`;
        
        } else if (textoLower === 'linha de produção') {
            console.log(`[Comando] "Linha de Produção" solicitado em ${remetente}`);
            const authUser = isTargetGroup ? AUTHORIZED_BOT_NUMBERS[0] : remetente;
            url = `${PYTHON_API_HOST}/api/bot/fila_producao?remetente=${encodeURIComponent(authUser)}`;
        
        } else if (textoLower === 'standby') {
            console.log(`[Comando] "Standby" solicitado em ${remetente}`);
            const authUser = isTargetGroup ? AUTHORIZED_BOT_NUMBERS[0] : remetente;
            url = `${PYTHON_API_HOST}/api/bot/grupo?nome_grupo=StandBy&remetente=${encodeURIComponent(authUser)}`;

        } else {
            // Busca Padrão
            if (textoOriginal.length < 2) return; // Ignora mensagens muito curtas
            console.log(`[Busca] "${textoOriginal}" solicitado em ${remetente}`);
            const authUser = isTargetGroup ? AUTHORIZED_BOT_NUMBERS[0] : remetente;
            const queryTexto = encodeURIComponent(textoOriginal);
            url = `${PYTHON_API_HOST}/api/bot/query?texto=${queryTexto}&remetente=${encodeURIComponent(authUser)}`;
        }

        // --- EXECUÇÃO DA REQUISIÇÃO AO PYTHON ---
        respostaPython = await httpGet(url);
        
        try {
            jsonResposta = JSON.parse(respostaPython);
        } catch (e) {
            // Se não for JSON, pode ser erro ou string direta (embora seu app retorne JSON)
            console.error("Erro ao parsear resposta do Python:", e);
            return;
        }

        // Envio da Resposta
        if (jsonResposta.respostas) { 
            // Caso: Busca (array de respostas)
            if (jsonResposta.respostas.length > 0) {
                for (const resposta of jsonResposta.respostas) {
                    await client.sendMessage(remetente, resposta);
                    await new Promise(resolve => setTimeout(resolve, 500)); 
                }
            }
        } else if (jsonResposta.resposta && jsonResposta.resposta.trim() !== "") {
            // Caso: Comando (resposta única)
            await client.sendMessage(remetente, jsonResposta.resposta);
        }

    } catch (error) {
        console.error('Erro ao processar mensagem/comando:', error);
    }
});

// Função helper para requisições GET
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