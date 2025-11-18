"""
10.3.4 在智能体中使用A2A工具
（1）使用A2ATool包装器
"""

from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import A2ATool
from dotenv import load_dotenv

load_dotenv()

import yaml
from pathlib import Path
current_dir = Path(__file__).parent

# 读取配置文件
with open(current_dir.parent.parent / 'config.yaml', 'r') as f:
    config = yaml.safe_load(f)

Provider = 'ModelScope'
llm_config = dict(
    base_url=config[Provider]["BASE_URL"],
    api_key=config[Provider]["API_KEY"],
    model=config[Provider]["MODEL_NAME"],
    )

llm = HelloAgentsLLM(**llm_config)

# 假设已经有一个研究员Agent服务运行在 http://127.0.0.1:5000

# 创建协调者Agent
coordinator = SimpleAgent(name="协调者", llm=llm)

# 添加A2A工具，连接到研究员Agent
researcher_tool = A2ATool(agent_url="http://127.0.0.1:5000")
coordinator.add_tool(researcher_tool)

# 协调者可以调用研究员Agent
# 使用 action="ask" 向 Agent 提问
response = coordinator.run("使用a2a工具，向Agent提问：请研究AI在教育领域的应用")
print(response)
