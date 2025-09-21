# Documentação Completa: Dashboard de Análise de Colaboradores

## 1. Visão Geral do Projeto

Este projeto consiste em um dashboard interativo para a análise de dados de colaboradores, desenvolvido em Python com a biblioteca Streamlit. A aplicação conta com um sistema de autenticação de usuários para controle de acesso, foi totalmente conteinerizada com Docker e implantada em um cluster Kubernetes na DigitalOcean, com automação de deploy, segurança HTTPS e escalabilidade.

O objetivo é fornecer uma ferramenta visual para que gestores e analistas possam explorar dados demográficos e organizacionais da força de trabalho, aplicando filtros dinâmicos para obter insights.

---

## 2. Arquitetura da Solução

A arquitetura foi projetada para ser moderna, segura e escalável, seguindo as melhores práticas de DevOps e engenharia de nuvem.

**Fluxo de Tráfego do Usuário:**

```
Usuário (Navegador)
       |
       | HTTPS (Porta 443) - Domínio: regiao.slggti.com.br
       v
DigitalOcean Load Balancer (IP Público)
       |
       | Tráfego direcionado para o cluster
       v
NGINX Ingress Controller (Dentro do Cluster Kubernetes)
       |
       | 1. Terminação TLS (descriptografa o HTTPS)
       | 2. Roteamento baseado no domínio
       v
Service (dadosregiao-service)
       |
       | Roteamento interno para um pod saudável
       v
Pod (dadosregiao-deployment)
       |
       +--> Container Docker (luisgomes1978/dadosregiao)
            |
            +--> Aplicação Streamlit (app.py) rodando na porta 8501
```

---

## 3. Stack de Tecnologias

*   **Linguagem:** Python 3.11
*   **Análise de Dados:** Pandas, NumPy
*   **Frontend e Visualização:** Streamlit, Plotly
*   **Conteinerização:** Docker
*   **Orquestração:** Kubernetes (DigitalOcean Managed Kubernetes)
*   **Gateway de API / Roteamento:** NGINX Ingress Controller
*   **Segurança (HTTPS):** cert-manager com Let's Encrypt
*   **Automação de Deploy:** Shell Script (`deploy_to_do.sh`), `doctl`, `kubectl`

---

## 4. Estrutura do Projeto

Cada arquivo no repositório tem um propósito específico:

*   **`app.py`**: O ponto de entrada da aplicação Streamlit. Ele orquestra a interface do usuário, a lógica de negócio e o sistema de autenticação.
*   **`src/`**: Diretório que contém o código-fonte principal da aplicação.
    *   **`processing.py`**: Módulo com todas as funções de processamento e transformação de dados.
    *   **`constants.py`**: Centraliza constantes e grandes estruturas de dados, como mapeamentos de regiões e bairros.
*   **`requirements.txt`**: Lista todas as bibliotecas Python necessárias para a aplicação. É usado pelo Docker para construir um ambiente consistente.
*   **`data/dadosregiao.csv`**: A fonte de dados brutos utilizada pela aplicação. **Este diretório é ignorado pelo Git.**
*   **`config.yaml`**: Arquivo de configuração para credenciais de login (usado pelo `streamlit-authenticator`). **Este arquivo é sensível e não é enviado para o repositório Git.**
*   **`Dockerfile`**: A "receita" para construir a imagem Docker da aplicação. Define o ambiente, instala as dependências e especifica como executar a aplicação.
*   **`.dockerignore`**: Lista arquivos a serem ignorados durante a construção da imagem Docker, mantendo-a leve e segura.
*   **`.gitignore`**: Lista arquivos a serem ignorados pelo Git, como o `config.yaml` e o `generate_hash.py`, para evitar o vazamento de segredos.
*   **`generate_hash.py`**: Script auxiliar para gerar hashes de senhas para novos usuários do `streamlit-authenticator`. **Este arquivo é ignorado pelo Git.**
*   **`k8s/`**: Contém todos os manifestos do Kubernetes.
    *   `deployment.yaml`, `service.yaml`, `ingress.yaml`, `cluster-issuer.yaml`.
*   **`scripts/`**: Contém os scripts de automação.
    *   `deploy_to_do.sh`: Orquestra todo o processo de deploy.
    *   `delete_do_env.sh`: Script auxiliar para destruir o ambiente.
