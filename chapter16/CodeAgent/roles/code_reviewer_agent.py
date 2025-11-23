import sys
from pathlib import Path
current_dir = Path(__file__).parent

proj_dir = current_dir.parent
sys.path.insert(0, proj_dir.as_posix())

from prompt.template.code_reviewer_agent_prompt import CODE_REVIEWER_AGENT_PROMPT


"""
@Desc:
    运行本代码，需要先去 utils 目录中，使用 “CodeExtraction.py” 文件提取目标代码文件的相关类、方法的源码
    并自动保存到 reviewer_agent_code_context_inputs.txt” 文件中
"""

# 代码审查需求
refinement_needs = '''
1. 重构 _cal_max_selling_amount_with_min_yield 方法，提高执行效率的优化方案；
2. 重构 _cal_fifo_redeem_rate 方法，提高执行效率的优化方案；
3. 重构相关依赖、和被依赖项的执行效率
4. 审查重构后的功能实现是否与原代码保持一致，如有，请继续优化
5. 审查重构后各依赖之间是否产生冲突？如有，需要给出相关依赖的适配方案
'''.lstrip()

# 业务规则
business_rules = '''
1. _cal_max_selling_amount_with_min_yield 方法计算账户指定基金持仓中满足最小净收益率的累计持仓份额；
2. _cal_fifo_redeem_rate 方法计算赎回某只基金持仓的指定份额时，该笔赎回的整体手续费率；
3. 某基金单笔持仓的净收益率 = 记录的持仓收益率 + 当日基金预计涨跌幅 - 该笔赎回的手续费率；
4. 基金赎回按照 FIFO 规则，先买入持仓，赎回时优先匹配；
5. 单笔持仓（etf 除外）的赎回费率与该笔持仓的天数有关。
6. ETF 基金的赎回与持有天数无关，无交易金额相关
7. mode='Backtest' 表示仅进行数据测算，不会更新账户的真实持仓数据；mode='LiveTrade' 会更新持仓数据，两种操作不能合并
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

def generate_agent_context(refinement_needs, business_rules) -> None:
    """
    生成代码审查代理的上下文文件，并将结果保存到指定路径。
    该函数会读取待审查的代码上下文、审查需求和业务规则，并格式化为提示模板，最后保存到指定文件。
    """
    # 读取待审查的代码上下文
    wait_refined_code_context = read_code_context(proj_dir / 'inputs/reviewer_agent_code_context_inputs.txt')

    # 格式化上下文
    code_reviewer_agent_context = CODE_REVIEWER_AGENT_PROMPT.format(
        wait_refined_code_context=wait_refined_code_context,
        refinement_needs=refinement_needs,
        business_rules=business_rules,
    )

    # 保存上下文
    with open(proj_dir / 'context/code_reviewer_agent_context.md', 'w') as f:
        f.write(code_reviewer_agent_context)
        print(code_reviewer_agent_context)

if __name__ == "__main__":
    generate_agent_context()
