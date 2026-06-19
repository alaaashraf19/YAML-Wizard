from fastapi import APIRouter,Depends, Request
from services.platform_connectors.factory import get_connector
from sqlalchemy.ext.asyncio import AsyncSession
from database.db_engine import get_db


router = APIRouter()



@router.get("/{platform}/connect")
async def connect(platform: str, request: Request, db: AsyncSession = Depends(get_db)):
    connector = get_connector(platform)
    return await connector.connect(request, db)


@router.get("/{platform}/callback")
async def callback(platform: str, code: str, request: Request, db: AsyncSession = Depends(get_db)):
    connector = get_connector(platform)
    return await connector.callback(code, request, db)
    