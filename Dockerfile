# Etapa 1: Base e Instalação de Dependências
# Usar uma imagem Python oficial e leve como base.
FROM python:3.10-slim

# Definir o diretório de trabalho dentro do contêiner.
WORKDIR /app

# Copiar apenas o arquivo de dependências primeiro.
# Isso aproveita o cache do Docker: as dependências só serão reinstaladas se o requirements.txt mudar.
COPY requirements.txt .

# Instalar as dependências.
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código do aplicativo.
# Note que NÃO estamos copiando 'config.yaml'. Ele será injetado em tempo de execução.
COPY app.py .
COPY dadosregiao.csv .

# Expor a porta que o Streamlit usa.
EXPOSE 8501

# Comando para executar o aplicativo quando o contêiner iniciar.
# Os argumentos garantem que o Streamlit seja acessível externamente.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
