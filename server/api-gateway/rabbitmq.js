const amqp = require('amqplib');
const { v4: uuidv4 } = require('uuid');

let channel;
let replyQueue;
const pendingRequests = new Map();

async function initRabbitMQ(rabbitUrl, retries = 20, delay = 5000) {
    while (retries > 0) {
        try {
            console.log(`Tentando conectar ao RabbitMQ. Tentativas restantes: ${retries}`);
            const connection = await amqp.connect(rabbitUrl);
            channel = await connection.createChannel();
            
            const q = await channel.assertQueue('', { exclusive: true });
            replyQueue = q.queue;

            channel.consume(replyQueue, (msg) => {
                if (msg) {
                    const correlationId = msg.properties.correlationId;
                    const resolve = pendingRequests.get(correlationId);
                    
                    if (resolve) {
                        const response = JSON.parse(msg.content.toString());
                        resolve(response);
                        pendingRequests.delete(correlationId);
                    }
                }
            }, { noAck: true });

            console.log("Conectado ao RabbitMQ e aguardando respostas RPC.");
            return; // Sai do loop se a conexão for bem sucedida

        } catch (error) {
            console.error("Falha ao conectar no RabbitMQ. Tentando novamente...");
            retries -= 1;
            // Espera o tempo definido (delay) antes de tentar novamente
            await new Promise(res => setTimeout(res, delay));
        }
    }
    console.error("Falha de conexão com o RabbitMQ após limite de tentativas.");
    process.exit(1); // Encerra a aplicação se não conseguir de forma alguma
}

// Envia uma mensagem para o backend e espera a resposta (padrão RPC).
// Se o backend não responder em timeoutMs, a Promise é rejeitada, para o
// navegador não ficar esperando para sempre.
async function sendRpcMessage(msgType, payload, timeoutMs = 5000) {
    return new Promise((resolve, reject) => {
        const correlationId = uuidv4();
        const timer = setTimeout(() => {
            pendingRequests.delete(correlationId);
            reject(new Error(`Sem resposta do backend para '${msgType}'.`));
        }, timeoutMs);

        pendingRequests.set(correlationId, (response) => {
            clearTimeout(timer);
            resolve(response);
        });

        const message = { type: msgType, ...payload };

        channel.sendToQueue('my_queue', Buffer.from(JSON.stringify(message)), {
            correlationId: correlationId,
            replyTo: replyQueue
        });
    });
}

module.exports = { initRabbitMQ, sendRpcMessage };