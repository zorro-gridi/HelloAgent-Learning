# %%
import yaml
import os
import re
import requests
import json
from tavily import TavilyClient
from openai import OpenAI

from pathlib import Path
current_dir = Path(__file__).parent

# 读取配置文件
with open(current_dir.parent.parent.parent / 'config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# %%
AGENT_SYSTEM_PROMPT = """
你是一个智能旅行助手。你的任务是分析用户的请求，并使用可用工具一步步地解决问题。

# 可用工具:
- `get_weather(city: str)`: 查询指定城市的实时天气。
- `get_attraction(city: str, weather: str)`: 根据城市和天气搜索推荐的旅游景点。

# 行动格式:
你的回答必须严格遵循以下格式。首先是你的思考过程，然后是你要执行的具体行动，格式如下：
Thought: [这里是你的思考过程和下一步计划]
Action: [这里是你要调用的工具，格式为 function_name(arg_name="arg_value")]

* 强烈要求：你需要一步一步思考，每次回复仅输出一对 Thought-Action，避免过度思考。
* 输出示例，以下为一对 Thought-Action，输出后，即停止输出
Thought: 已获取北京天气为小雨和雾，气温11℃。需要调用get_attraction根据天气推荐适合的景点。
Action: get_attraction(city="北京", weather="Light rain, mist")

# 任务完成:
当你收集到足够的信息，能够回答用户的最终问题时，你必须在`Action:`字段后使用 `finish(answer="...")` 来输出最终答案。

要求使用中文回答用户问题，请开始吧！
"""

# --- 1. 配置LLM客户端 ---
# 请根据您使用的服务，将这里替换成对应的凭证和地址
os.environ['TAVILY_API_KEY'] = config['TAVILY']['API_KEY']


# %%
def get_weather(city: str) -> str:
    """
    通过调用 wttr.in API 查询真实的天气信息。
    """
    # API端点，我们请求JSON格式的数据
    url = f"https://wttr.in/{city}?format=j1"

    try:
        # 发起网络请求
        response = requests.get(url)
        # 检查响应状态码是否为200 (成功)
        response.raise_for_status()
        # 解析返回的JSON数据
        data = response.json()

        # 提取当前天气状况
        current_condition = data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']

        # 格式化成自然语言返回
        return f"{city}当前天气：{weather_desc}，气温{temp_c}摄氏度"

    except requests.exceptions.RequestException as e:
        # 处理网络错误
        return f"错误：查询天气时遇到网络问题 - {e}"
    except (KeyError, IndexError) as e:
        # 处理数据解析错误
        return f"错误：解析天气数据失败，可能是城市名称无效 - {e}"

print(get_weather('北京'))

# %%
def get_attraction(city: str, weather: str) -> str:
    """
    根据城市和天气，使用Tavily Search API搜索并返回优化后的景点推荐。
    """

    # 从环境变量或主程序配置中获取API密钥
    api_key = os.environ.get("TAVILY_API_KEY") # 推荐方式
    # 或者，我们可以在主循环中传入，如此处代码所示

    if not api_key:
        return "错误：未配置TAVILY_API_KEY。"

    # 2. 初始化Tavily客户端
    tavily = TavilyClient(api_key=api_key)

    # 3. 构造一个精确的查询
    query = f"'{city}' 在'{weather}'天气下最值得去的旅游景点推荐及理由"

    try:
        # 4. 调用API，include_answer=True会返回一个综合性的回答
        response = tavily.search(query=query, search_depth="basic", include_answer=True)

        # 5. Tavily返回的结果已经非常干净，可以直接使用
        # response['answer'] 是一个基于所有搜索结果的总结性回答
        if response.get("answer"):
            return response["answer"]

        # 如果没有综合性回答，则格式化原始结果
        formatted_results = []
        for result in response.get("results", []):
            formatted_results.append(f"- {result['title']}: {result['content']}")

        if not formatted_results:
             return "抱歉，没有找到相关的旅游景点推荐。"

        return "根据搜索，为您找到以下信息：\n" + "\n".join(formatted_results)

    except Exception as e:
        return f"错误：执行Tavily搜索时出现问题 - {e}"

print(get_attraction('北京', '气温10摄氏度'))

# %%
# 将所有工具函数放入一个字典，方便后续调用
available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
}


