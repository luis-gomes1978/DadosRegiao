import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime, timezone, timedelta
import numpy as np
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import requests
import time
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configurações da Página e Timestamp ---
st.set_page_config(
    page_title="Dashboard de Análise de Colaboradores",
    page_icon=":bar_chart:",
    layout="wide",
)

# Adiciona um timestamp para verificar a atualização do deploy
sao_paulo_tz = timezone(timedelta(hours=-3))
now = datetime.now(sao_paulo_tz)
st.markdown(f"<p style='text-align: right; color: grey;'>Página gerada em: {now.strftime('%d/%m/%Y %H:%M:%S')}</p>", unsafe_allow_html=True)


# --- MODO DE DESENVOLVIMENTO ---
# Mude para False para ativar a tela de login para produção.
DEV_MODE = False

# --- AUTHENTICATION ---
try:
    # Carregamento do arquivo de configuração.
    # O caminho 'config.yaml' corresponde ao 'mountPath' definido no deployment.yaml,
    # garantindo que estamos lendo o arquivo do Secret do Kubernetes.
    with open('config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)

    # Inicialização do autenticador
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized']
    )

    # Login
    name, authentication_status, username = authenticator.login('Login', 'main')

except FileNotFoundError:
    st.error("Arquivo de configuração 'config.yaml' não encontrado. A autenticação não pode ser inicializada.")
    st.stop() # Interrompe a execução se o arquivo de config não existe

