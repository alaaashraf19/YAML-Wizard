from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.db_engine import get_db
from schemas.project_schema import ProjectCreate,ProjectResponse,ProjectUpdate
from services.project_service import create_project,get_project_by_id,get_user_projects,delete_project,update_project
from core.security import get_current_user
from models.user_model import User
from typing import List

router = APIRouter()

@router.post("", response_model=ProjectResponse)
async def projectCreate(project: ProjectCreate,current_user:User = Depends(get_current_user) ,db: Session = Depends(get_db)):
    return await create_project(project,current_user.id,db)

@router.get("", response_model=List[ProjectResponse])
async def getUserProjects(current_user:User = Depends(get_current_user),db: Session = Depends(get_db)):
    return await get_user_projects(current_user.id,db)

@router.get("/{project_id}", response_model=ProjectResponse)
async def getProject(project_id:int, current_user:User = Depends(get_current_user),db: Session = Depends(get_db)):
    return await get_project_by_id(project_id,current_user.id,db)

@router.delete("/{project_id}", response_model=ProjectResponse)
async def deleteProject(project_id: int,current_user:User = Depends(get_current_user) ,db: Session = Depends(get_db)):
    return await delete_project(project_id,current_user.id,db)

@router.put("/{project_id}", response_model=ProjectResponse)
async def updateProject(project_id:int, project_update:ProjectUpdate ,current_user = Depends(get_current_user),db: Session = Depends(get_db)):
    return await update_project(project_id,current_user.id,project_update,db)