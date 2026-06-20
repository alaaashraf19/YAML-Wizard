import requests
import time
from jose import  jwt
import os 
from dotenv import load_dotenv
from fastapi import  HTTPException


load_dotenv()

APP_ID = os.getenv("APP_ID")
if not APP_ID:
    raise ValueError("APP_ID environment variable must be set")
PRIVATE_KEY = open("./private-key.pem").read()
if not PRIVATE_KEY:
    raise ValueError("Private key file not found or empty")

def generate_jwt():
    now = int(time.time())
    payload = {
        "iat": now - 30,
        "exp": now + 540,
        "iss": str(APP_ID)
    }

    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")


def get_installation_token(installation_id):#installation access token to act on a specific repo, expires in 1 hr 
    jwt_token = generate_jwt()

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }

    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    response = requests.post(url, headers=headers)
    if response.status_code != 201:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()["token"]