from urllib.parse import urlencode
import secrets
import os
from dotenv import load_dotenv
from core.security import get_current_user
import httpx
from fastapi import HTTPException
from datetime import datetime, timezone, timedelta
from models.platforms_model import GitLabConnection, OAuthState
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from .oauth_connector import oauthConnector
from .oauth_utils import encrypt_token, decrypt_token

load_dotenv()
GITLAB_CLIENT_ID = os.getenv("GITLAB_CLIENT_ID")
GITLAB_REDIRECT_URI = os.getenv("GITLAB_REDIRECT_URI")
GITLAB_CLIENT_SECRET = os.getenv("GITLAB_CLIENT_SECRET")
GITLAB_REVOKE_URL = "https://gitlab.com/oauth/revoke"

class GitLabConnector(oauthConnector):

    async def connect(self, request, db):

        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(401, "Login required")
        
        user = await get_current_user(db, token)
        state = secrets.token_urlsafe(16)
        oauth_state = OAuthState(
                user_id=user.id,
                provider="gitlab",
                state=state
            )
        db.add(oauth_state)
        await db.commit()
        params = {
            "client_id": GITLAB_CLIENT_ID,
            "redirect_uri": GITLAB_REDIRECT_URI,
            "response_type": "code",
            "scope": "api", #Full API access to GitLab on behalf of the user
            "state": state
        }

        url = "https://gitlab.com/oauth/authorize?" + urlencode(params)
        return RedirectResponse(url)





    async def callback(self, code,state, request, db):
        
        base_url = os.getenv("Frontend_Base_URL")

        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(f"{base_url}/login?error=login_required")

        user = await get_current_user(db, token)

        #validate state
        result = await db.execute(
            select(OAuthState).where(
                OAuthState.state == state,
                OAuthState.provider == "gitlab",
                OAuthState.user_id == user.id
            )
        )

        oauth_state = result.scalar_one_or_none()

        if not oauth_state:
            return RedirectResponse(f"{base_url}/profile?gitlab=error&reason=invalid_state")


        token_url = "https://gitlab.com/oauth/token"

        data = {
            "client_id": GITLAB_CLIENT_ID,
            "client_secret": GITLAB_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": GITLAB_REDIRECT_URI,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(token_url, data=data)

        if resp.status_code != 200:
            return RedirectResponse(f"{base_url}/profile?gitlab=error&reason=gitlab_oAuth_failed")

        token_data = resp.json()

        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")

        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        
        #fetch user info from GitLab
        async with httpx.AsyncClient() as client:
            user_resp = await client.get(
                "https://gitlab.com/api/v4/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )

        access_token = encrypt_token(access_token)
        if refresh_token:
            refresh_token = encrypt_token(refresh_token)
        gitlab_user = user_resp.json()
        gitlab_user_id = gitlab_user.get("id")
        gitlab_username = gitlab_user.get("username")

        if not gitlab_user_id:
            return RedirectResponse(f"{base_url}/profile?gitlab=error&reason=user_fetch_failed")
        
        result = await db.execute(select(GitLabConnection).where(GitLabConnection.user_id == user.id))
        existing = result.scalar_one_or_none()

        if existing:
                existing.access_token = access_token
                existing.refresh_token = refresh_token
                existing.expires_at = expires_at
                existing.gitlab_user_id = gitlab_user_id
                existing.gitlab_username = gitlab_username
        else:
            new_conn = GitLabConnection(
                    user_id=user.id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    gitlab_user_id=gitlab_user_id,
                    gitlab_username=gitlab_username,
            )
            db.add(new_conn)

        await db.delete(oauth_state)
        await db.commit()

        # Redirect back to frontend with success
        return RedirectResponse(f"{base_url}/profile?gitlab=success")


    async def get_valid_token(self, connection, db):
        valid= await self.is_token_valid(connection)
        if not valid:
            print("calling refresh")
            connection = await self.refresh_gitlab_token(connection, db)

        return decrypt_token(connection.access_token)


    async def is_token_valid(self, connection):
        if not connection.expires_at:
            return True
        expires_at = connection.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        return datetime.now(timezone.utc) < expires_at


    async def refresh_gitlab_token(self, connection, db):
        url = "https://gitlab.com/oauth/token"

        if not connection.refresh_token:
            raise HTTPException(401, "Missing refresh token")

        data = {
            "client_id": GITLAB_CLIENT_ID,
            "client_secret": GITLAB_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": decrypt_token(connection.refresh_token),
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=data)

        if resp.status_code != 200:
            raise HTTPException(401, "GitLab token refresh failed")

        token_data = resp.json()

        # new tokens
        connection.access_token = encrypt_token(token_data["access_token"])
        connection.refresh_token = encrypt_token(token_data.get("refresh_token", connection.refresh_token))

        expires_in = token_data.get("expires_in")
        if expires_in:
            connection.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        await db.commit()
        await db.refresh(connection)

        return connection
    
    async def revoke_gitlab_token(self, access_token: str):

        data = {
            "client_id": GITLAB_CLIENT_ID,
            "client_secret": GITLAB_CLIENT_SECRET,
            "token": access_token,
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(GITLAB_REVOKE_URL, data=data)

        # GitLab returns:
        # 200 or 204 usually success
        # 400 if already invalid
        if resp.status_code in (200, 204):
            print("GitLab token revoked successfully.")
        elif resp.status_code == 400:
            print("GitLab token was already invalid or not found.")
        else:
            raise Exception(f"GitLab revoke failed: {resp.status_code} {resp.text}")
    
    async def disconnect(self, request, db):

        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(401, "Not authenticated")

        user = await get_current_user(db, token)

        result = await db.execute(select(GitLabConnection).where(GitLabConnection.user_id == user.id))
        connection = result.scalar_one_or_none()

        if not connection:
            return {"status": "already_disconnected"}

        #Try revoke on GitLab
        try:
            decrypted_token = decrypt_token(connection.access_token)
            await self.revoke_gitlab_token(decrypted_token)
        except Exception:
            pass

        await db.delete(connection)
        await db.commit()
        return {"status": "disconnected"}