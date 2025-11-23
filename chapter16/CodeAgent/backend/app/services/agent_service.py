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