
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime
import numpy as np
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

st.set_page_config(
    page_title="Dashboard de Análise de Colaboradores",
    page_icon=":bar_chart:",
    layout="wide",
)

# --- AUTHENTICATION ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

authenticator.login()

if st.session_state["authentication_status"]:
    authenticator.logout('Logout', 'main')

    # Carregar e preparar os dados
    @st.cache_data
    def load_data():
        df = pd.read_csv("dadosregiao.csv", sep=';')
        df['DT_NASCIMENTO'] = pd.to_datetime(df['DT_NASCIMENTO'], format='%d/%m/%Y')
        df['IDADE'] = (datetime.now() - df['DT_NASCIMENTO']).dt.days / 365.25
        df['IDADE'] = df['IDADE'].astype(int)

        # Criar coluna de Região
        mapa_regioes = {
            'AC': 'Norte', 'AP': 'Norte', 'AM': 'Norte', 'PA': 'Norte', 'RO': 'Norte', 'RR': 'Norte', 'TO': 'Norte',
            'AL': 'Nordeste', 'BA': 'Nordeste', 'CE': 'Nordeste', 'MA': 'Nordeste', 'PB': 'Nordeste', 'PE': 'Nordeste', 'PI': 'Nordeste', 'RN': 'Nordeste', 'SE': 'Nordeste',
            'DF': 'Centro-Oeste', 'GO': 'Centro-Oeste', 'MT': 'Centro-Oeste', 'MS': 'Centro-Oeste',
            'ES': 'Sudeste', 'MG': 'Sudeste', 'RJ': 'Sudeste', 'SP': 'Sudeste',
            'PR': 'Sul', 'RS': 'Sul', 'SC': 'Sul'
        }
        df['REGIAO'] = df['ESTADO'].map(mapa_regioes)

        # Criar coluna de Tipo de Cargo
        cargos_gerenciais = ['GERENTE', 'DIRETOR', 'CONTROLLER', 'CHEF EXECUTIVO DE COZINHA']
        df['TIPO_CARGO'] = df['FUNÇÃO'].apply(lambda x: 'Gerencial' if any(cargo in x.upper() for cargo in cargos_gerenciais) else 'Operacional')

        # Carregar dados de municípios para obter coordenadas
        df_municipios = pd.read_csv("https://raw.githubusercontent.com/kelvins/Municipios-Brasileiros/main/csv/municipios.csv")
        df_municipios = df_municipios.rename(columns={'nome': 'CIDADE', 'uf': 'ESTADO'})
        df = pd.merge(df, df_municipios[['CIDADE', 'latitude', 'longitude']], on='CIDADE', how='left')

        # Adicionar ruído aleatório às coordenadas
        np.random.seed(0)
        df['latitude'] += np.random.normal(0, 0.01, size=len(df))
        df['longitude'] += np.random.normal(0, 0.01, size=len(df))

        # Agrupar bairros do Rio de Janeiro por região
        # Refatorado para melhor legibilidade e manutenção
        BAIRROS_RIO = {
            'Rio_Zona Sul': {
                'BOTAFOGO', 'CATETE', 'COPACABANA', 'COSME VELHO', 'FLAMENGO', 'GÁVEA', 'GLÓRIA', 'HUMAITÁ', 'IPANEMA',
                'JARDIM BOTÂNICO', 'LAGOA', 'LARANJEIRAS', 'LEBLON', 'LEME', 'SÃO CONRADO', 'URCA', 'VIDIGAL'
            },
            'Rio_Centro': {
                'BONSUCESSO', 'BANCÁRIOS', 'CACUIA', 'CIDADE UNIVERSITÁRIA', 'COCOTÁ', 'FREGUESIA (ILHA)',
                'JARDIM CARIOCA', 'JARDIM GUANABARA', 'MONERÓ', 'PITANGUEIRAS', 'PRAIA DA BANDEIRA', 'RIBEIRA',
                'ZUMBI', 'CAJU', 'CATUMBI', 'CENTRO', 'CIDADE NOVA', 'ESTÁCIO', 'GAMBOA', 'LAPA', 'MANGUEIRA',
                'PAQUETÁ', 'RIO COMPRIDO', 'SANTA TERESA', 'SANTO CRISTO', 'SAÚDE', 'VASCO DA GAMA', 'GAMBOA/SAUDE',
                'GLORIA'
            },
            'Rio_Zona Norte': {
                'ABOLIÇÃO', 'ÁGUA SANTA', 'ACÁRI', 'ALDEIA CAMPISTA', 'ALTO DA BOA VISTA', 'ANCHIETA', 'ANDARAÍ',
                'BANGU', 'BARROS FILHO', 'BENTO RIBEIRO', 'BRÁS DE PINA', 'CACHAMBI', 'CAMPO DOS AFONSOS', 'CAMPINHO',
                'CASCADURA', 'CAVALCANTI', 'COELHO NETO', 'COLÉGIO', 'COMPLEXO DO ALEMÃO', 'CORDOVIL', 'COSTA BARROS',
                'DEL CASTILHO', 'DEODORO', 'ENCANTADO', 'ENGENHO DA RAINHA', 'ENGENHO DE DENTRO', 'ENGENHO NOVO',
                'GRAJAÚ', 'GUADALUPE', 'HIGIENÓPOLIS', 'HONÓRIO GURGEL', 'INHAÚMA', 'IRAJÁ', 'JACARÉ', 'JACAREZINHO',
                'JARDIM AMÉRICA', 'LINS DE VASCONCELOS', 'MADUREIRA', 'MAGALHÃES BASTOS', 'MARACANÃ', 'MARECHAL HERMES',
                'MARIA DA GRAÇA', 'MÉIER', 'OLARIA', 'OSWALDO CRUZ', 'PARADA DE LUCAS', 'PARQUE ANCHIETA',
                'PARQUE COLÚMBIA', 'PAVUNA', 'PACIÊNCIA', 'PADRE MIGUEL', 'PENHA', 'PENHA CIRCULAR', 'PIEDADE',
                'PILARES', 'PRAÇA DA BANDEIRA', 'PRAÇA SECA', 'QUINTINO BOCAIUVA', 'RAMOS', 'REALENGO', 'RIACHUELO',
                'RICARDO DE ALBUQUERQUE', 'ROCHA', 'ROCHA MIRANDA', 'SAMPAIO', 'SÃO FRANCISCO XAVIER', 'SENADOR CAMARÁ',
                'SENADOR VASCONCELOS', 'SANTÍSSIMO', 'TODOS OS SANTOS', 'TOMÁS COELHO', 'TURIAÇU', 'VILA DA PENHA',
                'VILA ISABEL', 'VILA KOSMOS', 'VILA MILITAR', 'VILA VALQUEIRE', 'VICENTE DE CARVALHO', 'VIGÁRIO GERAL',
                'VISTA ALEGRE', 'TIJUCA', 'SAO CRISTOVAO', 'ROCINHA', 'ENGENHEIRO LEAL', 'MARE', 'OLINDA', 'ACARI',
                'MANGUINHOS', 'MARUREIRA', 'JACARE', 'COLEGIO', 'BAIRRO MEIER', 'QUINTINO', 'GALEÃO', 'PORTUGUESA',
                'TAUÁ', 'TUBIACANGA', 'BENFICA', 'HIGIENOPOLIS', 'MARÉ', 'TOMAS COELHO', 'MAGALHAES BASTOS'
            },
            'Rio_Zona Oeste': {
                'ANIL', 'BARRA DA TIJUCA', 'BARRA DE GUARATIBA', 'CAMORIM', 'CIDADE DE DEUS', 'CURICICA',
                'FREGUESIA (JACAREPAGUÁ)', 'GARDÊNIA AZUL', 'GRUMARI', 'ITANHANGÁ', 'JACAREPAGUÁ', 'JOÁ',
                'PECHINCHA', 'RECREIO DOS BANDEIRANTES', 'TANQUE', 'TAQUARA', 'VARGEM GRANDE', 'VARGEM PEQUENA',
                'CAMPO GRANDE', 'SANTISSIMO', 'SENADOR CAMARA', 'COSMOS', 'INHOAIBA', 'GUARATIBA', 'SEPETIBA',
                'SANTA CRUZ', 'AUGUSTO VASCONCELOS', 'RIO DAS PEDRAS', 'MUZEMA', 'CHATUBA', 'GARDENIA AZUL',
                'JACAREPAGUA', 'BARBANTE', 'FREGUESIA'
            }
        }

        # Mapeamento para outras cidades/bairros específicos
        OUTRAS_LOCALIDADES = {
            'NOVA ERA': 'Nova Iguaçu', 'AUSTIN': 'Nova Iguaçu', 'XANGRILÁ': 'Belford Roxo',
            'MESQUITA': 'Mesquita', 'SANTO EXPEDITO': 'Queimados', 'NILÓPOLIS': 'Nilópolis'
        }

        def classificar_regiao_rio(row):
            bairro = str(row['BAIRRO']).upper().strip()
            cidade = str(row['CIDADE'])

            if cidade == 'Rio de Janeiro':
                for regiao, bairros_na_regiao in BAIRROS_RIO.items():
                    if bairro in bairros_na_regiao:
                        return regiao
                return 'Rio_Outra'

            if bairro in OUTRAS_LOCALIDADES:
                return OUTRAS_LOCALIDADES[bairro]

            return cidade

        df['REGIAO_CIDADE'] = df.apply(classificar_regiao_rio, axis=1)

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
    idade_min = int(df['IDADE'].min())
    idade_max = int(df['IDADE'].max())
    faixa_etaria = st.sidebar.slider("Faixa Etária", idade_min, idade_max, (idade_min, idade_max))

    # --- Filtragem do DataFrame ---
    df_filtrado = df[
        (df['REGIAO'].isin(regioes_selecionadas)) &
        (df['REGIAO_CIDADE'].isin(regioes_cidade_selecionadas)) &
        (df['ESTADO'].isin(estados_selecionados)) &
        (df['SEXO'].isin(generos_selecionados)) &
        (df['Status'].isin(status_selecionados)) &
        (df['PLANO'].isin(planos_selecionados)) &
        (df['TIPO_CARGO'].isin(tipos_cargo_selecionados)) &
        (df['IDADE'] >= faixa_etaria[0]) &
        (df['IDADE'] <= faixa_etaria[1])
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

    # --- Análises Visuais com Plotly ---
    st.subheader("Gráficos")

    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        if not df_filtrado.empty:
            dist_regiao = df_filtrado['REGIAO'].value_counts().reset_index()
            dist_regiao.columns = ['REGIAO', 'Quantidade']
            grafico_regiao = px.bar(dist_regiao, x='REGIAO', y='Quantidade', title='Distribuição de Funcionários por Região')
            st.plotly_chart(grafico_regiao, use_container_width=True)
        else:
            st.warning("Nenhum dado para exibir no gráfico de região.")

    with col_graf2:
        if not df_filtrado.empty:
            grafico_faixa_etaria = px.histogram(df_filtrado, x='IDADE', nbins=20, title='Faixa Etária dos Colaboradores')
            st.plotly_chart(grafico_faixa_etaria, use_container_width=True)
        else:
            st.warning("Nenhum dado para exibir no gráfico de faixa etária.")

    col_graf3, col_graf4, col_graf5 = st.columns(3)

    with col_graf3:
        if not df_filtrado.empty:
            dist_genero = df_filtrado['SEXO'].value_counts().reset_index()
            dist_genero.columns = ['SEXO', 'Quantidade']
            grafico_genero = px.pie(dist_genero, names='SEXO', values='Quantidade', title='Distribuição de Gênero', hole=0.5)
            grafico_genero.update_traces(textinfo='percent+label')
            st.plotly_chart(grafico_genero, use_container_width=True)
        else:
            st.warning("Nenhum dado para exibir no gráfico de gênero.")

    with col_graf4:
        if not df_filtrado.empty:
            dist_status = df_filtrado['Status'].value_counts().reset_index()
            dist_status.columns = ['Status', 'Quantidade']
            grafico_status = px.pie(dist_status, names='Status', values='Quantidade', title='Status dos Colaboradores', hole=0.5)
            grafico_status.update_traces(textinfo='percent+label')
            st.plotly_chart(grafico_status, use_container_width=True)
        else:
            st.warning("Nenhum dado para exibir no gráfico de status.")

    with col_graf5:
        if not df_filtrado.empty:
            dist_plano = df_filtrado['PLANO'].value_counts().reset_index()
            dist_plano.columns = ['PLANO', 'Quantidade']
            grafico_plano = px.pie(dist_plano, names='PLANO', values='Quantidade', title='Colaboradores por Plano', hole=0.5)
            grafico_plano.update_traces(textinfo='percent+label')
            st.plotly_chart(grafico_plano, use_container_width=True)
        else:
            st.warning("Nenhum dado para exibir no gráfico de planos.")

    # --- Mapa de Calor do Brasil ---
    st.subheader("Distribuição de Colaboradores por Cidade")
    if not df_filtrado.empty:
        mapa = px.density_mapbox(
            df_filtrado,
            lat="latitude",
            lon="longitude",
            radius=10,
            zoom=3,
            height=600,
            mapbox_style="open-street-map"
        )
        mapa.update_layout(title='Mapa de Calor de Colaboradores no Brasil')
        st.plotly_chart(mapa, use_container_width=True)
    else:
        st.warning("Nenhum colaborador encontrado com os filtros selecionados.")


    # --- Tabela de Dados Detalhados ---
    st.subheader("Dados Detalhados")
    if not df_filtrado.empty:
        st.dataframe(df_filtrado)
    else:
        st.warning("Nenhum dado para exibir com os filtros selecionados.")

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')
