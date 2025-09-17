import requests
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_connectivity():
    """Verifica se há conexão com a internet"""
    try:
        requests.get("http://google.com", timeout=5)
        return True
    except requests.RequestException:
        logger.error("Sem conexão com a internet")
        return False

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def make_request(url, timeout=10):
    """Faz requisição com retry automático"""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logger.error(f"Erro na requisição: {str(e)}")
        raise
