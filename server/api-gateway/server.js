const express = require('express');
const cors = require('cors');
const { initRabbitMQ, sendRpcMessage } = require('./rabbitmq');

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

app.get('/api/points', async (req, res) => {
    try {
        const response = await sendRpcMessage('get_points', {});
        res.json(response);
    } catch (error) {
        res.status(500).json({ status: 'error', message: "Erro ao comunicar com o servidor." });
    }
});

app.post('/api/points', async (req, res) => {
    try {
        const response = await sendRpcMessage('add_point', req.body);
        res.json(response);
    } catch (error) {
        res.status(500).json({ status: 'error', message: "Erro ao adicionar ponto." });
    }
});

// Rota para excluir ponto turístico (Administrador)
app.delete('/api/points/:id', async (req, res) => {
    try {
        const pointId = parseInt(req.params.id);
        const response = await sendRpcMessage('delete_point', { point_id: pointId });
        res.json(response);
    } catch (error) {
        res.status(500).json({ status: 'error', message: "Erro ao excluir ponto turístico." });
    }
});

app.get('/api/tours', async (req, res) => {
    try {
        const response = await sendRpcMessage('get_tours', {});
        res.json(response);
    } catch (error) {
        res.status(500).json({ status: 'error', message: "Erro ao buscar tours." });
    }
});

app.post('/api/tours', async (req, res) => {
    try {
        const response = await sendRpcMessage('add_tour', req.body);
        res.json(response);
    } catch (error) {
        res.status(500).json({ status: 'error', message: "Erro ao adicionar tour." });
    }
});

// Rota para excluir tour (Turista)
app.delete('/api/tours/:id', async (req, res) => {
    try {
        const tourId = parseInt(req.params.id);
        const response = await sendRpcMessage('delete_tour', { tour_id: tourId });
        res.json(response);
    } catch (error) {
        res.status(500).json({ status: 'error', message: "Erro ao excluir tour." });
    }
});

app.post('/api/register', async (req, res) => {
    try {
        const response = await sendRpcMessage('register', req.body);
        res.json(response);
    } catch (error) {
        res.status(500).json({ status: 'error', message: "Erro interno ao registrar." });
    }
});

app.post('/api/login', async (req, res) => {
    try {
        const response = await sendRpcMessage('login', req.body);
        res.json(response);
    } catch (error) {
        res.status(500).json({ status: 'error', message: "Erro interno ao fazer login." });
    }
});

const PORT = 3000;
const RABBIT_URL = process.env.RABBITMQ_URL || 'amqp://guest:guest@localhost:5672';

initRabbitMQ(RABBIT_URL).then(() => {
    app.listen(PORT, () => {
        console.log(`API Gateway rodando na porta ${PORT}`);
    });
}).catch(console.error);
