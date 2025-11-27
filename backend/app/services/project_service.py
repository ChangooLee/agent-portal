"""
Project Service

프로젝트 및 팀 관리 서비스.
MariaDB 기반.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
import aiomysql

# MariaDB 설정
MARIADB_HOST = os.getenv('MARIADB_HOST', 'mariadb')
MARIADB_PORT = int(os.getenv('MARIADB_PORT', '3306'))
MARIADB_USER = os.getenv('MARIADB_USER', 'root')
MARIADB_PASSWORD = os.getenv('MARIADB_PASSWORD', 'password')
MARIADB_DATABASE = os.getenv('MARIADB_DATABASE', 'agent_portal')


class ProjectService:
    """프로젝트 관리 서비스."""
    
    async def _get_connection(self):
        """MariaDB 연결 획득."""
        return await aiomysql.connect(
            host=MARIADB_HOST,
            port=MARIADB_PORT,
            user=MARIADB_USER,
            password=MARIADB_PASSWORD,
            db=MARIADB_DATABASE,
            autocommit=True
        )
    
    async def list_projects(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        프로젝트 목록 조회.
        user_id가 제공되면 해당 사용자가 접근 가능한 프로젝트만 반환.
        """
        try:
            conn = await self._get_connection()
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                if user_id:
                    # 사용자가 속한 팀의 프로젝트만 조회
                    await cursor.execute("""
                        SELECT DISTINCT p.* 
                        FROM projects p
                        LEFT JOIN team_projects tp ON p.id = tp.project_id
                        LEFT JOIN team_members tm ON tp.team_id = tm.team_id
                        WHERE tm.user_id = %s OR p.id = '8c59e361-3727-418c-bc68-086b69f7598b'
                        ORDER BY p.created_at DESC
                    """, (user_id,))
                else:
                    # 모든 프로젝트 조회
                    await cursor.execute("""
                        SELECT * FROM projects ORDER BY created_at DESC
                    """)
                
                rows = await cursor.fetchall()
                projects = []
                for row in rows:
                    project = dict(row)
                    if project.get('settings') and isinstance(project['settings'], str):
                        project['settings'] = json.loads(project['settings'])
                    if project.get('created_at'):
                        project['created_at'] = project['created_at'].isoformat()
                    if project.get('updated_at'):
                        project['updated_at'] = project['updated_at'].isoformat()
                    projects.append(project)
                
                conn.close()
                return projects
        except Exception as e:
            # 테이블이 없는 경우 기본 프로젝트 반환
            return [{
                'id': '8c59e361-3727-418c-bc68-086b69f7598b',
                'name': 'Default Project',
                'description': 'Default project for LLM monitoring',
                'default_model': None,
                'settings': None,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }]
    
    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """프로젝트 상세 조회."""
        try:
            conn = await self._get_connection()
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    "SELECT * FROM projects WHERE id = %s",
                    (project_id,)
                )
                row = await cursor.fetchone()
                conn.close()
                
                if row:
                    project = dict(row)
                    if project.get('settings') and isinstance(project['settings'], str):
                        project['settings'] = json.loads(project['settings'])
                    if project.get('created_at'):
                        project['created_at'] = project['created_at'].isoformat()
                    if project.get('updated_at'):
                        project['updated_at'] = project['updated_at'].isoformat()
                    return project
                return None
        except Exception as e:
            # 테이블이 없는 경우 기본 프로젝트 반환
            if project_id == '8c59e361-3727-418c-bc68-086b69f7598b':
                return {
                    'id': '8c59e361-3727-418c-bc68-086b69f7598b',
                    'name': 'Default Project',
                    'description': 'Default project for LLM monitoring',
                    'default_model': None,
                    'settings': None,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
            return None
    
    async def create_project(
        self,
        project_id: str,
        name: str,
        description: Optional[str] = None,
        default_model: Optional[str] = None,
        settings: Optional[dict] = None
    ) -> Dict[str, Any]:
        """새 프로젝트 생성."""
        conn = await self._get_connection()
        async with conn.cursor() as cursor:
            settings_json = json.dumps(settings) if settings else None
            await cursor.execute("""
                INSERT INTO projects (id, name, description, default_model, settings)
                VALUES (%s, %s, %s, %s, %s)
            """, (project_id, name, description, default_model, settings_json))
            
        conn.close()
        return await self.get_project(project_id)
    
    async def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        default_model: Optional[str] = None,
        settings: Optional[dict] = None
    ) -> Optional[Dict[str, Any]]:
        """프로젝트 수정."""
        # 기존 프로젝트 확인
        existing = await self.get_project(project_id)
        if not existing:
            return None
        
        conn = await self._get_connection()
        async with conn.cursor() as cursor:
            updates = []
            values = []
            
            if name is not None:
                updates.append("name = %s")
                values.append(name)
            if description is not None:
                updates.append("description = %s")
                values.append(description)
            if default_model is not None:
                updates.append("default_model = %s")
                values.append(default_model)
            if settings is not None:
                updates.append("settings = %s")
                values.append(json.dumps(settings))
            
            if updates:
                values.append(project_id)
                await cursor.execute(
                    f"UPDATE projects SET {', '.join(updates)} WHERE id = %s",
                    tuple(values)
                )
        
        conn.close()
        return await self.get_project(project_id)
    
    async def delete_project(self, project_id: str) -> bool:
        """프로젝트 삭제."""
        existing = await self.get_project(project_id)
        if not existing:
            return False
        
        conn = await self._get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM projects WHERE id = %s",
                (project_id,)
            )
        conn.close()
        return True


    # Team methods
    async def list_teams(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """팀 목록 조회."""
        try:
            conn = await self._get_connection()
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                if user_id:
                    await cursor.execute("""
                        SELECT DISTINCT t.* 
                        FROM teams t
                        LEFT JOIN team_members tm ON t.id = tm.team_id
                        WHERE tm.user_id = %s
                        ORDER BY t.created_at DESC
                    """, (user_id,))
                else:
                    await cursor.execute("SELECT * FROM teams ORDER BY created_at DESC")
                
                rows = await cursor.fetchall()
                teams = []
                for row in rows:
                    team = dict(row)
                    if team.get('created_at'):
                        team['created_at'] = team['created_at'].isoformat()
                    if team.get('updated_at'):
                        team['updated_at'] = team['updated_at'].isoformat()
                    teams.append(team)
                
                conn.close()
                return teams
        except Exception:
            return []
    
    async def get_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        """팀 상세 조회."""
        try:
            conn = await self._get_connection()
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("SELECT * FROM teams WHERE id = %s", (team_id,))
                row = await cursor.fetchone()
                conn.close()
                
                if row:
                    team = dict(row)
                    if team.get('created_at'):
                        team['created_at'] = team['created_at'].isoformat()
                    if team.get('updated_at'):
                        team['updated_at'] = team['updated_at'].isoformat()
                    return team
                return None
        except Exception:
            return None
    
    async def create_team(
        self,
        team_id: str,
        name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """새 팀 생성."""
        conn = await self._get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO teams (id, name, description)
                VALUES (%s, %s, %s)
            """, (team_id, name, description))
        conn.close()
        return await self.get_team(team_id)
    
    async def update_team(
        self,
        team_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """팀 수정."""
        existing = await self.get_team(team_id)
        if not existing:
            return None
        
        conn = await self._get_connection()
        async with conn.cursor() as cursor:
            updates = []
            values = []
            
            if name is not None:
                updates.append("name = %s")
                values.append(name)
            if description is not None:
                updates.append("description = %s")
                values.append(description)
            
            if updates:
                values.append(team_id)
                await cursor.execute(
                    f"UPDATE teams SET {', '.join(updates)} WHERE id = %s",
                    tuple(values)
                )
        conn.close()
        return await self.get_team(team_id)
    
    async def delete_team(self, team_id: str) -> bool:
        """팀 삭제."""
        existing = await self.get_team(team_id)
        if not existing:
            return False
        
        conn = await self._get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM teams WHERE id = %s", (team_id,))
        conn.close()
        return True
    
    # Team Members
    async def list_team_members(self, team_id: str) -> List[Dict[str, Any]]:
        """팀 멤버 목록 조회."""
        try:
            conn = await self._get_connection()
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("""
                    SELECT * FROM team_members WHERE team_id = %s
                """, (team_id,))
                rows = await cursor.fetchall()
                conn.close()
                
                members = []
                for row in rows:
                    member = dict(row)
                    if member.get('created_at'):
                        member['created_at'] = member['created_at'].isoformat()
                    if member.get('updated_at'):
                        member['updated_at'] = member['updated_at'].isoformat()
                    members.append(member)
                return members
        except Exception:
            return []
    
    async def add_team_member(
        self,
        team_id: str,
        user_id: str,
        role: str = "member"
    ) -> Dict[str, Any]:
        """팀에 멤버 추가."""
        conn = await self._get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO team_members (team_id, user_id, role)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE role = VALUES(role)
            """, (team_id, user_id, role))
        conn.close()
        return {"team_id": team_id, "user_id": user_id, "role": role}
    
    async def update_team_member_role(
        self,
        team_id: str,
        user_id: str,
        role: str
    ) -> Optional[Dict[str, Any]]:
        """팀 멤버 역할 변경."""
        conn = await self._get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("""
                UPDATE team_members SET role = %s WHERE team_id = %s AND user_id = %s
            """, (role, team_id, user_id))
            if cursor.rowcount == 0:
                conn.close()
                return None
        conn.close()
        return {"team_id": team_id, "user_id": user_id, "role": role}
    
    async def remove_team_member(self, team_id: str, user_id: str) -> bool:
        """팀에서 멤버 제거."""
        conn = await self._get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("""
                DELETE FROM team_members WHERE team_id = %s AND user_id = %s
            """, (team_id, user_id))
            success = cursor.rowcount > 0
        conn.close()
        return success
    
    # Team Projects
    async def list_team_projects(self, team_id: str) -> List[Dict[str, Any]]:
        """팀에 할당된 프로젝트 목록 조회."""
        try:
            conn = await self._get_connection()
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("""
                    SELECT p.* FROM projects p
                    JOIN team_projects tp ON p.id = tp.project_id
                    WHERE tp.team_id = %s
                    ORDER BY p.created_at DESC
                """, (team_id,))
                rows = await cursor.fetchall()
                conn.close()
                
                projects = []
                for row in rows:
                    project = dict(row)
                    if project.get('settings') and isinstance(project['settings'], str):
                        project['settings'] = json.loads(project['settings'])
                    if project.get('created_at'):
                        project['created_at'] = project['created_at'].isoformat()
                    if project.get('updated_at'):
                        project['updated_at'] = project['updated_at'].isoformat()
                    projects.append(project)
                return projects
        except Exception:
            return []
    
    async def add_team_project(self, team_id: str, project_id: str) -> Dict[str, Any]:
        """팀에 프로젝트 할당."""
        conn = await self._get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO team_projects (team_id, project_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE team_id = VALUES(team_id)
            """, (team_id, project_id))
        conn.close()
        return {"team_id": team_id, "project_id": project_id}
    
    async def remove_team_project(self, team_id: str, project_id: str) -> bool:
        """팀에서 프로젝트 제거."""
        conn = await self._get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("""
                DELETE FROM team_projects WHERE team_id = %s AND project_id = %s
            """, (team_id, project_id))
            success = cursor.rowcount > 0
        conn.close()
        return success


# Singleton
project_service = ProjectService()

