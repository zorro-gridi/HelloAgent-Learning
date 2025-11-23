
import os
import sys
from pathlib import Path
current_dir = Path(__file__).parent
proj_dir = current_dir.parent

sys.path.insert(0, proj_dir.as_posix())

from prompt.template.bug_solver_agent_prompt import BUG_SOLVER_AGENT_PROMPT


"""
@Desc:
    运行方式
    1. 优先依赖最小异常堆栈信息层次文件 "code_exception_stack_extract_agent_output.txt"。
    获取方式：
    1. 大模型输入：“code_exception_stack_extract_agent_context.md”，
    2. 获取模型返回结果，保存到 "code_exception_stack_extract_agent_output.txt"
    3. 执行本代码
"""

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


user_exception_desc = '''
文件夹是在创建成功后，抛出的 IsADirectoryError: [Errno 21] Is a directory 异常
'''.lstrip()


def generate_agent_context(user_exception_desc) -> None:
    """
    生成 Bug 解决代理的上下文文件，并将结果保存到指定路径。
    该函数会读取异常代码上下文和异常堆栈信息，并格式化为提示模板，最后保存到指定文件。
    """
    # 读取异常代码上下文
    exception_code_context_file = proj_dir / 'outputs/bug_source_code_extract_agent_output.txt'
    exception_code_context = read_code_context(exception_code_context_file)

    # 读取异常堆栈信息
    mini_stack_info_file = proj_dir / 'outputs/code_exception_stack_extract_agent_output.txt'
    if mini_stack_info_file.exists():
        exception_stack_info = read_code_context(mini_stack_info_file)
    else:
        raise Exception('\n❌ 建议将原始堆栈信息经过 llm 过滤分析，减少堆栈的层次\n')
        exception_stack_info = read_code_context(proj_dir / 'inputs/code_exception_stack_info.txt')

    # 格式化上下文
    bug_solve_agent_context = BUG_SOLVER_AGENT_PROMPT.format(
        user_exception_desc=user_exception_desc,
        exception_code_context=exception_code_context,
        exception_stack_info=exception_stack_info
    )

    # 保存上下文
    with open(proj_dir / 'context/bug_solver_agent_context.md', 'w') as f:
        f.write(bug_solve_agent_context)
        print(bug_solve_agent_context)

if __name__ == "__main__":
    generate_agent_context(user_exception_desc)
