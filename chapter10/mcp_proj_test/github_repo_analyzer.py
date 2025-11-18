import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI
import json
from typing import List, Dict, Any

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


class GitHubRepoSearchAgent:
    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_config = llm_config
        self.client = OpenAI(
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"]
        )

    async def get_available_tools(self, session: ClientSession) -> List[Dict]:
        """获取MCP服务提供的工具列表"""
        try:
            tools_response = await session.list_tools()
            return tools_response.tools
        except Exception as e:
            print(f"获取工具列表失败: {e}")
            return []

    def select_appropriate_tool(self, task_description: str, available_tools: List[Dict]) -> Dict:
        """根据任务描述选择合适的工具"""

        tools_info = []
        for tool in available_tools:
            tools_info.append({
                "name": tool.name,
                "description": tool.description or "",
                "inputSchema": tool.inputSchema or {}
            })

        prompt = f"""
        你是一个智能工具选择助手。请根据用户的任务需求，从以下可用工具中选择最合适的工具。

        任务需求: {task_description}

        可用工具列表:
        {json.dumps(tools_info, indent=2, ensure_ascii=False)}

        请分析:
        1. 任务需求与每个工具的匹配度
        2. 工具的功能描述是否满足任务需求
        3. 工具的输入参数是否能够支持任务执行

        请返回JSON格式:
        ```JSON
        {{
            "selected_tool": "工具名称",
            "reasoning": "选择理由",
            "parameters": Optional[{{"参数名": "参数值", ...}}, None]
        }}
        ```
        """

        try:
            response = self.client.chat.completions.create(
                model=self.llm_config["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=self.llm_config["temperature"],
                stream=True,
            )

            # 处理流式响应
            print("✅ 大语言模型响应成功:")
            result = ''
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                if content:
                    print(content, end="", flush=True)
                    result += content

            return result
        except Exception as e:
            print(f"工具选择失败: {e}")
            return {}

    async def search_repositories(self, session: ClientSession, search_query: str, per_page: int = 5) -> Dict:
        """执行仓库搜索"""

        # 获取可用工具
        available_tools = await self.get_available_tools(session)
        if not available_tools:
            return {"error": "无法获取工具列表"}

        print(f"可用工具数量: {len(available_tools)}")
        for tool in available_tools:
            print(f"- {tool.name}: {tool.description}")

        # 选择合适的工具
        task_description = f"搜索GitHub仓库，关键词: {search_query}，返回数量: {per_page}"
        tool_selection = self.select_appropriate_tool(task_description, available_tools)

        import re
        cleaned_marks = re.sub(r'```JSON|```', '', tool_selection, flags=re.IGNORECASE | re.DOTALL)
        # 步骤2：移除外层多余的双大括号及周围空白
        cleaned_braces = re.sub(r'^\s*{{|}}\s*$', '', cleaned_marks, flags=re.DOTALL)
        # 解析为JSON对象
        tool_selection = json.loads(cleaned_braces)

        if not tool_selection or "selected_tool" not in tool_selection:
            return {"error": "无法选择合适的工具"}

        selected_tool_name = tool_selection["selected_tool"]
        print(f"选择的工具: {selected_tool_name}")
        print(f"选择理由: {tool_selection.get('reasoning', '')}")

        # 构造参数
        parameters = tool_selection["parameters"]
        print(f"调用参数: {parameters}")

        try:
            # 调用工具
            result = await session.call_tool(selected_tool_name, parameters)
            return result

        except Exception as e:
            return {"error": f"工具调用失败: {e}"}

class ReportSummaryAgent:
    def __init__(self, llm_config: Dict[str, Any]):
        self.llm_config = llm_config
        self.client = OpenAI(
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"]
        )

    def analyze_trends_and_summarize(self, search_results: Dict, search_query: str) -> str:
        """分析趋势并生成总结报告"""

        # 提取仓库信息
        repositories = []
        try:
            content = search_results.content
            if isinstance(content, list):
                repositories = content
            elif isinstance(content, dict) and "items" in content:
                repositories = content["items"]
        except:
            pass

        print(repositories)

        # 限制为前5个仓库
        top_repos = repositories[:5] if repositories else []
        if len(top_repos) == 0:
            raise Exception(f'❌ 返回 repo 仓库为零')

        # {json.dumps(top_repos, indent=2, ensure_ascii=False)}

        prompt = f"""
        请根据以下GitHub仓库搜索结果，生成一份详细的分析报告。

        搜索关键词: {search_query}
        搜索结果数量: {len(top_repos)}

        仓库信息:
        {top_repos}

        请按照以下结构生成报告:

        # GitHub仓库搜索分析报告

        ## 1. 搜索结果概览
        - 搜索关键词: {search_query}
        - 发现的仓库数量: {len(top_repos)}
        - 总体质量评估

        ## 2. Top {min(5, len(top_repos))} 项目详细介绍
        对每个项目进行详细介绍，包括:
        - 项目名称和描述
        - 主要技术栈
        - 项目特点和优势
        - 活跃度和社区情况

        ## 3. 技术趋势分析
        根据这些项目分析当前的技术发展趋势:
        - 主要技术框架和工具
        - 架构模式
        - 创新点和技术亮点

        ## 4. 未来发展预测
        - 基于当前项目的技术方向预测
        - 潜在的技术挑战
        - 建议关注的重点领域

        请用中文生成报告，确保内容专业、详细且有洞察力。
        """

        try:
            response = self.client.chat.completions.create(
                model=self.llm_config["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=self.llm_config["temperature"],
                stream=True,
            )
            # 处理流式响应
            print("✅ 大语言模型响应成功:")
            result = ''
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                if content:
                    print(content, end="", flush=True)
                    result += content

            return result
        except Exception as e:
            return f"生成报告失败: {e}"

async def main():
    # 配置MCP服务器
    server_params = StdioServerParameters(
        command="npx",
        args=["@modelcontextprotocol/server-github"],
        env={"GIT_TOKEN": GIT_TOKEN}
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 创建两个agent
                search_agent = GitHubRepoSearchAgent(LLM_CONFIG)
                summary_agent = ReportSummaryAgent(LLM_CONFIG)

                # 搜索关键词
                search_query = "AI Agent"
                per_page = 5

                print(f"开始搜索GitHub仓库: {search_query}")
                print("=" * 50)

                # 执行搜索
                search_results = await search_agent.search_repositories(
                    session, search_query, per_page
                )

                if "error" in search_results:
                    print(f"搜索失败: {search_results['error']}")
                    return

                print("\n搜索完成，开始生成分析报告...")
                print("=" * 50)

                # 生成分析报告
                report = summary_agent.analyze_trends_and_summarize(search_results, search_query)

                print("\n" + "=" * 50)
                print("分析报告生成完成:")
                print("=" * 50)
                print(report)

                # 保存报告到文件
                with open("github_analysis_report.md", "w", encoding="utf-8") as f:
                    f.write(report)
                print(f"\n报告已保存到: github_analysis_report.md")

    except Exception as e:
        raise e



if __name__ == "__main__":
    # 运行前请确保设置以下环境变量:
    # export GIT_TOKEN=your_GIT_TOKEN
    # export OPENAI_API_KEY=your_openai_api_key
    # 如果需要自定义OpenAI基础URL:
    # export OPENAI_BASE_URL=your_base_url

    asyncio.run(main())