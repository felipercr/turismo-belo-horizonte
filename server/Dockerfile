FROM python:3.10-slim

WORKDIR /app

# Copia e instala as dependências
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o servidor (infraestrutura) e as regras de negócio (pasta api)
COPY server/ .
COPY api/ ./api/

CMD ["python", "-u", "main.py"]
