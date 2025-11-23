# Created by auto-generator
from typing import Dict, Any, Optional
from pydantic import BaseModel

class AgentGenerateRequest(BaseModel):
    """Agent生成请求模型"""
    agent_name: str
    parameters: Dict[str, Any] = {}

class AgentGenerateResponse(BaseModel):
    """Agent生成响应模型"""
    success: bool
    message: str
    agent_name: Optional[str] = None
    output_file: Optional[str] = None
    error: Optional[str] = None