#!/bin/bash
set -e

echo "--- Iniciando Deploy para DigitalOcean Kubernetes ---"

# Variáveis de Configuração
CLUSTER_NAME="dadosregiao-cluster"
REGION="nyc3"
K8S_VERSION="1.33.1-do.3" # Versão recomendada (verificada via doctl kubernetes options versions)
NODE_SIZE="s-1vcpu-2gb"   # Menor tamanho disponível (verificado via doctl compute size list)
NODE_COUNT=1              # Número de nós para o pool inicial
LETSENCRYPT_EMAIL="seu-email@exemplo.com" # <-- IMPORTANTE: Troque pelo seu e-mail

# 1. Verificar autenticação (doctl e docker)
echo "1. Verificando autenticação do doctl e docker..."
doctl account get > /dev/null || { echo "Erro: doctl não autenticado. Execute 'doctl auth init'."; exit 1; }
docker info > /dev/null || { echo "Erro: Docker não está rodando ou não autenticado. Verifique o Docker Desktop."; exit 1; }
docker login > /dev/null || { echo "Erro: Docker Hub não autenticado. Execute 'docker login'."; exit 1; }

# 2. Verificar/Criar o Cluster Kubernetes
echo "2. Verificando a existência do cluster '$CLUSTER_NAME'..."
if ! doctl kubernetes cluster get "$CLUSTER_NAME" > /dev/null 2>&1; then
    echo "   Cluster não encontrado. Criando um novo cluster (isso pode levar alguns minutos)..."
    doctl kubernetes cluster create "$CLUSTER_NAME" \
        --region "$REGION" \
        --version "$K8S_VERSION" \
        --node-pool "name=default-pool;size=$NODE_SIZE;count=$NODE_COUNT" \
        --wait
    echo "   Cluster '$CLUSTER_NAME' criado com sucesso."
else
    echo "   Cluster '$CLUSTER_NAME' já existe. Reutilizando."
fi

# 3. Configurar kubectl para acessar o novo cluster
echo "3. Configurando kubectl para o cluster..."
doctl kubernetes cluster kubeconfig save "$CLUSTER_NAME"

# 3.1. Instalar NGINX Ingress Controller (se necessário)
echo "3.1. Verificando/Instalando o NGINX Ingress Controller..."
if ! kubectl get namespace ingress-nginx > /dev/null 2>&1; then
    echo "   Instalando NGINX Ingress Controller (isso criará um Load Balancer)..."
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.1/deploy/static/provider/do/deploy.yaml
    echo "   Aguardando o Ingress Controller ficar pronto..."
    kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=5m
else
    echo "   NGINX Ingress Controller já instalado."
fi

# 3.1.1. Garantir que o PROXY protocol esteja desativado para evitar erros de 'broken header'
echo "3.1.1. Verificando e ajustando a configuração do NGINX Ingress..."
if kubectl get configmap -n ingress-nginx ingress-nginx-controller -o jsonpath='{.data.use-proxy-protocol}' | grep -q "true"; then
    kubectl patch configmap -n ingress-nginx ingress-nginx-controller --type merge -p '{"data":{"use-proxy-protocol":"false"}}'
    echo "      PROXY protocol desativado. Reiniciando o controller para aplicar a mudança..."
    kubectl delete pod -n ingress-nginx -l app.kubernetes.io/component=controller
fi

# 3.2. Instalar Cert-Manager (se necessário)
echo "3.2. Verificando/Instalando o Cert-Manager..."
if ! kubectl get namespace cert-manager > /dev/null 2>&1; then
    echo "   Instalando Cert-Manager..."
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.1/cert-manager.yaml
    echo "   Aguardando o Cert-Manager ficar pronto..."
    kubectl wait --namespace cert-manager --for=condition=ready pod --selector=app.kubernetes.io/instance=cert-manager --timeout=5m
else
    echo "   Cert-Manager já instalado."
fi

# Gerar uma tag única para a imagem usando o timestamp atual para garantir a atualização
IMAGE_TAG=$(date +%s)
IMAGE_NAME="luisgomes1978/dadosregiao:$IMAGE_TAG"

# 4. Construir a imagem Docker para AMD64
echo "4. Construindo imagem Docker com a tag única: $IMAGE_NAME"
docker build --no-cache --platform linux/amd64 -t "$IMAGE_NAME" .

# 5. Enviar a imagem para o Docker Hub
echo "5. Enviando imagem para o Docker Hub..."
docker push "$IMAGE_NAME"

# 5.5. Criar o Secret do Kubernetes a partir do config.yaml
echo "5.5. Criando/Atualizando o Secret do Kubernetes para o config.yaml..."
# Deleta o secret se ele já existir, para garantir que está sempre atualizado
kubectl delete secret dadosregiao-config --ignore-not-found=true
kubectl create secret generic dadosregiao-config --from-file=config.yaml=./config.yaml

# 6. Aplicar manifestos Kubernetes
echo "6. Aplicando manifestos no cluster..."

# Substitui o placeholder da imagem no deployment.yaml e aplica
# Isso garante que o Kubernetes use a nova imagem com a tag única
sed -e "s|__IMAGE_PLACEHOLDER__|$IMAGE_NAME|g" \
    -e "s|__DEPLOY_TIMESTAMP_PLACEHOLDER__|$IMAGE_TAG|g" \
    ../k8s/deployment.yaml | kubectl apply -f -

kubectl apply -f ../k8s/service.yaml -f ../k8s/ingress.yaml
# Substitui o e-mail no ClusterIssuer e aplica sem modificar o arquivo original
sed "s/seu-email@exemplo.com/$LETSENCRYPT_EMAIL/g" ../k8s/cluster-issuer.yaml | kubectl apply -f -

echo "7. Configurações de Ingress e Certificado aplicadas."
echo "   Aguarde alguns minutos para que o certificado seja emitido pelo Let's Encrypt."
echo "   Você pode verificar o status com: kubectl describe certificate dadosregiao-tls-secret"

# 8. Obter e exibir o IP do Load Balancer do Ingress
echo "8. Obtendo o IP do Load Balancer do Ingress Controller..."
INGRESS_IP=""
while [ -z "$INGRESS_IP" ]; do
    echo "   Aguardando o IP externo do Load Balancer do NGINX..."
    # O serviço do ingress-nginx pode demorar um pouco para obter um IP externo
    INGRESS_IP=$(kubectl get service -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)
    [ -z "$INGRESS_IP" ] && sleep 10
done

echo "--- Deploy Concluído! ---"
echo ""
echo "################################################################################"
echo "### AÇÃO MANUAL NECESSÁRIA ###"
echo ""
echo "   O IP do seu Load Balancer é: $INGRESS_IP"
echo ""
echo "   Vá ao seu provedor de DNS e garanta que o registro 'A' para"
echo "   'regiao.slggti.com.br' aponte para este IP."
echo ""
echo "################################################################################"
echo ""
echo "Após a emissão do certificado, sua aplicação estará acessível em: https://regiao.slggti.com.br"