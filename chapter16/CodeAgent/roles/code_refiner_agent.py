
from code_reviewer_agent import (
    business_rules,
    refinement_needs,
	)

import sys
from pathlib import Path
current_dir = Path(__file__).parent

proj_dir = current_dir.parent
sys.path.insert(0, proj_dir.as_posix())

from prompt.template.code_refiner_agent_prompt import CODE_REFINE_AGENT_PROMPT


"""
@Desc:
    运行本代码
    1. 需要先去 utils 目录中，使用 “CodeExtraction.py” 文件提取目标代码文件的相关类、方法的源码
       并自动保存到 refiner_agent_code_context_inputs.txt” 文件中
    2. 将 reviewer agent 的输出保存在 “reviewer_agent_output.txt” 文件中
"""

import sys
from pathlib import Path

def read_code_context(file_path: Path) -> str:
    """
    读取指定文件的内容。

    Args:
        file_path (Path): 要读取的文件路径。

    Returns:
        str: 文件内容。
    """
    with open(file_path, 'r') as f:
        return f.read()

def generate_agent_context(refinement_needs, business_rules) -> None:
    """
    生成代码优化代理的上下文文件，并将结果保存到指定路径。
    该函数会读取待优化的代码上下文和架构师的优化指令，并格式化为提示模板，最后保存到指定文件。
    """
    current_dir = Path(__file__).parent
    proj_dir = current_dir.parent
    sys.path.insert(0, proj_dir.as_posix())

    # 读取待优化的代码上下文
    un_refinement_code_context = read_code_context(proj_dir / 'inputs/refiner_agent_code_context_inputs.txt')

    # 读取架构师的优化指令
    arch_refinement_instruction = read_code_context(proj_dir / 'outputs/reviewer_agent_output.txt')

    # 格式化上下文
    code_refiner_agengt_context = CODE_REFINE_AGENT_PROMPT.format(
        un_refinement_code_context=un_refinement_code_context,
        arch_refinement_instruction=arch_refinement_instruction,
        business_rules=business_rules,
        task_description=refinement_needs,
    )

    # 保存上下文
    with open(proj_dir / 'context/code_refiner_agent_context.md', 'w') as f:
        f.write(code_refiner_agengt_context)
        print(code_refiner_agengt_context)

if __name__ == "__main__":
    generate_agent_context()
