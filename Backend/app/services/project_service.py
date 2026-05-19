from datetime import datetime
from typing import List

from schemas.project_schema import ProjectCreate, ProjectResponse, ProjectUpdate
from models.project_model import Project
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select,update,delete
from sqlalchemy.ext.asyncio import AsyncSession


async def get_user_projects(user_id: int, db: AsyncSession):
    result = await db.execute(select(Project).where(Project.user_id == user_id))
    return result.scalars().all()

async def create_project(project: ProjectCreate,user_id:int, db: AsyncSession):
    project_data = project.model_dump()
    project_data['user_id'] = user_id
    new_project = Project(**project_data)
    new_project.created_at = datetime.utcnow()
    new_project.updated_at = datetime.utcnow()
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    return new_project

async def update_project(project_id: int, user_id:int, project_update: ProjectUpdate, db: AsyncSession):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalars().one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    project.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(project)
    return project

async def delete_project(project_id: int,user_id: int, db: AsyncSession):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalars().one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()
    return project

async def get_project_by_id(project_id: int,user_id:int, db: AsyncSession):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalars().one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project