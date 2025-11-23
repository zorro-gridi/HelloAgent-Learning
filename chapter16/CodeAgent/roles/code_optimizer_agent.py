import sys
from pathlib import Path
current_dir = Path(__file__).parent

proj_dir = current_dir.parent
sys.path.insert(0, proj_dir.as_posix())

from prompt.template.code_optimizer_agent_prompt import CODE_REFINE_AGENT_PROMPT


"""
@Desc:
    运行本代码
    复制需要优化的源码到 “optimizer_agent_code_context_inputs.txt” 文件中
"""


import sys
from pathlib import Path


# - 本次项目需求类型:
# @可选需求类型：
# 	**功能扩展**
#   **功能优化**
#   **功能新增**
# 	**性能优化**
# 	**提高代码可读性**
# 	**优化代码编写规范**
# 	**优化代码结构**
# 	**......**
needs_type = '功能优化'

# 具体优化需求
refinement_needs = '''
测试中发现 create_from_tree_structure 方法的功能实现不满足需求
1. 无法适配文本整体存在不同缩进的情况
2. 文件错误地被创建成了目录

分析、并修复以上两项功能异常
'''.lstrip()

# 用户约束条件
optimize_constrain = '''
1. 仔细审查并优化
'''.lstrip()


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

def generate_agent_context(needs_type, refinement_needs, optimize_constrain) -> None:
    """
    生成代码优化代理的上下文文件，并将结果保存到指定路径。
    该函数会读取优化需求、约束条件和待优化的代码上下文，并格式化为提示模板，最后保存到指定文件。
    """
    # 读取待优化的代码上下文
    wait_refined_code_context = read_code_context(proj_dir / 'inputs/optimizer_agent_code_context_inputs.txt')

    # 格式化上下文
    code_refiner_agent_context = CODE_REFINE_AGENT_PROMPT.format(
        needs_type=needs_type,
        refinement_needs=refinement_needs,
        optimize_constrain=optimize_constrain,
        wait_refined_code_context=wait_refined_code_context,
    )

    # 保存上下文
    with open(proj_dir / 'context/optimizer_agent_context_inputs.md', 'w') as f:
        f.write(code_refiner_agent_context)
        print(code_refiner_agent_context)


if __name__ == "__main__":
    generate_agent_context(needs_type, refinement_needs, optimize_constrain)
