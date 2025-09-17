import streamlit_authenticator as stauth

hashed_passwords = stauth.Hasher(['Julia123']).generate()
with open('hashed_password.txt', 'w') as f:
    f.write(hashed_passwords[0])
