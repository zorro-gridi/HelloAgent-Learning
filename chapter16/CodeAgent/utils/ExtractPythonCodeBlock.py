import re

def extract_python_definitions(code_text):
    """
    使用正则表达式提取Python代码中的类和函数定义

    Args:
        code_text (str): Python代码文本

    Returns:
        dict: 包含提取到的类和函数定义的字典
    """

    def clean_code(text):
        """清理代码：移除字符串和注释"""
        # 移除多行字符串
        text = re.sub(r"'''.*?'''", '', text, flags=re.DOTALL)
        text = re.sub(r'""".*?"""', '', text, flags=re.DOTALL)
        # 移除单行字符串
        text = re.sub(r"'.*?'", '', text)
        text = re.sub(r'".*?"', '', text)
        # 移除注释
        text = re.sub(r'#.*$', '', text, flags=re.MULTILINE)
        return text

    def extract_class_definition(match):
        """提取单个类定义的详细信息"""
        class_block = match.group(0)
        class_name = match.group(1)
        inheritance = match.group(2).strip() if match.group(2) else None

        # 提取类中的方法
        methods = []
        method_matches = re.finditer(r'^\s+def\s+(\w+)\s*\((.*?)\)', class_block, re.MULTILINE)
        for method_match in method_matches:
            methods.append({
                'name': method_match.group(1),
                'parameters': method_match.group(2),
                'full_signature': method_match.group(0).strip()
            })

        return {
            'name': class_name,
            'inheritance': inheritance,
            'full_definition': class_block.strip(),
            'methods': methods
        }

    def extract_function_definition(match, is_async=False):
        """提取函数定义的详细信息"""
        func_name = match.group(1)
        parameters = match.group(2)
        return_type = match.group(3).strip() if match.group(3) else None

        return {
            'name': func_name,
            'parameters': parameters,
            'return_type': return_type,
            'full_definition': match.group(0).strip(),
            'is_async': is_async
        }

    # 清理代码
    cleaned_code = clean_code(code_text)

    results = {
        'classes': [],
        'functions': [],
        'async_functions': []
    }

    try:
        # 类定义模式 - 修复后的版本
        class_pattern = re.compile(
            r'^class\s+(\w+)(?:\(([^)]*)\))?\s*:.*?(?=^class|\Z)'
            )
    finally:
        1 / 0


if __name__ == '__main__':
    import requests
    requests.get('/')