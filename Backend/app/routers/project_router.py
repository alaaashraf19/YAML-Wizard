from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.db_engine import get_db
from schemas.project_schema import ProjectCreate,ProjectResponse,ProjectUpdate
from schemas.pipeline_schema import PipelineCreate,PipelineResponse,PipelineUpdate,PipelineSummary
from services.chatbot_service import ChatbotService
from services.project_service import create_project,get_project_by_id,get_user_projects,delete_project,update_project
from services.pipeline_services import(
    create_pipeline,get_pipeline_by_id,get_project_pipelines
    ,get_active_pipeline,set_active_pipeline,
    update_pipeline,delete_pipeline)
from schemas.chatbot_schema import ChatSessionResponse
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

@router.get("/{project_id}/sessions",response_model=List[ChatSessionResponse])
async def get_sessions_of_project(
        project_id: int, db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)):
    chatbot_service = ChatbotService()
    sessions = await chatbot_service.get_project_sessions(
        user_id=current_user.id,project_id=project_id,db=db )
    return [
        ChatSessionResponse(
            id=session.id,
            session_name=session.session_name,
            created_at=session.created_at,
            updated_at=session.updated_at,
            project_id=session.project_id,
            project={
                "id": session.project_id,
                "name": session.project.project_name,
                "target_platform": session.project.target_platform,
            } if session.project else None,
        )
        for session in sessions
    ]


@router.put("/{project_id}", response_model=ProjectResponse)
async def updateProject(project_id:int, project_update:ProjectUpdate ,current_user = Depends(get_current_user),db: AsyncSession = Depends(get_db)):
    return await update_project(project_id,current_user.id,project_update,db)

@router.delete("/{project_id}", response_model=ProjectResponse)
async def deleteProject(project_id: int,current_user:User = Depends(get_current_user) ,db: AsyncSession = Depends(get_db)):
    return await delete_project(project_id,current_user.id,db)


################### PIPELINES #################
@router.post("/{project_id}/pipelines", response_model=PipelineResponse)
async def create_project_pipeline(
    project_id: int,
    pipeline: PipelineCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await create_pipeline(pipeline, project_id, current_user.id, db)


@router.get("/{project_id}/pipelines", response_model=List[PipelineSummary])
async def get_project_pipelines_list(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_project_pipelines(project_id, current_user.id, db)


@router.get("/{project_id}/pipelines/active", response_model=PipelineResponse)
async def get_project_active_pipeline(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pipeline = await get_active_pipeline(project_id, current_user.id, db)

    return pipeline


@router.get("/{project_id}/pipelines/{pipeline_id}", response_model=PipelineResponse)
async def get_project_pipeline_by_id(
    project_id: int,
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pipeline = await get_pipeline_by_id(pipeline_id, current_user.id, db)
    project = await get_project_by_id(pipeline.project_id, current_user.id, db)
    p = PipelineResponse.model_validate(pipeline)
    p.is_active = (pipeline.id == project.active_pipeline_id)
    return p



@router.put("/{project_id}/pipelines/{pipeline_id}", response_model=PipelineResponse)
async def update_project_pipeline(
    project_id: int,
    pipeline_id: int,
    pipeline_update: PipelineUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await update_pipeline(pipeline_id,project_id, pipeline_update, current_user.id, db)


@router.delete("/{project_id}/pipelines/{pipeline_id}", response_model=dict)
async def delete_project_pipeline(
    project_id: int,
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pipeline = await get_pipeline_by_id(pipeline_id, current_user.id, db)
    if pipeline.project_id != project_id:
        raise HTTPException(
            status_code=404,
            detail="Pipeline not found in this project"
        )
    await delete_pipeline(pipeline_id, current_user.id, db)
    return {"message": "Pipeline deleted successfully", "pipeline_id": pipeline_id}


@router.post("/{project_id}/pipelines/{pipeline_id}/activate", response_model=PipelineResponse)
async def activate_project_pipeline(
    project_id: int,
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    pipeline = await get_pipeline_by_id(pipeline_id, current_user.id, db)
    if pipeline.project_id != project_id:
        raise HTTPException(
            status_code=404,
            detail="Pipeline not found in this project"
        )
    return await set_active_pipeline(pipeline_id, current_user.id, db)
