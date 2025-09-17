#!/bin/bash
set -e

echo "--- Iniciando Exclusão do Ambiente DigitalOcean ---"

# Variáveis de Configuração (devem corresponder ao script de deploy)
CLUSTER_NAME="dadosregiao-cluster"

# 1. Deletar o Cluster
echo "1. Deletando cluster '$CLUSTER_NAME'..."
echo "Isso pode levar alguns minutos."
# A flag -f pula a confirmação interativa.
doctl kubernetes cluster delete "$CLUSTER_NAME" -f

echo "--- Exclusão Concluída! ---"
echo "O cluster '$CLUSTER_NAME' foi deletado."