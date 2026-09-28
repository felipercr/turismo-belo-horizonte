FROM node:18-alpine
WORKDIR /app

# Dependências do gateway
COPY server/api-gateway/package*.json ./
RUN npm install

# Código do gateway e o frontend (servido como arquivos estáticos em /public)
COPY server/api-gateway/ .
COPY frontend/ ./public/

CMD ["node", "server.js"]
