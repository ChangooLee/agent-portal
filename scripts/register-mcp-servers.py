#!/usr/bin/env python3
"""
MCP 서버 등록 스크립트

3개의 MCP 서버를 stdio 방식으로 MariaDB에 등록합니다.
- mcp-kr-realestate (부동산)
- mcp-kr-health (건강/의료)
- mcp-kr-legislation (법률)

Usage:
    python scripts/register-mcp-servers.py
    
    # Docker 환경에서:
    docker compose exec backend python /app/scripts/register-mcp-servers.py
"""

import asyncio
import aiomysql
import uuid
import json
import os
from datetime import datetime

# MariaDB 연결 설정
DB_HOST = os.getenv("MARIADB_HOST", "mariadb")
DB_PORT = int(os.getenv("MARIADB_PORT", "3306"))
DB_USER = os.getenv("MARIADB_USER", "root")
DB_PASSWORD = os.getenv("MARIADB_ROOT_PASSWORD", "rootpass")
DB_NAME = os.getenv("MARIADB_DATABASE", "agent_portal")

# MCP 서버 설정
MCP_SERVERS = [
    {
        "name": "mcp-kr-realestate",
        "description": "한국 부동산 시세 및 거래 정보 분석 MCP 서버",
        "github_url": "https://github.com/ChangooLee/mcp-kr-realestate",
        "local_path": "/Users/lchangoo/Workspace/mcp-kr-realestate",
        "command": "/Users/lchangoo/Workspace/mcp-kr-realestate/.venv310/bin/mcp-kr-realestate",
        "env_vars": {
            "PUBLIC_DATA_API_KEY": os.getenv("PUBLIC_DATA_API_KEY", ""),
            "PUBLIC_DATA_API_KEY_ENCODED": os.getenv("PUBLIC_DATA_API_KEY_ENCODED", ""),
            "ECOS_API_KEY": os.getenv("ECOS_API_KEY", ""),
            "HOST": "0.0.0.0",
            "PORT": "8001",
            "TRANSPORT": "stdio",
            "LOG_LEVEL": "INFO",
            "MCP_SERVER_NAME": "mcp-kr-realestate"
        }
    },
    {
        "name": "mcp-kr-health",
        "description": "한국 건강보험/의료기관 정보 검색 MCP 서버",
        "github_url": "https://github.com/ChangooLee/mcp-kr-health",
        "local_path": "/Users/lchangoo/Workspace/mcp-kr-health",
        "command": "/Users/lchangoo/Workspace/mcp-kr-health/.venv/bin/python",
        "args": ["-m", "mcp_kr_health.server"],
        "cwd": "/Users/lchangoo/Workspace/mcp-kr-health/src",
        "env_vars": {
            "PUBLIC_DATA_API_KEY": os.getenv("PUBLIC_DATA_API_KEY", ""),
            "PUBLIC_DATA_API_KEY_ENCODED": os.getenv("PUBLIC_DATA_API_KEY_ENCODED", ""),
            "HOST": "0.0.0.0",
            "PORT": "8000",
            "TRANSPORT": "stdio",
            "LOG_LEVEL": "INFO",
            "MCP_SERVER_NAME": "mcp-kr-health"
        }
    },
    {
        "name": "mcp-kr-legislation",
        "description": "한국 법률 정보 검색 MCP 서버",
        "github_url": "https://github.com/ChangooLee/mcp-kr-legislation",
        "local_path": "/Users/lchangoo/Workspace/mcp-kr-legislation",
        "command": "/opt/homebrew/bin/python3",
        "args": ["-m", "mcp_kr_legislation.server"],
        "cwd": "/Users/lchangoo/Workspace/mcp-kr-legislation/src",
        "env_vars": {
            "LEGISLATION_API_KEY": os.getenv("LEGISLATION_API_KEY", "lchangoo"),
            "HOST": "0.0.0.0",
            "PORT": "8002",
            "TRANSPORT": "stdio",
            "LOG_LEVEL": "INFO",
            "MCP_SERVER_NAME": "mcp-kr-legislation"
        }
    }
]


async def get_connection():
    """MariaDB 연결 생성."""
    return await aiomysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset='utf8mb4',
        autocommit=True
    )


async def check_existing(conn, name: str) -> bool:
    """기존 서버 존재 여부 확인."""
    async with conn.cursor() as cursor:
        await cursor.execute(
            "SELECT id FROM mcp_servers WHERE name = %s",
            (name,)
        )
        return await cursor.fetchone() is not None


async def register_server(conn, server: dict) -> str:
    """MCP 서버 등록."""
    server_id = str(uuid.uuid4())
    
    # command 구성 (args가 있으면 포함)
    full_command = server["command"]
    if server.get("args"):
        full_command = f"{server['command']} {' '.join(server['args'])}"
    
    # local_path는 cwd가 있으면 cwd 사용
    local_path = server.get("cwd", server.get("local_path", ""))
    
    # endpoint_url은 어댑터 URL
    adapter_url = f"http://backend:3010/mcp/adapters/{server_id}"
    
    env_vars_json = json.dumps(server["env_vars"])
    
    query = """
    INSERT INTO mcp_servers (
        id, name, description, endpoint_url, transport_type,
        auth_type, enabled,
        github_url, local_path, command, env_vars, process_status
    ) VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, %s, %s, %s, %s)
    """
    
    async with conn.cursor() as cursor:
        await cursor.execute(
            query,
            (
                server_id,
                server["name"],
                server["description"],
                adapter_url,
                "stdio",
                "none",
                server.get("github_url", ""),
                local_path,
                full_command,
                env_vars_json,
                "stopped"
            )
        )
    
    return server_id


async def main():
    """메인 함수."""
    print(f"Connecting to MariaDB at {DB_HOST}:{DB_PORT}...")
    
    try:
        conn = await get_connection()
        print("Connected to MariaDB")
        
        for server in MCP_SERVERS:
            name = server["name"]
            
            if await check_existing(conn, name):
                print(f"⏭️  {name}: 이미 등록됨 (스킵)")
                continue
            
            server_id = await register_server(conn, server)
            print(f"✅ {name}: 등록 완료 (ID: {server_id})")
        
        print("\n🎉 MCP 서버 등록 완료!")
        print("\n등록된 서버 확인:")
        print("  curl http://localhost:3010/api/mcp/servers")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