class OpenAICompatibleClient:
    """
    一个用于调用任何兼容OpenAI接口的LLM服务的客户端。
    """
    def __init__(self, model: str, api_key: str, base_url: str, stream=False):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.stream = stream

    def generate(self, prompt: str, system_prompt: str) -> str:
        """调用LLM API来生成回应。"""
        print("正在调用大语言模型...")
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=self.stream
            )
            # print(response)

            # 用于收集流式输出的完整响应，包含推理过程和答案输出
            full_response = ''
            if self.stream:
                print("=== 模型思考过程 ===")
                # 收集完整推理过程
                reasoning_content = ""
                # 收集完整答案
                answer_content = ""

                for chunk in response:
                    # 收集推理内容（如果有）
                    if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                        reasoning_chunk = chunk.choices[0].delta.reasoning_content or ""
                        print(reasoning_chunk, end='', flush=True)
                        reasoning_content += reasoning_chunk

                    # 收集最终答案内容
                    answer_chunk = chunk.choices[0].delta.content or ""
                    answer_content += answer_chunk

                    # 实时显示答案内容
                    if answer_chunk:
                        if reasoning_content and not hasattr(self, '_reasoning_done'):
                            print('\n\n=== 最终答案 ===\n')
                            self._reasoning_done = True
                        print(answer_chunk, end='', flush=True)

                # 合并推理内容和答案内容
                full_response = reasoning_content + answer_content
                if hasattr(self, '_reasoning_done'):
                    delattr(self, '_reasoning_done')
            else:
                answer_content = response.choices[0].message.content
            print()
            print("大语言模型响应成功。")
            return answer_content
        except Exception as e:
            print(f"调用LLM API时发生错误: {e}")
            return "错误：调用语言模型服务时出错。"

# %%
PROVIDER = 'ModelScope'
stream = True

llm = OpenAICompatibleClient(
    model=config[PROVIDER]['MODEL_NAME'],
    api_key=config[PROVIDER]['API_KEY'],
    base_url=config[PROVIDER]['BASE_URL'],
    stream=stream,
)

# --- 2. 初始化 ---
user_prompt = "你好，请帮我查询一下今天北京的天气，然后根据天气推荐一个合适的旅游景点。"
prompt_history = [f"用户请求: {user_prompt}"]
print(f"用户输入: {user_prompt}\n" + "="*40)

# --- 3. 运行主循环 ---
for i in range(5): # 设置最大循环次数
    print(f"--- 循环 {i+1} ---\n")

    # 3.1. 构建Prompt (NOTE: 每一轮循环增加上一轮推理的结果，作为上下文信息)
    full_prompt = "\n".join(prompt_history)

    # 3.2. 调用LLM进行思考
    llm_output = llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)
    # 模型可能会输出多余的 Thought-Action，需要截断
    '''
    NOTE: 为什么需要这个处理？
        ​1. ​防止模型"超前思考"​​：LLM可能会一次性生成多个思考-行动步骤，但实际执行时应该一步一步来
        ​​2. 确保单步执行​​：Agent框架通常需要先执行当前动作，获得观察结果后，再进行下一步思考
        ​​3. 避免混乱​​：如果一次性输出多个步骤，可能会造成执行逻辑的混乱
    '''
    # 解析 Thought - Action 对
    match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
    if match:
        # NOTE: 只获取第一个 Thought - Action 对，确保模型的思考一步步来
        truncated = match.group(1).strip()
        if truncated != llm_output.strip():
            llm_output = truncated
            print("已截断多余的 Thought-Action 对")

    print(f"模型输出:\n{llm_output}\n")
    prompt_history.append(llm_output)

    # 3.3. 解析并执行行动
    action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
    if not action_match:
        print("解析错误：模型输出中未找到 Action。")
        break

    action_str = action_match.group(1).strip()

    if action_str.startswith("finish"):
        final_answer = re.search(r'finish\(answer="(.*)"\)', action_str).group(1)
        print(f"任务完成，最终答案: {final_answer}")
        break

    tool_name = re.search(r"(\w+)\(", action_str).group(1)
    args_str = re.search(r"\((.*)\)", action_str).group(1)
    kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

    # 调用 tool 工具
    if tool_name in available_tools:
        observation = available_tools[tool_name](**kwargs)
    else:
        observation = f"错误：未定义的工具 '{tool_name}'"

    # 3.4. 记录观察结果
    observation_str = f"Observation: {observation}"
    print(f"{observation_str}\n" + "="*40)
    prompt_history.append(observation_str)
# %%
