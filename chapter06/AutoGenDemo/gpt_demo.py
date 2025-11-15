from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

import asyncio

import os
from typing import Dict, List

from typing import Sequence
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage

import yaml
from pathlib import Path
current_dir = Path(__file__).parent

# 读取配置文件
with open(current_dir.parent.parent.parent / 'config.yaml', 'r') as f:
    config = yaml.safe_load(f)

Provider = 'ModelScope'
model_client = OpenAIChatCompletionClient(
        model=config[Provider]['MODEL_NAME'],
        api_key=config[Provider]["API_KEY"],
        base_url=config[Provider]["BASE_URL"],
        model_info={
                "function_calling": False,
                "max_tokens": 4096,
                "context_length": 32768,
                "vision": False,
                "json_output": True,
                "family": "qwen",
                "structured_output": False,
            }
    )

# 1. 定义用户代理（User Proxy）
user_proxy = UserProxyAgent(
    name="User",
    description="""作为软件需求提出者，你将提供具体的应用开发需求。
    收到最终代码后，你需要进行测试并反馈结果。""",
)

# 2. 定义产品经理Agent
product_manager = AssistantAgent(
    name="ProductManager",
    system_message="""你是一名资深产品经理，擅长将用户需求转化为详细的产品设计文档。
    工作流程：
    1. 接收用户需求后，进行需求分析和澄清
    2. 编写《应用产品开发总体需求说明书》，包含：
       - 产品目标与定位
       - 核心功能模块
       - 目标用户与使用场景
       - 非功能需求（性能、安全等）
    3. 编写《详细设计说明书》，包含：
       - 功能模块详细说明
       - 界面交互逻辑（如果适用）
       - 数据处理流程
       - 关键功能实现思路
    4. 确保设计文档足够详细，能指导程序员开发""",
    model_client=model_client,
)

# 3. 定义Python程序员Agent
python_developer = AssistantAgent(
    name="PythonDeveloper",
    system_message="""你是一名资深Python开发者，擅长根据产品设计文档实现应用程序。
    工作流程：
    1. 仔细分析产品经理提供的设计文档，有疑问及时提出
    2. 进行模块化开发，逐步实现各项功能
    3. 提交代码时需包含：
       - 完整可运行的代码
       - 必要的注释说明
       - 运行环境与依赖说明
       - 使用方法
    4. 根据评审专家意见修改代码，直至通过评审
    5. 最终提交完整代码包供用户测试""",
    model_client=model_client,
)

# 4. 定义代码评审专家Agent
code_reviewer = AssistantAgent(
    name="CodeReviewer",
    system_message="""你是一名资深代码评审专家，专注于Python代码质量评估。
    评审标准：
    1. 功能完整性：是否完全实现设计文档中的需求
    2. 代码质量：
       - 代码规范性（PEP8标准）
       - 命名合理性
       - 注释完整性
       - 模块化设计
    3. 鲁棒性：
       - 错误处理机制
       - 边界条件处理
       - 输入验证
    4. 性能：
       - 算法效率
       - 资源使用合理性
    5. 安全性：潜在安全风险

    评审输出格式：
    - 总体评价
    - 优点
    - 问题清单（含严重程度和修改建议）
    - 是否通过评审（是/否）""",
    model_client=model_client,
)

# 定义协作流程和对话规则
def custom_selector(messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> str | None:
    """Return next speaker name or None to use LLM selection"""
    if not messages:
        return "ProductManager"

    last_msg = messages[-1]
    if not isinstance(last_msg, BaseChatMessage):
        return None

    sender = last_msg.source
    content = str(last_msg.content) if hasattr(last_msg, 'content') else ""

    if sender == "ProductManager":
        if "总体需求说明书" in content and "详细设计说明书" in content:
            return "PythonDeveloper"
        return "ProductManager"
    elif sender == "PythonDeveloper":
        if "```python" in content or "代码如下" in content:
            return "CodeReviewer"
        return "PythonDeveloper"
    elif sender == "CodeReviewer":
        return "PythonDeveloper"

    return None  # Use LLM to select

termination = MaxMessageTermination(max_messages=50)

# team = RoundRobinGroupChat(
#     participants=[product_manager, python_developer, code_reviewer],
#     termination_condition=termination
# )

team = SelectorGroupChat(
    participants=[product_manager, python_developer, code_reviewer],
    model_client=model_client,
    termination_condition=termination,
    selector_func=custom_selector
)

async def main():
    result = await team.run(task="开发一个显示比特币实时价格与24小时涨跌幅的网页，使用steamlit实现")
    print(result)


# 启动对话
if __name__ == "__main__":
    print("===== 软件开发团队协作系统 =====")
    print("请输入您的应用开发需求，系统将自动启动协作流程...")
    asyncio.run(main())