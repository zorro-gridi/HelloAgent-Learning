import sys
from pathlib import Path

current_dir = Path(__file__).parent
proj_dir = current_dir.parent
sys.path.insert(0, proj_dir.as_posix())

from prompt.template.code_verify_agent_prompt import CODE_VERIFY_AGENT_PROMPT

# 业务审核条件
business_review_rules = ''.lstrip()
code_before = ''
code_after = ''


def generate_agent_context(business_review_rules, code_before, code_after) -> None:
    """
    生成代码验证代理的上下文文件，并将结果保存到指定路径。
    该函数会读取业务审核规则，并格式化为提示模板，最后保存到指定文件。
    """
    # 格式化上下文
    code_verfiy_agent_context = CODE_VERIFY_AGENT_PROMPT.format(
        business_review_rules=business_review_rules,
        code_before=code_before,
        code_after=code_after,
    )

    # 保存上下文
    with open(proj_dir / 'context/code_verfiy_agent_context.md', 'w') as f:
        f.write(code_verfiy_agent_context)
        print(code_verfiy_agent_context)



if __name__ == "__main__":
    generate_agent_context(business_review_rules, code_before, code_after)
