# Estágio 1: Build
# Usar uma imagem Python específica e estável
FROM python:3.11-slim as builder
WORKDIR /app

# Copiar primeiro o requirements.txt para aproveitar o cache do Docker
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Estágio 2: Produção
FROM python:3.11-slim
WORKDIR /app

# Copia as dependências pré-compiladas do estágio de build e as instala
COPY --from=builder /app/wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt

# Copia o código da aplicação
COPY . .

EXPOSE 8501

HEALTHCHECK CMD streamlit healthcheck

# O ENTRYPOINT garante que o app rode corretamente no Kubernetes com Ingress
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]