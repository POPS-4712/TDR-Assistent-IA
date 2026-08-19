const fs = require('fs');
const path = './workflows/02-laboral.json';
const data = JSON.parse(fs.readFileSync(path, 'utf8'));

// Replace WhatsApp node with Telegram
const whatsappIndex = data.nodes.findIndex(n => n.name === 'WhatsApp - Oferta');
if (whatsappIndex !== -1) {
    const originalNode = data.nodes[whatsappIndex];
    data.nodes[whatsappIndex] = {
        parameters: {
            method: "POST",
            url: "=https://api.telegram.org/bot{{$env.TELEGRAM_BOT_TOKEN}}/sendMessage",
            sendHeaders: true,
            headerParameters: {
                parameters: [
                    {
                        name: "Content-Type",
                        value: "application/json"
                    }
                ]
            },
            sendBody: true,
            contentType: "raw",
            rawContentType: "application/json",
            body: "={{ JSON.stringify({ chat_id: $env.TELEGRAM_CHAT_ID, text: '<b>[Oferta laboral]</b> ' + ($json.titulo || '') + '\\n' + ($json.resumen || '') + '\\n' + ($json.enlace || ''), parse_mode: 'HTML' }) }}",
            options: {}
        },
        id: "telegram",
        name: "Telegram - Oferta",
        type: "n8n-nodes-base.httpRequest",
        typeVersion: 4.2,
        position: originalNode.position,
        retryOnFail: true,
        maxTries: 3,
        waitBetweenTries: 2000,
        onError: "continueRegularOutput"
    };
}

// Update connections
if (data.connections && data.connections['Validar JSON Gemini']) {
    const mainConnection = data.connections['Validar JSON Gemini'].main;
    if (mainConnection && mainConnection[0]) {
        for (const conn of mainConnection[0]) {
            if (conn.node === 'WhatsApp - Oferta') {
                conn.node = 'Telegram - Oferta';
            }
        }
    }
}

fs.writeFileSync(path, JSON.stringify(data, null, 2));
console.log('02-laboral.json updated');
