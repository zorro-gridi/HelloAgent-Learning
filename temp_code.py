import re
import json

# 原始字符串
raw_str = '''
```JSON{{
    "selected_tool": "工具名称",
    "reasoning": "选择理由",
    "parameters": {"参数名": "参数值"}
}}```
'''

# 移除外层多余的大括号（处理{{和}}）
cleaned_str = re.sub(r'^\s*{{|}}\s*$', '', raw_str, flags=re.DOTALL)

# 解析为JSON对象
json_obj = json.loads(cleaned_str)

print(json_obj)