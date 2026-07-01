from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.db_engine import get_db
from schemas.project_schema import ProjectCreate,ProjectResponse, ProjectSession,ProjectUpdate
from schemas.pipeline_schema import PipelineCreate,PipelineResponse,PipelineUpdate,PipelineSummary
from services.chatbot_service import ChatbotService
from services.project_service import create_project,get_project_by_id,get_projectModel_by_id,get_user_projects,delete_project,update_project
from services.pipeline_services import(
    create_pipeline,get_pipeline_by_id,get_project_pipelines
    ,get_active_pipelines,set_active_pipeline,
    update_pipeline,delete_pipeline,deactivate_pipeline, mark_pipeline_committed)
from schemas.chatbot_schema import ChatSessionResponse
from core.security import get_current_user
from models.user_model import User
from typing import List, Optional
from services.dashboard import yaml_sync_service
from schemas.yaml_sync_schema import YamlSyncResult, PipelineSyncResult

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


################### PIPELINES #################
# @router.post("/{project_id}/pipelines", response_model=PipelineResponse)
# async def create_project_pipeline(
#     project_id: int,
#     pipeline: PipelineCreate,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     pipeline = await create_pipeline(pipeline, project_id, current_user.id, db)
#     return PipelineResponse.model_validate(pipeline)
#
#
# @router.get("/{project_id}/pipelines", response_model=List[PipelineResponse])
# async def get_project_pipelines_list(
#     project_id: int,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     pipelines =  await get_project_pipelines(project_id, current_user.id, db)
#     return [PipelineResponse.model_validate(p) for p in pipelines]
#
#
# @router.get("/{project_id}/pipelines/active", response_model=List[PipelineResponse])
# async def get_project_active_pipelines(
#     project_id: int,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     pipelines = await get_active_pipelines(project_id, current_user.id, db)
#     return [PipelineResponse.model_validate(p) for p in pipelines]
#
#
# @router.get("/{project_id}/pipelines/{pipeline_id}", response_model=PipelineResponse)
# async def get_project_pipeline_by_id(
#     project_id: int,
#     pipeline_id: int,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     pipeline = await get_pipeline_by_id(pipeline_id, current_user.id, db)
#     return PipelineResponse.model_validate(pipeline)
#
#
#
# @router.put("/{project_id}/pipelines/{pipeline_id}", response_model=PipelineResponse)
# async def update_project_pipeline(
#     project_id: int,
#     pipeline_id: int,
#     pipeline_update: PipelineUpdate,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     pipeline = await update_pipeline(pipeline_id,project_id, pipeline_update, current_user.id, db)
#     return PipelineResponse.model_validate(pipeline)
#
#
# @router.delete("/{project_id}/pipelines/{pipeline_id}", response_model=dict)
# async def delete_project_pipeline(
#     project_id: int,
#     pipeline_id: int,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     return await delete_pipeline(pipeline_id,current_user.id,db)
#
#
# @router.post("/{project_id}/pipelines/{pipeline_id}/activate", response_model=PipelineResponse)
# async def activate_project_pipeline(
#     project_id: int,
#     pipeline_id: int,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     pipeline = await set_active_pipeline(pipeline_id, current_user.id, db)
#     return PipelineResponse.model_validate(pipeline)
#
# @router.post("/{project_id}/pipelines/{pipeline_id}/deactivate", response_model=PipelineResponse)
# async def deactivate_project_pipeline(
#     project_id: int,
#     pipeline_id: int,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     pipeline = await deactivate_pipeline(pipeline_id, current_user.id, db)
#     return PipelineResponse.model_validate(pipeline)
#
# @router.post("{project_id}/pipelines/{pipeline_id}/commit", response_model=PipelineResponse)
# async def commit_project_pipeline(
#     project_id: int,
#     pipeline_id: int,
#     commit_hash: str,
#     commit_author: str,
#     commit_message: Optional[str] = "",
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     pipeline = await mark_pipeline_committed(
#         pipeline_id, current_user.id, commit_hash,
#         commit_author, db, commit_message)
#     return PipelineResponse.model_validate(pipeline)