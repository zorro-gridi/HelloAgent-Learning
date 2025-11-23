
import os
import sys
from pathlib import Path
current_dir = Path(__file__).parent

proj_dir = current_dir.parent
sys.path.insert(0, proj_dir.as_posix())

from prompt.template.code_exception_stack_extract_agent_prompt import CODE_EXCEPTION_STACK_EXTRACT_AGENT_PROMPT


"""
@Desc:
    运行代码
    1. 在 utils 目录中执行 “ExceptionTracker.py”, 获取 "code_exception_stack_info.txt" 的堆栈异常信息
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

def generate_agent_context() -> None:
    """
    生成异常堆栈提取代理的上下文文件，并将结果保存到指定路径。
    该函数会读取异常堆栈信息，并格式化为提示模板，最后保存到指定文件。
    """
    # 读取异常堆栈信息
    exception_stack_info = read_code_context(proj_dir / 'inputs/code_exception_stack_info.txt')

    # 格式化上下文
    code_exception_stack_extract_agent_context = CODE_EXCEPTION_STACK_EXTRACT_AGENT_PROMPT.format(
        exception_stack_info=exception_stack_info
    )

    # 保存上下文
    with open(proj_dir / 'context/code_exception_stack_extract_agent_context.md', 'w') as f:
        f.write(code_exception_stack_extract_agent_context)
        print(code_exception_stack_extract_agent_context)

if __name__ == "__main__":
    generate_agent_context()
