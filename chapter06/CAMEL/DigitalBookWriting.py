from colorama import Fore
from camel.societies import RolePlaying
from camel.utils import print_text_animated

# 定义协作任务
task_prompt = """
创作一本关于"拖延症心理学"的短篇电子书，目标读者是对心理学感兴趣的普通大众。
要求：
1. 内容科学严谨，基于实证研究
2. 语言通俗易懂，避免过多专业术语
3. 包含实用的改善建议和案例分析
4. 篇幅控制在8000-10000字
5. 结构清晰，包含引言、核心章节和总结
6. 电子书语言使用中文，面向中文读者
"""

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import ChatGPTConfig
from camel.agents import ChatAgent

import yaml
import re
from pathlib import Path
current_dir = Path(__file__).parent

# 读取配置文件
with open(current_dir.parent.parent.parent / 'config.yaml', 'r') as f:
    config = yaml.safe_load(f)

Provider = 'ModelScope'
model = ModelFactory.create(
    model_platform=ModelPlatformType.MODELSCOPE,
    model_type=config[Provider]['MODEL_NAME'],
    url=config[Provider]['BASE_URL'],
    api_key=config[Provider]['API_KEY'],
    model_config_dict=ChatGPTConfig(temperature=0.2, stream=True).as_dict(),
)

print(Fore.YELLOW + f"协作任务:\n{task_prompt}\n")


# 初始化角色扮演会话
role_play_session = RolePlaying(
    assistant_role_name="心理学家",
    user_role_name="作家",
    task_prompt=task_prompt,
    model=model,
)

print(Fore.CYAN + f"具体任务描述:\n{role_play_session.task_prompt}\n")

# 开始协作对话
chat_turn_limit, n = 30, 0
input_msg = role_play_session.init_chat()

while n < chat_turn_limit:
    n += 1
    assistant_response, user_response = role_play_session.step(input_msg)

    print_text_animated(Fore.BLUE + f"作家:\n\n{user_response.msg.content}\n")
    print_text_animated(Fore.GREEN + f"心理学家:\n\n{assistant_response.msg.content}\n")

    pattern = r"(?:<\s*CAMEL_TASK_DONE\s*>|\bCAMEL_TASK_DONE\b)"
    done_user = bool(re.search(pattern, user_response.msg.content))
    done_assistant = bool(re.search(pattern, assistant_response.msg.content))
    if done_user and done_assistant:
        print(Fore.MAGENTA + "✅ 电子书创作完成！")
        break

    input_msg = assistant_response.msg

print(Fore.YELLOW + f"总共进行了 {n} 轮协作对话")
