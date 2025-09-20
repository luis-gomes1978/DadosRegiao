import pandas as pd
import numpy as np
from datetime import datetime
import logging
from src.constants import MAPA_REGIOES, CARGOS_GERENCIAIS, BAIRROS_RIO, OUTRAS_LOCALIDADES

logger = logging.getLogger(__name__)

def _calculate_age(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a idade dos colaboradores com base na data de nascimento."""
    df['DT_NASCIMENTO'] = pd.to_datetime(df['DT_NASCIMENTO'], format='%d/%m/%Y', errors='coerce')
    age_in_years = (datetime.now() - df['DT_NASCIMENTO']).dt.days / 365.25
    df['IDADE'] = np.floor(age_in_years).astype('Int64')
    return df

def _map_brazilian_regions(df: pd.DataFrame) -> pd.DataFrame:
    """Mapeia o estado para a região geográfica correspondente."""
    df['REGIAO'] = df['ESTADO'].map(MAPA_REGIOES)
    return df

def _classify_job_type(df: pd.DataFrame) -> pd.DataFrame:
    """Classifica os cargos em 'Gerencial' ou 'Operacional'."""
    df['TIPO_CARGO'] = df['FUNÇÃO'].apply(
        lambda x: 'Gerencial' if any(cargo in str(x).upper() for cargo in CARGOS_GERENCIAIS) else 'Operacional'
    )
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
        df['latitude'] = np.nan
        df['longitude'] = np.nan

    # Adiciona ruído apenas às coordenadas válidas para evitar sobreposição
    valid_coords_mask = df['latitude'].notna() & df['longitude'].notna()
    
    np.random.seed(0)
    noise_lat = np.random.normal(0, 0.01, size=valid_coords_mask.sum())
    noise_lon = np.random.normal(0, 0.01, size=valid_coords_mask.sum())
    df.loc[valid_coords_mask, 'latitude'] += noise_lat
    df.loc[valid_coords_mask, 'longitude'] += noise_lon
    return df

def _classify_special_locations(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa bairros do Rio e outras localidades específicas."""
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

def load_and_process_data(csv_path: str) -> pd.DataFrame:
    """
    Carrega e processa todos os dados em uma pipeline completa.
    Args:
        csv_path (str): O caminho para o arquivo CSV de dados.
    Returns:
        pd.DataFrame: O DataFrame processado e pronto para análise.
    """
    logger.info(f"Iniciando pipeline de processamento para {csv_path}")
    
    dtype_spec = {
        'CHAPA': 'str', 'UNIDADE': 'category', 'FUNÇÃO': 'category',
        'SEXO': 'category', 'BAIRRO': 'str', 'CIDADE': 'str',
        'ESTADO': 'category', 'CEP': 'str', 'CODSITUACAO': 'category',
        'PLANO': 'category', 'Status': 'category'
    }
    
    try:
        df = pd.read_csv(
            csv_path, sep=';', encoding='utf-8-sig', on_bad_lines='warn', dtype=dtype_spec
        )
        
        pipeline = [
            _calculate_age,
            _map_brazilian_regions,
            _classify_job_type,
            _merge_geo_coordinates,
            _classify_special_locations
        ]
        
        for func in pipeline:
            logger.info(f"Executando etapa: {func.__name__}")
            df = func(df)
            
        logger.info("Pipeline de processamento concluída com sucesso.")
        return df
    except FileNotFoundError:
        logger.error(f"Erro crítico: Arquivo de dados não encontrado em '{csv_path}'.")
        # Retorna um DataFrame vazio para evitar que a aplicação quebre
        return pd.DataFrame()