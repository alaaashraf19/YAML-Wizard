from urllib.parse import urlencode
import os
from dotenv import load_dotenv
from core.security import get_current_user
import httpx
from fastapi import HTTPException
from datetime import datetime, timezone, timedelta
from models.platforms_model import GitLabConnection

load_dotenv()

GITLAB_CLIENT_ID = os.getenv("GITLAB_CLIENT_ID")
GITLAB_REDIRECT_URI = os.getenv("GITLAB_REDIRECT_URI")
GITLAB_CLIENT_SECRET = os.getenv("GITLAB_CLIENT_SECRET")


def gitlab_connect_service(request, db):

    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(401, "Login required")
    
    #this user part will be updates
    user = get_current_user(db, token)

    params = {
        "client_id": GITLAB_CLIENT_ID,
        "redirect_uri": GITLAB_REDIRECT_URI,
        "response_type": "code",
        "scope": "read_user api", #Full API access to GitLab on behalf of the user
    }

    url = "https://gitlab.com/oauth/authorize?" + urlencode(params)
    return {"auth_url": url}





async def gitlab_callback_service(code, request,db):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(401, "Login required")

    user = get_current_user(db, token)


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
        raise HTTPException(status_code=400, detail="GitLab OAuth failed")

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

    gitlab_user = user_resp.json()
    gitlab_user_id = gitlab_user["id"]
    gitlab_username = gitlab_user["username"]

    existing = db.query(GitLabConnection).filter_by(user_id=user.id).first()

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

    db.commit()

    return {"status": "connected"}


async def get_valid_gitlab_token(connection, db):
    if is_token_expired(connection):
        connection = await refresh_gitlab_token(connection, db)

    return connection.access_token#


def is_token_expired(connection):
    if not connection.expires_at:
        return False
    return datetime.now(timezone.utc) >= connection.expires_at


async def refresh_gitlab_token(connection, db):
    url = "https://gitlab.com/oauth/token"

    if not connection.refresh_token:
        raise HTTPException(401, "Missing refresh token")

    data = {
        "client_id": GITLAB_CLIENT_ID,
        "client_secret": GITLAB_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": connection.refresh_token,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, data=data)

    if resp.status_code != 200:
        raise HTTPException(401, "GitLab token refresh failed")

    token_data = resp.json()

    # new tokens
    connection.access_token = token_data["access_token"]
    connection.refresh_token = token_data.get("refresh_token", connection.refresh_token)

    expires_in = token_data.get("expires_in")
    if expires_in:
        connection.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    db.commit()
    db.refresh(connection)

    return connection