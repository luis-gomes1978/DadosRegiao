import streamlit_authenticator as stauth
import getpass

def generate_hash():
    print("Digite a senha que deseja criptografar e pressione Enter: ")
    password = getpass.getpass()
    hasher = stauth.Hasher()
    hashed_password = hasher.hash(password)
    print("\nSenha hash gerada:")
    print(hashed_password)
    
    # Opcional: Salvar em um arquivo
    with open('hashed_password.txt', 'w') as f:
        f.write(hashed_password)
    print("\nHash salvo em 'hashed_password.txt'")

if __name__ == "__main__":
    generate_hash()
