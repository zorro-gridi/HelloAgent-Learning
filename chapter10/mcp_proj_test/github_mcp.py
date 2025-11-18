
import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import yaml
from pathlib import Path
current_dir = Path(__file__).parent

# 读取配置文件
with open(current_dir.parent.parent.parent / 'config.yaml', 'r') as f:
    config = yaml.safe_load(f)

Provider = 'ModelScope'

LLM_CONFIG = dict(
    base_url=config[Provider]["BASE_URL"],
    api_key=config[Provider]["API_KEY"],
    model=config[Provider]["MODEL_NAME"],
    temperature=0.1,
    )

GIT_TOKEN = config["GIT_TOKEN"]

async def simple_github_search():
    server_params = StdioServerParameters(
        command="npx",
        args=["@modelcontextprotocol/server-github"],
        env={"GITHUB_TOKEN": GIT_TOKEN}
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                _available_tools = await session.list_tools()
                print(_available_tools)

                # 简单的搜索测试
                result = await session.call_tool(
                    "search_repositories",
                    {"query": "AI Agent", "per_page": 3}
                )

                # print("搜索结果:", result)

    except Exception as e:
        print(f"错误: {e}")



if __name__ == "__main__":
    asyncio.run(simple_github_search())