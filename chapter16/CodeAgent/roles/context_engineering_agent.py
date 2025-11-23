
import sys
from pathlib import Path
current_dir = Path(__file__).parent

proj_dir = current_dir.parent
print(proj_dir)
sys.path.insert(0, proj_dir.as_posix())

from prompt.template.context_engineering_agent_prompt import CONTEXT_ENGINERRING_AGENT_PROMPT


# - 已知的程序源码:
source_code = '''

'''

# - 开发任务
task_description = '''

'''
