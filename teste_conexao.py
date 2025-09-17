import requests
import logging

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

def testar_conexao():
    print("Iniciando teste de conexão...")
    try:
        response = requests.get("http://google.com", timeout=5)
        print("Conexão bem sucedida!")
        return True
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return False

if __name__ == "__main__":
    testar_conexao()
