
你是一个全栈开发助手，擅长各种主流的前、后端编程语言，你能够根据领导的任务指令，完整不同语言的编程任务。

- 编程任务:
根据 fastapi 后段的接口实现，使用 typedict + vue 技术栈设计一个前端项目结构，保存在 frontend 目录下

- 前端页面的交互方案如下：
1. 页面左侧侧边栏显示当前任务的完整处理流程节点路径图，并显示当前处理节点的名称
2. 右侧根据节点处理的需要，显示不同数量的大块文本输入框，输入框需的设计要有复制图标、提交按钮等交互元素
3. 页面顶部需要有导航栏，分别显示 "代码调试"，“代码优化”，“代码审查”，“代码校对”等任务列表
4. 选中导航栏上不同任务列表，页面左侧边栏显示对应任务的处理流程节点路径图
5. 点击左侧边栏上任务的处理节点，页面应自动滚动定位到该处理节点的起始位置

- 不同任务的流程处理节点
1. "代码调试"任务节点流程：1)提取异常堆栈与源码 -> 2)复制异常堆栈与源码 -> 3)提交LLM分析异常根因
            -> 4）复制保存LLM异常分析结果 -> 5）生成 Bug Sovler Context 上下文
            -> 6）提交LLM生成异常解决方案 -> 7）根据方案修改代码

    节点1）状态下，页面右侧显示空白输入框
    节点2）状态下，输入框内显示节点1）生成的内容
    节点3）为里程碑节点，不可点击，但是需要显示不同颜色，以示区别
    节点4）与节点 1）显示逻辑相同，用于保存复制来自的llm异常结果
    节点5）与节点 1）显示逻辑相同，点击生成按钮后，自动显示生成的上下文
    节点6）节点7）都是里程碑节点，不可点击，但是需要显示不同颜色，以示区别

完成以上需求的前端代码，并给出启动项目的命令

- 项目目录树
backend/
└── app/
    ├── dependencies/
    ├── models/
    ├── routers/
    ├── services/
    ├── __init__.py
    └── main.py


- 代码上下文:
- 以下为文件/Users/zorro/Documents/成长笔记/Agent开发/CodeAgent/backend/app/services/agent_service.py的完整源码
```python
import importlib
import sys
from pathlib import Path
from typing import Dict, Any
import inspect

class AgentService:
    """Agent服务类，负责动态加载和执行不同的agent"""

    def __init__(self):
        self.agents_base_path = Path(__file__).parent.parent.parent.parent / "roles"
        sys.path.insert(0, str(self.agents_base_path.parent))

    async def execute_agent_generation(self, agent_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行指定agent的generate_agent_context方法
        """
        # 构建agent模块路径
        module_name = f"{agent_name}"
        module_path = self.agents_base_path / f"{module_name}.py"

        if not module_path.exists():
            raise ValueError(f"Agent '{agent_name}' not found at {module_path}")

        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 获取generate_agent_context方法
            if not hasattr(module, 'generate_agent_context'):
                raise ValueError(f"Agent '{agent_name}' does not have generate_agent_context method")

            generate_func = module.generate_agent_context

            # 分析函数参数
            sig = inspect.signature(generate_func)
            func_params = list(sig.parameters.keys())

            # 准备调用参数
            call_kwargs = {}
            for param_name in func_params:
                if param_name in parameters:
                    call_kwargs[param_name] = parameters[param_name]
                elif param_name == 'self':
                    continue
                else:
                    # 对于没有提供的必需参数，尝试从模块中获取变量值
                    if hasattr(module, param_name):
                        call_kwargs[param_name] = getattr(module, param_name)
                    else:
                        # 如果参数没有默认值且未提供，则报错
                        param = sig.parameters[param_name]
                        if param.default == param.empty:
                            raise ValueError(f"Required parameter '{param_name}' not provided for agent '{agent_name}'")

            # 执行生成方法
            result = generate_func(**call_kwargs)

            return {
                "output_file": self._get_expected_output_file(agent_name),
                "result": result
            }

        except Exception as e:
            raise ValueError(f"Error executing agent '{agent_name}': {str(e)}")

    def _get_expected_output_file(self, agent_name: str) -> str:
        """获取预期的输出文件路径"""
        output_files = {
            "bug_solver_agent": "context/bug_solver_agent_context.md",
            "bug_source_code_extract_agent": "context/bug_source_code_extract_agent_context.md",
            "code_exception_stack_extract_agent": "context/code_exception_stack_extract_agent_context.md",
            "code_optimizer_agent": "context/optimizer_agent_context_inputs.md",
            "code_refiner_agent": "context/code_refiner_agent_context.md",
            "code_reviewer_agent": "context/code_reviewer_agent_context.md",
            "code_verify_agent": "context/code_verfiy_agent_context.md"
        }
        return output_files.get(agent_name, "context/unknown_agent_context.md")

    def get_available_agents(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用的agent及其参数信息"""
        agents_info = {}

        for py_file in self.agents_base_path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            agent_name = py_file.stem
            try:
                spec = importlib.util.spec_from_file_location(agent_name, py_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, 'generate_agent_context'):
                    sig = inspect.signature(module.generate_agent_context)
                    params = {}

                    for param_name, param in sig.parameters.items():
                        if param_name == 'self':
                            continue
                        params[param_name] = {
                            'type': str(param.annotation) if param.annotation != param.empty else 'Any',
                            'required': param.default == param.empty,
                            'default': param.default if param.default != param.empty else None
                        }

                    agents_info[agent_name] = {
                        'parameters': params,
                        'description': module.__doc__ or "No description available"
                    }

            except Exception:
                continue

        return agents_info
```

- 以下为文件/Users/zorro/Documents/成长笔记/Agent开发/CodeAgent/backend/app/dependencies/agent_dependency.py的完整源码
```python
import sys
from pathlib import Path
current_dir = Path(__file__).parent
proj_dir = current_dir.parent

sys.path.insert(0, proj_dir.as_posix())

from backend.app.services.agent_service import AgentService

def get_agent_service() -> AgentService:
    """获取AgentService依赖"""
    return AgentService()
```

- 以下为文件/Users/zorro/Documents/成长笔记/Agent开发/CodeAgent/backend/app/routers/prompt_router.py的完整源码
```python
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
```

- 以下为文件/Users/zorro/Documents/成长笔记/Agent开发/CodeAgent/backend/app/main.py的完整源码
```python
import sys
from pathlib import Path
current_dir = Path(__file__).parent
proj_dir = current_dir.parent

sys.path.insert(0, proj_dir.as_posix())

from app.routers.prompt_router import router as prompt_router
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="CodeAgent API", version="1.0.0")

# 注册路由
app.include_router(prompt_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "CodeAgent API Server is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
```

- 以下为文件/Users/zorro/Documents/成长笔记/Agent开发/CodeAgent/backend/app/models/agent_models.py的完整源码
```python
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
```



- 核心约束
1. 不能修改原代码的功能，保留原有的实现逻辑
2. 提供完整的 fastapi 接口功能

- 严格按照以下格式返回你的输出
- app 子项目目录树
```plaintext
{{目录树}}
```
- 1. {{接口代码文件完整路径名}}
```python
{{完整 fastapi 接口代码}}
- 2. {{model 代码文件完整路径名}}
... 依此类推
```

请开始执行任务

