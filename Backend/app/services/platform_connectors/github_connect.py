import secrets
from fastapi import HTTPException
from fastapi.responses import RedirectResponse
import httpx
import os
from dotenv import load_dotenv
from core.security import get_current_user
from models.platforms_model import GitHubConnection, OAuthState
from sqlalchemy import select
from services.platform_connectors.oauth_utils import encrypt_token, decrypt_token
from .oauth_connector import oauthConnector
from .oauth_utils import encrypt_token, decrypt_token
import base64

load_dotenv()

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")
GITHUB_REVOKE_URL = "https://api.github.com/applications/{client_id}/token"

class GithubConnector(oauthConnector):

    async def connect(self,request, db):

        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(401, "Login required")

        user = await get_current_user(db, token)

        state = secrets.token_urlsafe(16)
        oauth_state = OAuthState(
                user_id=user.id,
                provider="github",
                state=state
            )
        db.add(oauth_state)
        await db.commit()
        url = (
            "https://github.com/login/oauth/authorize"
            f"?client_id={GITHUB_CLIENT_ID}"
            f"&redirect_uri={GITHUB_REDIRECT_URI}"
            f"&scope=read:user user:email"
            f"&state={state}"
        )

        return RedirectResponse(url)



    async def callback(self, code, state, request, db):
        
        base_url = os.getenv("Frontend_Base_URL")

        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(f"{base_url}/login?error=login_required")

        user = await get_current_user(db, token)

        #validate state
        result = await db.execute(
            select(OAuthState).where(
                OAuthState.state == state,
                OAuthState.provider == "github",
                OAuthState.user_id == user.id
            )
        )

        oauth_state = result.scalar_one_or_none()

        if not oauth_state:
            return RedirectResponse(f"{base_url}/profile?github=error&reason=invalid_state")


        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": GITHUB_REDIRECT_URI,
                    "state": state,
                },
            )

        token_json = token_res.json()
        access_token = token_json.get("access_token")

        if not access_token:
            return RedirectResponse(f"{base_url}/profile?github=error&reason=github_token_exchange_failed")


        async with httpx.AsyncClient() as client:
            user_res = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )

        github_user = user_res.json()

        github_id = github_user.get("id")
        github_login = github_user.get("login")

        if not github_id:
            return RedirectResponse(f"{base_url}/profile?github=error&reason=github_user_fetch_failed")

        
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

        await db.delete(oauth_state)
        await db.commit()

        # Redirect back to frontend with success
        return RedirectResponse(f"{base_url}/profile?github=success")

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
    

    async def revoke_github_token(self, access_token: str):
        """Revokes a GitHub OAuth token so it becomes invalid immediately when user clicks disconnect then we delete from db his data"""

        url = GITHUB_REVOKE_URL.format(client_id=GITHUB_CLIENT_ID)

        auth = base64.b64encode(f"{GITHUB_CLIENT_ID}:{GITHUB_CLIENT_SECRET}".encode()).decode()

        headers = {
            "Authorization": f"Basic {auth}",
            "Accept": "application/vnd.github+json"}

        payload = {"access_token": access_token}

        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.delete(url, json=payload, headers=headers)

        if res.status_code == 204:
            print("GitHub token revoked successfully.")
        elif res.status_code == 404:
            print("GitHub token was already invalid or not found.")
        if res.status_code not in (204, 404):
            raise Exception(f"GitHub revoke failed: {res.status_code} {res.text}")
        
    async def disconnect(self, request, db):
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(401, "Not authenticated")

        user = await get_current_user(db, token)

        result = await db.execute(select(GitHubConnection).where(GitHubConnection.user_id == user.id))
        connection = result.scalar_one_or_none()

        if not connection:
            return {"status": "already_disconnected"}

        try:
            decrypted = decrypt_token(connection.access_token)
            await self.revoke_github_token(decrypted)
        except Exception:
            #if github call fails we just dlete from db and return success, since the token is invalid anyway and we want to remove the connection from our db
            pass

        await db.delete(connection)
        await db.commit()
        return {"status": "disconnected"}