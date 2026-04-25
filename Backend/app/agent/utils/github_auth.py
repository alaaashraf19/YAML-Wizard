import requests
import time
from jose import  jwt
import os 
from dotenv import load_dotenv


load_dotenv()

APP_ID = os.getenv("APP_ID")
if not APP_ID:
    raise ValueError("APP_ID environment variable must be set")
PRIVATE_KEY = open("./private-key.pem").read()

def generate_jwt():#i am the github app
    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,#10 mins
        "iss": APP_ID#issuer
    }

    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")#this algorithm is required by github use private ky to sign the token



def get_installation_token(installation_id):#installation access token to act on a specific repo, expires in 1 hr 
    jwt_token = generate_jwt()

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }

    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"

    response = requests.post(url, headers=headers)
    return response.json()["token"] #if jwt is valid, app is installed, permissions are correct, we get the token, else we get an error response
