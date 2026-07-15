from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.db_engine import get_db
from schemas.project_schema import ProjectCreate,ProjectResponse, ProjectSession,ProjectUpdate
from services.chatbot_service import ChatbotService
from services.project_service import create_project,get_project_by_id,get_user_projects,delete_project,update_project
from core.security import get_current_user
from models.user_model import User
from typing import List


router = APIRouter()

@router.post("", response_model=ProjectResponse)
async def projectCreate(project: ProjectCreate,current_user:User = Depends(get_current_user) ,db: AsyncSession = Depends(get_db)):
    return await create_project(project,current_user.id,db)

@router.get("", response_model=List[ProjectResponse])
async def getUserProjects(current_user:User = Depends(get_current_user),db: AsyncSession = Depends(get_db)):
    return await get_user_projects(current_user.id,db)

@router.get("/{project_id}", response_model=ProjectResponse)
async def getProject(project_id:int, current_user:User = Depends(get_current_user),db: AsyncSession = Depends(get_db)):
    return await get_project_by_id(project_id,current_user.id,db)

@router.get("/{project_id}/sessions",response_model=List[ProjectSession])
async def get_sessions_of_project(
        project_id: int, db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)):
    chatbot_service = ChatbotService()
    sessions = await chatbot_service.get_project_sessions(
        user_id=current_user.id,project_id=project_id,db=db )
    return [
        ProjectSession(
            id=session.id,
            session_name=session.session_name,
            updated_at=session.updated_at
        )
        for session in sessions
    ]


@router.put("/{project_id}", response_model=ProjectResponse)
async def updateProject(project_id:int, project_update:ProjectUpdate ,current_user = Depends(get_current_user),db: AsyncSession = Depends(get_db)):
    return await update_project(project_id,current_user.id,project_update,db)

@router.delete("/{project_id}")
async def deleteProject(project_id: int,current_user:User = Depends(get_current_user) ,db: AsyncSession = Depends(get_db)):
    return await delete_project(project_id,current_user.id,db)