#!/bin/bash
set -e

echo "--- Iniciando Deploy para DigitalOcean Kubernetes ---"

# Variáveis de Configuração
CLUSTER_NAME="dadosregiao-cluster"
REGION="nyc3"
K8S_VERSION="1.33.1-do.3" # Versão recomendada (verificada via doctl kubernetes options versions)
NODE_SIZE="s-1vcpu-2gb"   # Menor tamanho disponível (verificado via doctl compute size list)
NODE_COUNT=1              # Número de nós para o pool inicial

# 1. Verificar autenticação (doctl e docker)
echo "1. Verificando autenticação do doctl e docker..."
doctl account get > /dev/null || { echo "Erro: doctl não autenticado. Execute 'doctl auth init'."; exit 1; }
docker info > /dev/null || { echo "Erro: Docker não está rodando ou não autenticado. Verifique o Docker Desktop."; exit 1; }
docker login > /dev/null || { echo "Erro: Docker Hub não autenticado. Execute 'docker login'."; exit 1; }

# 2. Criar Cluster Kubernetes no DigitalOcean (MANUALMENTE VIA PAINEL DO)
echo "2. Por favor, crie o cluster Kubernetes '$CLUSTER_NAME' manualmente no painel do DigitalOcean."
echo "   - Região: '$REGION'"
echo "   - Versão K8s: '$K8S_VERSION'"
echo "   - Node Pool: '$NODE_SIZE' com '$NODE_COUNT' nó(s)."
echo "Aguarde até que o cluster esteja '(running)' no painel."
read -p "Pressione Enter para continuar quando o cluster estiver pronto e copie o ID do cluster: " 

CLUSTER_ID=$(doctl kubernetes cluster list --output json | jq -r ".[] | select(.name==\"$CLUSTER_NAME\") | .id")

if [ -z "$CLUSTER_ID" ]; then
    echo "Erro: Não foi possível obter o ID do cluster '$CLUSTER_NAME'. Verifique se o nome está correto e se o cluster foi criado."
    exit 1
fi
echo "Cluster '$CLUSTER_NAME' encontrado com ID: $CLUSTER_ID"

# 3. Configurar kubectl para acessar o novo cluster
echo "3. Configurando kubectl para o cluster..."
doctl kubernetes cluster kubeconfig save $CLUSTER_ID

# 4. Construir a imagem Docker para AMD64
echo "4. Construindo imagem Docker para deploy (linux/amd64)..."
docker build --platform linux/amd64 -t luisgomes1978/dadosregiao:v1 .

# 5. Enviar a imagem para o Docker Hub
echo "5. Enviando imagem para o Docker Hub..."
docker push luisgomes1978/dadosregiao:v1

# 6. Aplicar manifestos Kubernetes
echo "6. Aplicando manifestos deployment.yaml e service.yaml no cluster..."
kubectl apply -f deployment.yaml -f service.yaml

# 7. Obter IP externo do Load Balancer
echo "7. Aguardando e obtendo IP externo do Load Balancer..."
ATTEMPTS=0
MAX_ATTEMPTS=30 # Tentar por 5 minutos (30 * 10 segundos)
IP=""
while [ -z "$IP" ] && [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    sleep 10
    IP=$(kubectl get services conversao-distancia-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
    ATTEMPTS=$((ATTEMPTS+1))
    echo "Aguardando IP... Tentativa $ATTEMPTS de $MAX_ATTEMPTS"
done

if [ -z "$IP" ]; then
    echo "Erro: Não foi possível obter o IP externo do Load Balancer após várias tentativas."
    echo "Verifique o status do serviço com 'kubectl get services dadosregiao-service'."
    exit 1
fi

echo "--- Deploy Concluído! ---"
echo "Sua aplicação está acessível em: http://$IP"