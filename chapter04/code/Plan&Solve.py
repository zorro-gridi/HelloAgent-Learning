from llm import HelloAgentsLLM
from tool import ToolExecutor

import sys
import re
import subprocess
import ast


PLANNER_PROMPT_TEMPLATE = """
你是一个顶级的AI规划专家。你的任务是将用户提出的复杂问题分解成一个由多个简单步骤组成的行动计划。
请确保计划中的每个步骤都是一个独立的、可执行的子任务，并且严格按照逻辑顺序排列。
你的输出必须是一个Python列表，其中每个元素都是一个描述子任务的字符串。

问题: {question}

请严格按照以下格式输出你的计划, ```python、与```作为前后缀是必要的:
```python
["步骤1", "步骤2", "步骤3", ...]
```
"""

class Planner:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def plan(self, question: str) -> list[str]:
        """
        根据用户问题生成一个行动计划。
        """
        prompt = PLANNER_PROMPT_TEMPLATE.format(question=question)

        # 为了生成计划，我们构建一个简单的消息列表
        messages = [{"role": "user", "content": prompt}]

        print("--- 正在生成计划 ---")
        # 使用流式输出来获取完整的计划
        response_text = self.llm_client.think(messages=messages) or ""
        print(f"✅ 计划已生成:\n{response_text}")

        # 解析LLM输出的列表字符串
        try:
            # 找到```python和```之间的内容
            plan_str = response_text.split("```python")[1].split("```")[0].strip()
            # 使用ast.literal_eval来安全地执行字符串，将其转换为Python列表
            plan = ast.literal_eval(plan_str)
            return plan if isinstance(plan, list) else []

        except (ValueError, SyntaxError, IndexError) as e:
            print(f"❌ 解析计划时出错: {e}")
            print(f"原始响应: {response_text}")
            raise e

        except Exception as e:
            print(f"❌ 解析计划时发生未知错误: {e}")
            raise e

# TODO: 后面章节应该有学习案例
# 为加快任务执行，你还有以下工具用于辅助计算
# {tools}

EXECUTOR_PROMPT_TEMPLATE = """
你是一位顶级的AI执行专家。你的任务是严格按照给定的计划，一步步地解决问题。
你将收到原始问题、完整的计划、以及到目前为止已经完成的步骤和结果。
请你专注于解决“当前步骤”，并仅输出该步骤的最终答案，不要输出任何额外的解释或对话。

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}

你应该**优先尝试编写 Python 函数**，并通过函数调用解决问题，特别是对于数理、计数等逻辑问题。
- 函数设计**必须包含完整的函数签名、文档字符串，并遵循PEP 8编码规范**。
- 当你使用 Python 函数调用解决问题时，你的输出是一段 Python 代码，要求 print 函数调用结果。输出格式如下：
```python
你的代码
```

- 当你能够直接回答问题时，请直接范围答案文本

请仅输出针对“当前步骤”的回答:
"""

import calendar
from datetime import date, timedelta
from typing import List


class Calendar:
    def get_month_days(self, year: int, month: int):
        '''
        Desc:
            获取某年某月一共有多少天
        Args:
            year: int, 年份
            month: int, 月份
        Returns:
            int: 该月的天数
        '''
        # 使用calendar模块的monthrange函数获取该月的天数
        # monthrange返回一个元组 (该月第一天的星期, 该月的天数)
        days = calendar.monthrange(year, month)[1]
        return f'{days}天'


    def get_month_weekdays(self, year: int, month: int, weekdays: List[str]):
        '''
        Desc:
            获取某年某月中有多少个weekdays
        Args:
            year: 年份
            month: 月份
            weekdays: 可选参数 ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        Returns:
            int: 指定星期几在该月中出现的次数
        '''
        weekday_map = {
            "周一": 0, "周二": 1, "周三": 2, "周四": 3,
            "周五": 4, "周六": 5, "周日": 6
        }

        target_weekdays = [weekday_map[wd] for wd in weekdays]

        # 获取该月的天数
        month_days = self.get_month_days(year, month)

        count = 0
        # 只需要遍历天数，计算每个日期对应的星期几
        for day in range(1, month_days + 1):
            current_date = date(year, month, day)
            if current_date.weekday() in target_weekdays:
                count += 1

        return f'{count}次'


class Executor:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def execute(self, question: str, plan: list[str]) -> str:
        """
        根据计划，逐步执行并解决问题。
        """
        history = "" # 用于存储历史步骤和结果的字符串

        print("\n--- 正在执行计划 ---")

        for i, step in enumerate(plan):
            print(f"\n-> 正在执行步骤 {i+1}/{len(plan)}: {step}")

            prompt = EXECUTOR_PROMPT_TEMPLATE.format(
                question=question,
                plan=plan,
                history=history if history else "无", # 如果是第一步，则历史为空
                current_step=step
            )

            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages) or ""

            if '```python' in response_text:
                print(f'🧮 该问题优先使用编程解决')
                # 匹配 ```python 开头，``` 结尾的代码块
                pattern = r'```python(.*?)```'
                matches = re.findall(pattern, response_text, re.DOTALL)

                # 清理每段代码（去除前后空白）
                code_blocks = [match.strip() for match in matches]
                # 将代码保存到临时文件执行
                with open('temp_code.py', 'w', encoding='utf-8') as f:
                    f.write(code_blocks[0])

                # 执行并捕获输出
                result = subprocess.run([sys.executable, 'temp_code.py'],
                                    capture_output=True, text=True, timeout=30)
                response_text = result.stdout.strip()

            # 更新历史记录，为下一步做准备
            history += f"步骤 {i+1}: {step}\n结果: {response_text}\n\n"
            print(f"✅ 步骤 {i+1} 已完成，结果: {response_text}")

        # 循环结束后，最后一步的响应就是最终答案
        final_answer = response_text
        return final_answer


class PlanAndSolveAgent:
    def __init__(self, llm_client: HelloAgentsLLM):
        """
        初始化智能体，同时创建规划器和执行器实例。
        """
        self.llm_client = llm_client
        self.planner = Planner(self.llm_client)
        self.executor = Executor(self.llm_client)

    def run(self, question: str):
        """
        运行智能体的完整流程:先规划，后执行。
        """
        print(f"\n--- 开始处理问题 ---\n问题: {question}")

        # 1. 调用规划器生成计划
        plan = self.planner.plan(question)

        # 检查计划是否成功生成
        if not plan:
            print("\n--- 任务终止 --- \n无法生成有效的行动计划。")
            return

        # 2. 调用执行器执行计划
        final_answer = self.executor.execute(question, plan)
        print(f"\n--- 任务完成 ---\n最终答案: {final_answer}")



if __name__ == '__main__':
    llm_client = HelloAgentsLLM(Provider='ModelScope')
    tool_executor = ToolExecutor()

    tool_executor.registerTool('计算月份的天数', '返回指定*年*月一共有多少个自然日', Calendar().get_month_days)
    tool_executor.registerTool('计算月份中指定星期的天数', '返回指定*年*月中指定的星期有多少个自然日', Calendar().get_month_weekdays)

    plan_solve_agent = PlanAndSolveAgent(llm_client)
    plan_solve_agent.run('Zorro每周一、三、五游泳，游泳馆的票价为40元/次，请问在2025年11月份，Zorro游泳一共需要花多少钱？')