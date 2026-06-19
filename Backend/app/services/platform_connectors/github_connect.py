import secrets
from fastapi import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
import httpx
import os
from dotenv import load_dotenv
from core.security import get_current_user
from models.platforms_model import GitHubConnection
from sqlalchemy import select
from services.platform_connectors.oauth_utils import encrypt_token, decrypt_token
from .oauth_connector import oauthConnector
from .oauth_utils import encrypt_token, decrypt_token

load_dotenv()

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")


class GithubConnector(oauthConnector):

    async def connect(self,request, db):

        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(401, "Login required")

        user = await get_current_user(db, token)

        #state part will be updatedd
        state = secrets.token_urlsafe(16)

        url = (
            "https://github.com/login/oauth/authorize"
            f"?client_id={GITHUB_CLIENT_ID}"
            f"&redirect_uri={GITHUB_REDIRECT_URI}"
            f"&scope=read:user user:email"
            f"&state={state}"
        )

        return RedirectResponse(url)



    async def callback(self, code, request, db):

        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(401, "Login required")

        user = await get_current_user(db, token)

        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": GITHUB_REDIRECT_URI,
                },
            )

        token_json = token_res.json()
        access_token = token_json.get("access_token")

        if not access_token:
            raise HTTPException(400, "GitHub token exchange failed")

        async with httpx.AsyncClient() as client:
            user_res = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )

        github_user = user_res.json()

        github_id = github_user.get("id")
        github_login = github_user.get("login")

        if not github_id:
            raise HTTPException(400, "Failed to fetch GitHub user")
        
        result = await db.execute(
            select(GitHubConnection).where(GitHubConnection.user_id == user.id)
        )
        connection = result.scalar_one_or_none()

        if connection:
            connection.github_user_id = github_id
            connection.github_username = github_login
            connection.access_token = encrypt_token(access_token)
            connection.refresh_token = None  # GitHub OAuth usually doesn't return refresh token
            connection.expires_at = None
        else:
            connection = GitHubConnection(
                user_id=user.id,
                github_user_id=github_id,
                github_username=github_login,
                access_token=encrypt_token(access_token),
                refresh_token=None,
                expires_at=None
            )
            db.add(connection)

        await db.commit()
        # Redirect back to frontend with success
        # frontend_url = "http://localhost:5173/connect?status=success"
        # return RedirectResponse(frontend_url)

        return JSONResponse(content={"msg": "GitHub connected successfully"})


    async def is_token_valid(self, github_token: str) -> bool:
        """Check if GitHub access token is still valid"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {github_token}"}
                )
            return response.status_code == 200
        except:
            return False
        

    #maybe removed if we won't store the github token anymore and only use github app install
    async def get_valid_token(self, connection):
        return decrypt_token(connection.access_token)