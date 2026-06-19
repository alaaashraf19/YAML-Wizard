import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
load_dotenv()
FERNET_KEY=os.getenv("FERNET_KEY")

if FERNET_KEY is None:
    raise ValueError("FERNET_KEY is missing from environment variables")
fernet = Fernet(FERNET_KEY.encode())


def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()
