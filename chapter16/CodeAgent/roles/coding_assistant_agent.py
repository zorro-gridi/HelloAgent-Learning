
import os
import sys
from pathlib import Path
current_dir = Path(__file__).parent
proj_dir = current_dir.parent

sys.path.insert(0, proj_dir.as_posix())

from utils import utils


CODING_ASSISTANT_AGENT_PROMPT = '''
你是一个全栈开发助手，擅长各种主流的前、后端编程语言，你能够根据领导的任务指令，完整不同语言的编程任务。

- 编程任务:
{TAASK_DESC}

- 代码上下文:
{CODE_CNOTEXT}

{USER_INSTRUCTION}
'''

# 项目目录树
PROJ_TREE_INFO = utils.ProjectTreeGenerator().generate_tree('./backend', max_depth=1, include_patterns=['*.py'])

TAASK_DESC = f'''
根据 fastapi 后端的接口实现，使用 typedict + vue 技术栈设计一个前端项目结构，保存在 frontend 目录下

- 前端页面的交互方案如下：
1. 页面左侧侧边栏显示当前任务的完整处理流程节点路径图，并显示当前处理节点的名称
2. 右侧根据节点处理的需要，显示不同数量的大块文本输入框，输入框需的设计要有复制图标、提交按钮等交互元素
3. 页面顶部需要有导航栏，分别显示 "代码调试"，“代码优化”，“代码审查”，“代码校对”等任务列表
4. 选中导航栏上不同任务列表，页面左侧边栏显示对应任务的处理流程节点路径图
5. 点击左侧边栏上任务的处理节点，页面应自动滚动定位到该处理节点的起始位置

- 不同任务的流程处理节点
1. "代码调试"任务节点流程：1)提取异常堆栈与源码 -> 2)复制异常堆栈与源码 -> 3)提交LLM分析异常根因
            -> 4）复制保存LLM异常分析结果 -> 5）生成 Bug Sovler Context 上下文
            -> 6）提交LLM生成异常解决方案 -> 7）根据方案修改代码

    节点1）状态下，页面右侧显示空白输入框
    节点2）状态下，输入框内显示节点1）生成的内容
    节点3）为里程碑节点，不可点击，但是需要显示不同颜色，以示区别
    节点4）与节点 1）显示逻辑相同，用于保存复制来自的llm异常结果
    节点5）与节点 1）显示逻辑相同，点击生成按钮后，自动显示生成的上下文
    节点6）节点7）都是里程碑节点，不可点击，但是需要显示不同颜色，以示区别

完成以上需求的前端代码，并给出启动项目的命令

- 项目目录树
{PROJ_TREE_INFO}
'''.lstrip()

# NOTE: 读取输入的代码上下文
with open(proj_dir / 'inputs/include_files_source_code_inputs.md', 'r') as f:
    CODE_CNOTEXT = f.read()

USER_INSTRUCTION = '''
- 核心约束
1. 不能修改原代码的功能，保留原有的实现逻辑
2. 提供完整的 fastapi 接口功能

- 严格按照以下格式返回你的输出
- app 子项目目录树
```plaintext
{{目录树}}
```
- 1. {{接口代码文件完整路径名}}
```python
{{完整 fastapi 接口代码}}
- 2. {{model 代码文件完整路径名}}
... 依此类推
```

请开始执行任务
'''.lstrip()


code_assistant_agent_context = CODING_ASSISTANT_AGENT_PROMPT.format(
    TAASK_DESC=TAASK_DESC,
    USER_INSTRUCTION=USER_INSTRUCTION,
    CODE_CNOTEXT=CODE_CNOTEXT,
    )

with open(proj_dir / 'context/code_assistant_agent_context.md', 'w') as f:
    f.write(code_assistant_agent_context)
    print(code_assistant_agent_context)