# A lógica principal do app roda se a autenticação for bem-sucedida OU se estiver em modo de desenvolvimento
if st.session_state.get("authentication_status") or DEV_MODE:
    # Mostra o botão de logout apenas se a autenticação estiver ativa (não em DEV_MODE)
    if not DEV_MODE:
        authenticator.logout('Logout', 'sidebar')
        st.sidebar.title(f'Bem-vindo(a) *{name}*')
    
    # --- Funções de Processamento de Dados ---
    def _calculate_age(df: pd.DataFrame) -> pd.DataFrame:
        """Calcula a idade dos colaboradores com base na data de nascimento."""
        df['DT_NASCIMENTO'] = pd.to_datetime(df['DT_NASCIMENTO'], format='%d/%m/%Y', errors='coerce')
        # Cálculo robusto da idade, arredondando para baixo para garantir a conversão segura para inteiro.
        age_in_years = (datetime.now() - df['DT_NASCIMENTO']).dt.days / 365.25
        df['IDADE'] = np.floor(age_in_years).astype('Int64')
        return df

    def _map_brazilian_regions(df: pd.DataFrame) -> pd.DataFrame:
        """Mapeia o estado para a região geográfica correspondente."""
        mapa_regioes = {
            'AC': 'Norte', 'AP': 'Norte', 'AM': 'Norte', 'PA': 'Norte', 'RO': 'Norte', 'RR': 'Norte', 'TO': 'Norte',
            'AL': 'Nordeste', 'BA': 'Nordeste', 'CE': 'Nordeste', 'MA': 'Nordeste', 'PB': 'Nordeste', 'PE': 'Nordeste', 'PI': 'Nordeste', 'RN': 'Nordeste', 'SE': 'Nordeste',
            'DF': 'Centro-Oeste', 'GO': 'Centro-Oeste', 'MT': 'Centro-Oeste', 'MS': 'Centro-Oeste',
            'ES': 'Sudeste', 'MG': 'Sudeste', 'RJ': 'Sudeste', 'SP': 'Sudeste',
            'PR': 'Sul', 'RS': 'Sul', 'SC': 'Sul'
        }
        df['REGIAO'] = df['ESTADO'].map(mapa_regioes)
        return df

    def _classify_job_type(df: pd.DataFrame) -> pd.DataFrame:
        """Classifica os cargos em 'Gerencial' ou 'Operacional'."""
        cargos_gerenciais = ['GERENTE', 'DIRETOR', 'CONTROLLER', 'CHEF EXECUTIVO DE COZINHA', 'SUPERVISOR']
        df['TIPO_CARGO'] = df['FUNÇÃO'].apply(lambda x: 'Gerencial' if any(cargo in str(x).upper() for cargo in cargos_gerenciais) else 'Operacional')
        return df

    def _merge_geo_coordinates(df: pd.DataFrame) -> pd.DataFrame:
        """Busca e adiciona coordenadas geográficas com base na cidade."""
        try:
            logger.info("Buscando coordenadas geográficas de municípios...")
            df_municipios = pd.read_csv("https://raw.githubusercontent.com/kelvins/Municipios-Brasileiros/main/csv/municipios.csv")
            df_municipios = df_municipios.rename(columns={'nome': 'CIDADE', 'uf': 'ESTADO'})
            df = pd.merge(df, df_municipios[['CIDADE', 'latitude', 'longitude']], on='CIDADE', how='left')
            logger.info("Coordenadas geográficas mescladas com sucesso.")
        except Exception as e:
            logger.error(f"Falha ao buscar ou mesclar coordenadas geográficas: {e}")
            # Cria colunas vazias para que o resto do app não falhe
            df['latitude'] = 0
            df['longitude'] = 0

        # Preenche coordenadas ausentes com 0 para evitar erros no mapa
        df['latitude'].fillna(0, inplace=True)
        df['longitude'].fillna(0, inplace=True)

        # Adiciona ruído aleatório para evitar sobreposição exata no mapa
        np.random.seed(0)
        noise_lat = np.random.normal(0, 0.01, size=len(df))
        noise_lon = np.random.normal(0, 0.01, size=len(df))
        df['latitude'] += noise_lat
        df['longitude'] += noise_lon
        return df

    def _classify_special_locations(df: pd.DataFrame) -> pd.DataFrame:
        """Agrupa bairros do Rio e outras localidades específicas."""
        BAIRROS_RIO = {
            'Rio_Zona Sul': {'BOTAFOGO', 'CATETE', 'COPACABANA', 'COSME VELHO', 'FLAMENGO', 'GÁVEA', 'GLÓRIA', 'HUMAITÁ', 'IPANEMA', 'JARDIM BOTÂNICO', 'LAGOA', 'LARANJEIRAS', 'LEBLON', 'LEME', 'SÃO CONRADO', 'URCA', 'VIDIGAL'},
            'Rio_Centro': {'BONSUCESSO', 'BANCÁRIOS', 'CACUIA', 'CIDADE UNIVERSITÁRIA', 'COCOTÁ', 'FREGUESIA (ILHA)', 'JARDIM CARIOCA', 'JARDIM GUANABARA', 'MONERÓ', 'PITANGUEIRAS', 'PRAIA DA BANDEIRA', 'RIBEIRA', 'ZUMBI', 'CAJU', 'CATUMBI', 'CENTRO', 'CIDADE NOVA', 'ESTÁCIO', 'GAMBOA', 'LAPA', 'MANGUEIRA', 'PAQUETÁ', 'RIO COMPRIDO', 'SANTA TERESA', 'SANTO CRISTO', 'SAÚDE', 'VASCO DA GAMA', 'GAMBOA/SAUDE', 'GLORIA'},
            'Rio_Zona Norte': {'ABOLIÇÃO', 'ÁGUA SANTA', 'ACÁRI', 'ALDEIA CAMPISTA', 'ALTO DA BOA VISTA', 'ANCHIETA', 'ANDARAÍ', 'BANGU', 'BARROS FILHO', 'BENTO RIBEIRO', 'BRÁS DE PINA', 'CACHAMBI', 'CAMPO DOS AFONSOS', 'CAMPINHO', 'CASCADURA', 'CAVALCANTI', 'COELHO NETO', 'COLÉGIO', 'COMPLEXO DO ALEMÃO', 'CORDOVIL', 'COSTA BARROS', 'DEL CASTILHO', 'DEODORO', 'ENCANTADO', 'ENGENHO DA RAINHA', 'ENGENHO DE DENTRO', 'ENGENHO NOVO', 'GRAJAÚ', 'GUADALUPE', 'HIGIENÓPOLIS', 'HONÓRIO GURGEL', 'INHAÚMA', 'IRAJÁ', 'JACARÉ', 'JACAREZINHO', 'JARDIM AMÉRICA', 'LINS DE VASCONCELOS', 'MADUREIRA', 'MAGALHÃES BASTOS', 'MARACANÃ', 'MARECHAL HERMES', 'MARIA DA GRAÇA', 'MÉIER', 'OLARIA', 'OSWALDO CRUZ', 'PARADA DE LUCAS', 'PARQUE ANCHIETA', 'PARQUE COLÚMBIA', 'PAVUNA', 'PACIÊNCIA', 'PADRE MIGUEL', 'PENHA', 'PENHA CIRCULAR', 'PIEDADE', 'PILARES', 'PRAÇA DA BANDEIRA', 'PRAÇA SECA', 'QUINTINO BOCAIUVA', 'RAMOS', 'REALENGO', 'RIACHUELO', 'RICARDO DE ALBUQUERQUE', 'ROCHA', 'ROCHA MIRANDA', 'SAMPAIO', 'SÃO FRANCISCO XAVIER', 'SENADOR CAMARÁ', 'SENADOR VASCONCELOS', 'SANTÍSSIMO', 'TODOS OS SANTOS', 'TOMÁS COELHO', 'TURIAÇU', 'VILA DA PENHA', 'VILA ISABEL', 'VILA KOSMOS', 'VILA MILITAR', 'VILA VALQUEIRE', 'VICENTE DE CARVALHO', 'VIGÁRIO GERAL', 'VISTA ALEGRE', 'TIJUCA', 'SAO CRISTOVAO', 'ROCINHA', 'ENGENHEIRO LEAL', 'MARE', 'OLINDA', 'ACARI', 'MANGUINHOS', 'MARUREIRA', 'JACARE', 'COLEGIO', 'BAIRRO MEIER', 'QUINTINO', 'GALEÃO', 'PORTUGUESA', 'TAUÁ', 'TUBIACANGA', 'BENFICA', 'HIGIENOPOLIS', 'MARÉ', 'TOMAS COELHO', 'MAGALHAES BASTOS'},
            'Rio_Zona Oeste': {'ANIL', 'BARRA DA TIJUCA', 'BARRA DE GUARATIBA', 'CAMORIM', 'CIDADE DE DEUS', 'CURICICA', 'FREGUESIA (JACAREPAGUÁ)', 'GARDÊNIA AZUL', 'GRUMARI', 'ITANHANGÁ', 'JACAREPAGUÁ', 'JOÁ', 'PECHINCHA', 'RECREIO DOS BANDEIRANTES', 'TANQUE', 'TAQUARA', 'VARGEM GRANDE', 'VARGEM PEQUENA', 'CAMPO GRANDE', 'SANTISSIMO', 'SENADOR CAMARA', 'COSMOS', 'INHOAIBA', 'GUARATIBA', 'SEPETIBA', 'SANTA CRUZ', 'AUGUSTO VASCONCELOS', 'RIO DAS PEDRAS', 'MUZEMA', 'CHATUBA', 'GARDENIA AZUL', 'JACAREPAGUA', 'BARBANTE', 'FREGUESIA'}
        }
        OUTRAS_LOCALIDADES = {
            'NOVA ERA': 'Nova Iguaçu', 'AUSTIN': 'Nova Iguaçu', 'XANGRILÁ': 'Belford Roxo',
            'MESQUITA': 'Mesquita', 'SANTO EXPEDITO': 'Queimados', 'NILÓPOLIS': 'Nilópolis'
        }

        def classificar(row):
            bairro = str(row['BAIRRO']).upper().strip()
            if row['CIDADE'] == 'Rio de Janeiro':
                for regiao, bairros_na_regiao in BAIRROS_RIO.items():
                    if bairro in bairros_na_regiao:
                        return regiao
                return 'Rio_Outra'
            return OUTRAS_LOCALIDADES.get(bairro, row['CIDADE'])

        df['REGIAO_CIDADE'] = df.apply(classificar, axis=1)
        return df

    @st.cache_data
    def load_data():
        """Carrega e processa todos os dados em uma pipeline."""
        # Leitura robusta do CSV, lidando com a codificação 'utf-8-sig' que remove o BOM
        # e otimizando o uso de memória com dtypes.
        dtype_spec = {
            'CHAPA': 'str',
            'UNIDADE': 'category',
            'FUNÇÃO': 'category',
            'SEXO': 'category',
            'BAIRRO': 'str',
            'CIDADE': 'str',
            'ESTADO': 'category',
            'CEP': 'str',
            'CODSITUACAO': 'category',
            'PLANO': 'category',
            'Status': 'category'
        }
        df = pd.read_csv(
            "dadosregiao.csv", sep=';', encoding='utf-8-sig', on_bad_lines='warn', dtype=dtype_spec
        )
        df = _calculate_age(df)
        df = _map_brazilian_regions(df)
        df = _classify_job_type(df)
        df = _merge_geo_coordinates(df)
        df = _classify_special_locations(df)
        return df

    df = load_data()

    # --- Barra Lateral (Filtros) ---
    st.sidebar.header("🔍 Filtros")

    # Filtro por Região
    regioes_disponiveis = sorted(df['REGIAO'].dropna().unique())
    regioes_selecionadas = st.sidebar.multiselect("Região", regioes_disponiveis, default=regioes_disponiveis)

    # Filtro por Região da Cidade
    regioes_cidade_disponiveis = sorted(df['REGIAO_CIDADE'].dropna().unique())
    regioes_cidade_selecionadas = st.sidebar.multiselect("Localização", regioes_cidade_disponiveis, default=regioes_cidade_disponiveis)

    # Filtro por Estado
    estados_disponiveis = sorted(df['ESTADO'].unique())
    estados_selecionados = st.sidebar.multiselect("Estado", estados_disponiveis, default=estados_disponiveis)

    # Filtro por Gênero
    generos_disponiveis = sorted(df['SEXO'].unique())
    generos_selecionados = st.sidebar.multiselect("Gênero", generos_disponiveis, default=generos_disponiveis)

    # Filtro por Status
    status_disponiveis = sorted(df['Status'].unique())
    status_selecionados = st.sidebar.multiselect("Status", status_disponiveis, default=status_disponiveis)

    # Filtro por Plano
    planos_disponiveis = sorted(df['PLANO'].unique())
    planos_selecionados = st.sidebar.multiselect("Plano", planos_disponiveis, default=planos_disponiveis)

    # Filtro por Tipo de Cargo
    tipos_cargo_disponiveis = sorted(df['TIPO_CARGO'].unique())
    tipos_cargo_selecionados = st.sidebar.multiselect("Tipo de Cargo", tipos_cargo_disponiveis, default=tipos_cargo_disponiveis)

    # Filtro por Faixa Etária
    # Tratamento robusto para o caso de não haver idades válidas
    if not df['IDADE'].dropna().empty:
        idade_min = int(df['IDADE'].dropna().min())
        idade_max = int(df['IDADE'].dropna().max())
        faixa_etaria = st.sidebar.slider("Faixa Etária", idade_min, idade_max, (idade_min, idade_max))
    else:
        st.sidebar.warning("Nenhuma idade válida para filtrar.")
        faixa_etaria = (0, 100) # Define um padrão para evitar erro

    # --- Filtragem do DataFrame ---
    df_filtrado = df[
        (df['REGIAO'].isin(regioes_selecionadas)) &
        (df['REGIAO_CIDADE'].isin(regioes_cidade_selecionadas)) &
        (df['ESTADO'].isin(estados_selecionados)) &
        (df['SEXO'].isin(generos_selecionados)) &
        (df['Status'].isin(status_selecionados)) &
        (df['PLANO'].isin(planos_selecionados)) &
        (df['TIPO_CARGO'].isin(tipos_cargo_selecionados)) &
        # Filtragem robusta de idade, ignorando valores nulos para evitar erros
        (df['IDADE'].notna() &
         (df['IDADE'] >= faixa_etaria[0]) &
         (df['IDADE'] <= faixa_etaria[1]))
    ]

    # --- Conteúdo Principal ---
    st.title("📊 Dashboard de Análise de Colaboradores")
    st.markdown("Explore os dados dos colaboradores. Utilize os filtros à esquerda para refinar sua análise.")

    # --- Métricas Principais (KPIs) ---
    st.subheader("Métricas Gerais")

    if not df_filtrado.empty:
        total_colaboradores = df_filtrado.shape[0]
        idade_media = int(df_filtrado['IDADE'].mean())
    else:
        total_colaboradores = 0
        idade_media = 0

    col1, col2 = st.columns(2)
    col1.metric("Total de Colaboradores", f"{total_colaboradores:,}")
    col2.metric("Idade Média", f"{idade_media} anos")

    st.markdown("---")

    # --- Função Auxiliar para Gráficos ---
    def display_chart(chart_function, data, title, **kwargs):
        """Função auxiliar para exibir um gráfico ou um aviso se não houver dados."""
        st.subheader(title)
        if not data.empty:
            fig = chart_function(data, **kwargs)
            # Aplica configurações específicas para gráficos de pizza
            if 'hole' in kwargs:
                fig.update_traces(textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"Nenhum dado para exibir no gráfico: {title}")

    # --- Análises Visuais com Plotly ---
    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        dist_regiao = df_filtrado['REGIAO'].value_counts().reset_index(name='Quantidade')
        display_chart(px.bar, dist_regiao, title="Distribuição por Região", x='REGIAO', y='Quantidade')

    with col_graf2:
        display_chart(px.histogram, df_filtrado, title="Faixa Etária dos Colaboradores", x='IDADE', nbins=20)

    col_graf3, col_graf4, col_graf5 = st.columns(3)

    with col_graf3:
        dist_genero = df_filtrado['SEXO'].value_counts().reset_index(name='Quantidade')
        display_chart(px.pie, dist_genero, title="Distribuição de Gênero", names='SEXO', values='Quantidade', hole=0.5)

    with col_graf4:
        dist_status = df_filtrado['Status'].value_counts().reset_index(name='Quantidade')
        display_chart(px.pie, dist_status, title="Status dos Colaboradores", names='Status', values='Quantidade', hole=0.5)

    with col_graf5:
        dist_plano = df_filtrado['PLANO'].value_counts().reset_index(name='Quantidade')
        display_chart(px.pie, dist_plano, title="Colaboradores por Plano", names='PLANO', values='Quantidade', hole=0.5)

    # --- Mapa de Calor do Brasil ---
    st.subheader("Distribuição de Colaboradores por Cidade")
    try:
        if not df_filtrado.empty:
            fig_mapa = px.density_map(df_filtrado,
                                    lat="latitude",
                                    lon="longitude",
                                    radius=10,
                                    zoom=3,
                                    height=600)
            # A forma correta de definir o estilo do mapa é através do update_layout
            fig_mapa.update_layout(mapbox_style="open-street-map")
            st.plotly_chart(fig_mapa, use_container_width=True)
        else:
            st.warning("Nenhum dado para exibir no mapa.")
    except Exception as e:
        st.error(f"Ocorreu um erro ao gerar o mapa de calor. A equipe de desenvolvimento já foi notificada.")
        logger.error(f"Erro no mapa de calor: {e}")

    # --- Tabela de Dados Detalhados ---
    st.subheader("Dados Detalhados")
    if not df_filtrado.empty:
        st.dataframe(df_filtrado)
    else:
        st.warning("Nenhum dado para exibir com os filtros selecionados.")

# Mensagens de erro/aviso para o processo de login
elif st.session_state.get("authentication_status") is False:
    st.error('Usuário ou senha incorretos.')
elif st.session_state.get("authentication_status") is None:
    st.warning('Por favor, insira seu usuário e senha.')
