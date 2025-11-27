"""
Projects API Routes

프로젝트 관리 API 엔드포인트.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
import uuid
from app.services.project_service import project_service

router = APIRouter(prefix="/api/projects", tags=["Projects"])


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    default_model: Optional[str] = None
    settings: Optional[dict] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_model: Optional[str] = None
    settings: Optional[dict] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    default_model: Optional[str]
    settings: Optional[dict]
    created_at: datetime
    updated_at: datetime


@router.get("")
async def list_projects(
    user_id: Optional[str] = Query(None, description="Filter by user access")
):
    """
    프로젝트 목록 조회.
    user_id가 제공되면 해당 사용자가 접근 가능한 프로젝트만 반환.
    """
    try:
        projects = await project_service.list_projects(user_id=user_id)
        return {"projects": projects, "total": len(projects)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@router.post("")
async def create_project(project: ProjectCreate):
    """
    새 프로젝트 생성.
    """
    try:
        project_id = str(uuid.uuid4())
        result = await project_service.create_project(
            project_id=project_id,
            name=project.name,
            description=project.description,
            default_model=project.default_model,
            settings=project.settings
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/{project_id}")
async def get_project(project_id: str):
    """
    프로젝트 상세 조회.
    """
    try:
        project = await project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project: {str(e)}")


@router.put("/{project_id}")
async def update_project(project_id: str, project: ProjectUpdate):
    """
    프로젝트 수정.
    """
    try:
        result = await project_service.update_project(
            project_id=project_id,
            name=project.name,
            description=project.description,
            default_model=project.default_model,
            settings=project.settings
        )
        if not result:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update project: {str(e)}")


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """
    프로젝트 삭제.
    """
    try:
        success = await project_service.delete_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        return {"status": "deleted", "project_id": project_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")