*   **`.github/workflows/deploy.yml`**: Define o pipeline de CI/CD para automação do deploy com GitHub Actions.

---

## 5. Lógica da Aplicação (`app.py`)

O código da aplicação é estruturado em um sistema de autenticação, uma pipeline de processamento de dados e uma seção de renderização da interface.

### 5.1. Autenticação de Usuários

A aplicação utiliza a biblioteca `streamlit-authenticator` para gerenciar o acesso dos usuários. As credenciais são configuradas no arquivo `config.yaml` (que não é versionado no Git por segurança).

*   **Configuração:** O `config.yaml` armazena nomes de usuário, emails, nomes e senhas (em formato hash). Ele também define configurações de cookie para reautenticação.
*   **Criação de Novos Usuários:** Para adicionar novos usuários, você deve:
    1.  Gerar o hash da senha usando o script auxiliar `generate_hash.py` (execute `python3 generate_hash.py` no terminal e siga as instruções).
    2.  Adicionar manualmente o novo usuário e o hash gerado ao arquivo `config.yaml`.
*   **Login e Logout:** A interface de login é exibida na área principal da aplicação. Após o login bem-sucedido, um botão de logout é disponibilizado na barra lateral.

### 5.2. Pipeline de Processamento de Dados

A função `load_and_process_data()`, otimizada com `@st.cache_data`, é executada apenas uma vez para carregar e transformar os dados. Ela chama uma série de sub-funções, cada uma com uma responsabilidade única:

1.  **Leitura Otimizada:** Carrega o `dadosregiao.csv` usando `pandas`, especificando tipos de dados (`dtype_spec`) para otimizar o uso de memória e tratando a codificação `utf-8-sig` para remover caracteres invisíveis (BOM).
2.  **`_calculate_age`**: Calcula a idade de cada colaborador de forma robusta, tratando datas de nascimento inválidas.
3.  **`_map_brazilian_regions`**: Mapeia o estado de cada colaborador para a sua respectiva região geográfica (Norte, Sudeste, etc.).
4.  **`_classify_job_type`**: Classifica as funções em "Gerencial" ou "Operacional" com base em uma lista de palavras-chave.
5.  **`_merge_geo_coordinates`**: Faz uma chamada de rede para um repositório público para obter as coordenadas de latitude e longitude de cada município. Possui tratamento de erro para o caso de falha de rede.
6.  **`_classify_special_locations`**: Agrupa bairros específicos do Rio de Janeiro em zonas (Zona Sul, Zona Norte, etc.) e outras localidades da Baixada Fluminense.

### 5.3. Interface do Usuário

*   **Barra Lateral de Filtros:** Renderiza múltiplos filtros interativos (`multiselect`, `slider`) que permitem ao usuário refinar o conjunto de dados exibido.
*   **KPIs Principais:** Exibe métricas chave, como "Total de Colaboradores" e "Idade Média", que são recalculadas dinamicamente com base nos filtros aplicados.
*   **Gráficos e Visualizações:** Utiliza a biblioteca Plotly para renderizar os gráficos. Uma função auxiliar `display_chart` é usada para evitar repetição de código.
*   **Tabela de Dados:** Exibe o DataFrame filtrado em uma tabela interativa.

---

## 6. Processo de Deploy (`deploy_to_do.sh`)

O script de deploy foi projetado para ser **idempotente**, ou seja, pode ser executado várias vezes para criar um ambiente do zero ou para atualizar um já existente.

1.  **Verificação de Pré-requisitos:** Confere se `doctl` e `docker` estão instalados e autenticados.
2.  **Gerenciamento do Cluster:** Verifica se o cluster Kubernetes já existe. Se não, cria um novo na DigitalOcean.
3.  **Instalação de Dependências do Cluster:** Verifica e instala o NGINX Ingress Controller e o `cert-manager`, caso ainda não estejam presentes.
4.  **Construção da Imagem:** Gera uma **tag única** para a imagem Docker (baseada no timestamp) e constrói a imagem usando `docker build --no-cache`. Isso garante que o Kubernetes sempre reconheça que há uma nova versão.
5.  **Publicação da Imagem:** Envia a nova imagem para o Docker Hub.
6.  **Gerenciamento de Segredos:** Cria ou atualiza um `Secret` no Kubernetes com o conteúdo do `config.yaml` local.
7.  **Aplicação dos Manifestos:** Usa `sed` para substituir o placeholder da imagem no `deployment.yaml` pela nova tag única e aplica todas as configurações (`Deployment`, `Service`, `Ingress`, `ClusterIssuer`) no cluster. A variável de ambiente `DEPLOY_TIMESTAMP` também é injetada no contêiner neste passo, garantindo que a data e hora do deploy sejam exibidas na aplicação.
8.  **Feedback ao Usuário:** Informa o IP do Load Balancer para que o DNS possa ser configurado.

