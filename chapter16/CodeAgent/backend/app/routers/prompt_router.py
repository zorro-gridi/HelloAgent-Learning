import sys
from pathlib import Path
current_dir = Path(__file__).parent
proj_dir = current_dir.parent

sys.path.insert(0, proj_dir.as_posix())

from fastapi import APIRouter, HTTPException, Depends
from models.agent_models import AgentGenerateRequest, AgentGenerateResponse
from services.agent_service import AgentService

router = APIRouter(prefix="/prompt", tags=["prompt"])

@router.post("/generate", response_model=AgentGenerateResponse)
async def generate_agent_context(
    request: AgentGenerateRequest,
    agent_service: AgentService = Depends()
):
    """
    根据Agent名称生成对应的上下文
    """
    try:
        result = await agent_service.execute_agent_generation(
            request.agent_name,
            request.parameters
        )
        return AgentGenerateResponse(
            success=True,
            message="Agent context generated successfully",
            agent_name=request.agent_name,
            output_file=result.get("output_file")
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")