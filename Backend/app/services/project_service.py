from datetime import datetime
from typing import List

from schemas.project_schema import ProjectCreate, ProjectResponse, ProjectUpdate
from models.project_model import Project
from fastapi import HTTPException
from sqlalchemy.orm import Session


async def get_user_projects(user_id: int, db: Session):
    return db.query(Project).filter(Project.user_id == user_id).all()

async def create_project(project: ProjectCreate,user_id:int, db: Session):
    project_data = project.model_dump()
    project_data['user_id'] = user_id
    new_project = Project(**project_data)
    new_project.created_at = datetime.utcnow()
    new_project.updated_at = datetime.utcnow()
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project

async def update_project(project_id: int, user_id:int, project_update: ProjectUpdate, db: Session):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not Authorized")
    update_data = project_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(project, key, value)
    db.query(Project).filter(Project.id == project_id).update({
        "updated_at": datetime.utcnow()
    })
    db.commit()
    db.refresh(project)
    return project

async def delete_project(project_id: int,user_id: int, db: Session):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not Authorized")
    db.delete(project)
    db.commit()
    return project

async def get_project_by_id(project_id: int,user_id:int, db: Session):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not Authorized")
    return project