---

## 7. Backlog de Melhorias Futuras

Este projeto possui uma base sólida e profissional. As sugestões abaixo representam os próximos passos lógicos para evoluir a aplicação, melhorar a manutenibilidade e adicionar novas capacidades.

### 7.1. Infraestrutura e DevOps

*   **Implementar um Pipeline de CI/CD:**
    *   **Descrição:** Automatizar todo o processo de deploy usando uma ferramenta como **GitHub Actions**. Um novo `push` para a branch `main` poderia automaticamente construir a imagem, enviá-la e atualizar a aplicação no Kubernetes.
    *   **Benefício:** Reduz o trabalho manual, elimina erros humanos e acelera a entrega de novas funcionalidades.

*   **Adicionar Monitoramento e Alertas:**
    *   **Descrição:** Integrar o cluster com ferramentas como **Prometheus** para coletar métricas (uso de CPU/memória, tráfego) e **Grafana** para criar dashboards de monitoramento. Configurar alertas (via Alertmanager) para notificar a equipe sobre problemas (ex: pod travando, uso de CPU muito alto).
    *   **Benefício:** Visibilidade proativa sobre a saúde e a performance da aplicação, permitindo resolver problemas antes que os usuários sejam impactados.

*   **Configurar Limites de Recursos e Auto-escalonamento (HPA):**
    *   **Descrição:** Definir `requests` e `limits` de CPU e memória no `deployment.yaml` para garantir a estabilidade do pod. Em seguida, implementar um **Horizontal Pod Autoscaler (HPA)** para criar automaticamente novas réplicas da aplicação quando o uso de CPU aumentar, e removê-las quando o tráfego diminuir.
    *   **Benefício:** Garante alta disponibilidade durante picos de uso e otimiza custos ao reduzir o número de pods em períodos de baixa demanda.

### 7.2. Arquitetura da Aplicação

*   **Migrar a Fonte de Dados para um Banco de Dados:**
    *   **Descrição:** Substituir a leitura do `dadosregiao.csv` por uma conexão a um banco de dados relacional (ex: **PostgreSQL**, gerenciado pela DigitalOcean).
    *   **Benefício:** Melhora drasticamente a escalabilidade, a performance de consultas e a capacidade de gerenciar os dados de forma segura e estruturada.

*   **Refatorar Constantes para Arquivos de Configuração:**
    *   **Descrição:** Mover os grandes dicionários, como `BAIRROS_RIO` e `mapa_regioes`, do `app.py` para arquivos de configuração externos (ex: `locations.json`). A aplicação leria esses arquivos na inicialização.
    *   **Benefício:** Deixa o código `app.py` mais limpo, focado na lógica, e facilita a atualização das listas de bairros/regiões sem precisar alterar o código da aplicação.

### 7.3. Qualidade de Código e Testes

*   **Implementar Testes Automatizados:**
    *   **Descrição:** Criar uma suíte de testes usando uma biblioteca como **Pytest**. Adicionar testes unitários para as funções de processamento de dados (ex: `_calculate_age`, `_classify_job_type`) para garantir que elas se comportem como esperado com diferentes tipos de entrada.
    *   **Benefício:** Aumenta a confiança para fazer futuras alterações no código, garantindo que novas funcionalidades não quebrem o que já existe.

*   **Adicionar Logging Estruturado:**
    *   **Descrição:** Melhorar o sistema de logging para registrar informações mais detalhadas e em um formato estruturado (como JSON), facilitando a busca e a análise em uma ferramenta centralizada de logs (como Loki ou a stack ELK).
    *   **Benefício:** Acelera drasticamente a depuração de problemas em produção.

---