import sys
from pathlib import Path
current_dir = Path(__file__).parent
proj_dir = current_dir.parent

sys.path.insert(0, proj_dir.as_posix())

from backend.app.services.agent_service import AgentService

def get_agent_service() -> AgentService:
    """获取AgentService依赖"""
    return AgentService()