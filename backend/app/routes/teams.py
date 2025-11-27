"""
Teams API Routes

팀 관리 API 엔드포인트.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
import uuid
from app.services.project_service import project_service

router = APIRouter(prefix="/api/teams", tags=["Teams"])


class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TeamMemberAdd(BaseModel):
    user_id: str
    role: str = "member"  # owner, admin, member, viewer


class TeamMemberUpdate(BaseModel):
    role: str


class TeamProjectAdd(BaseModel):
    project_id: str


@router.get("")
async def list_teams(
    user_id: Optional[str] = Query(None, description="Filter by user membership")
):
    """
    팀 목록 조회.
    user_id가 제공되면 해당 사용자가 속한 팀만 반환.
    """
    try:
        teams = await project_service.list_teams(user_id=user_id)
        return {"teams": teams, "total": len(teams)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list teams: {str(e)}")


@router.post("")
async def create_team(team: TeamCreate):
    """
    새 팀 생성.
    """
    try:
        team_id = str(uuid.uuid4())
        result = await project_service.create_team(
            team_id=team_id,
            name=team.name,
            description=team.description
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create team: {str(e)}")


@router.get("/{team_id}")
async def get_team(team_id: str):
    """
    팀 상세 조회.
    """
    try:
        team = await project_service.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail=f"Team not found: {team_id}")
        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team: {str(e)}")


@router.put("/{team_id}")
async def update_team(team_id: str, team: TeamUpdate):
    """
    팀 수정.
    """
    try:
        result = await project_service.update_team(
            team_id=team_id,
            name=team.name,
            description=team.description
        )
        if not result:
            raise HTTPException(status_code=404, detail=f"Team not found: {team_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update team: {str(e)}")


@router.delete("/{team_id}")
async def delete_team(team_id: str):
    """
    팀 삭제.
    """
    try:
        success = await project_service.delete_team(team_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Team not found: {team_id}")
        return {"status": "deleted", "team_id": team_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete team: {str(e)}")


# Team Members
@router.get("/{team_id}/members")
async def list_team_members(team_id: str):
    """
    팀 멤버 목록 조회.
    """
    try:
        members = await project_service.list_team_members(team_id)
        return {"members": members, "total": len(members)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list team members: {str(e)}")


@router.post("/{team_id}/members")
async def add_team_member(team_id: str, member: TeamMemberAdd):
    """
    팀에 멤버 추가.
    """
    try:
        result = await project_service.add_team_member(
            team_id=team_id,
            user_id=member.user_id,
            role=member.role
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add team member: {str(e)}")


@router.put("/{team_id}/members/{user_id}")
async def update_team_member_role(team_id: str, user_id: str, member: TeamMemberUpdate):
    """
    팀 멤버 역할 변경.
    """
    try:
        result = await project_service.update_team_member_role(
            team_id=team_id,
            user_id=user_id,
            role=member.role
        )
        if not result:
            raise HTTPException(status_code=404, detail=f"Team member not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update team member role: {str(e)}")


@router.delete("/{team_id}/members/{user_id}")
async def remove_team_member(team_id: str, user_id: str):
    """
    팀에서 멤버 제거.
    """
    try:
        success = await project_service.remove_team_member(team_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Team member not found")
        return {"status": "removed", "team_id": team_id, "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove team member: {str(e)}")


# Team Projects
@router.get("/{team_id}/projects")
async def list_team_projects(team_id: str):
    """
    팀에 할당된 프로젝트 목록 조회.
    """
    try:
        projects = await project_service.list_team_projects(team_id)
        return {"projects": projects, "total": len(projects)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list team projects: {str(e)}")


@router.post("/{team_id}/projects")
async def add_team_project(team_id: str, project: TeamProjectAdd):
    """
    팀에 프로젝트 할당.
    """
    try:
        result = await project_service.add_team_project(
            team_id=team_id,
            project_id=project.project_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add team project: {str(e)}")


@router.delete("/{team_id}/projects/{project_id}")
async def remove_team_project(team_id: str, project_id: str):
    """
    팀에서 프로젝트 제거.
    """
    try:
        success = await project_service.remove_team_project(team_id, project_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Team project not found")
        return {"status": "removed", "team_id": team_id, "project_id": project_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove team project: {str(e)}")

