# Estágio 1: Build
# Usar uma imagem Python específica e estável
FROM python:3.11-slim as builder

WORKDIR /app

# Instalar dependências de build, se necessário
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential

# Copiar primeiro o requirements.txt para aproveitar o cache do Docker
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Estágio 2: Produção
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema necessárias
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Criar diretório para configurações
RUN mkdir -p /app/config
COPY config.yaml /app/config/

EXPOSE 8501

# Modificar o comando para usar variáveis de ambiente
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.baseUrlPath=/"]