"""
Legislation Agent - 법률 정보 분석 에이전트

한국 법률 정보를 검색하고 분석하는 에이전트.
mcp-kr-legislation MCP 서버 활용.
"""

from app.agents.legislation_agent.single_agent import LegislationSingleAgent
from app.agents.legislation_agent.graph import LegislationGraphAgent, legislation_graph_agent

__all__ = ["LegislationSingleAgent", "LegislationGraphAgent", "legislation_graph_agent"]



