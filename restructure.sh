#!/bin/bash
set -e
echo "--- Iniciando a reestruturação do projeto para melhores práticas ---"

# 1. Criar a nova estrutura de diretórios
echo "1. Criando diretórios: src, data, k8s, scripts, .github/workflows"
mkdir -p src data k8s scripts .github/workflows

# 2. Mover arquivos para os diretórios corretos
echo "2. Movendo arquivos..."
# Usando '|| true' para não falhar se o arquivo já foi movido ou não existe
mv -f dadosregiao.csv data/ || true
mv -f cluster-issuer.yaml deployment.yaml ingress.yaml service.yaml k8s/ || true
mv -f deploy_to_do.sh delete_do_env.sh scripts/ || true
mv -f deploy.yml .github/workflows/ || true

# 3. Limpar arquivos de desenvolvimento e temporários
echo "3. Removendo arquivos desnecessários..."
rm -f main.py network_check.py teste_conexao.py generate_hash.py cluster-issuer.yaml.bak hashed_password.txt "Relatorio Plano.xlsx" README.md dockerfile

# 4. Consolidar documentação
echo "4. Renomeando DOCUMENTATION.md para README.md..."
mv -f DOCUMENTATION.md README.md || true

# 5. Criar arquivo __init__.py para o módulo src
touch src/__init__.py

echo "--- Reestruturação de arquivos e diretórios concluída! ---"
echo "Agora, por favor, atualize o conteúdo dos arquivos modificados conforme as instruções a seguir."

