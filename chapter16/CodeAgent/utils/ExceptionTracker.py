import inspect
import traceback
import os
import sys
import ast
import site
from typing import List, Dict, Optional, Callable
from copy import copy

import os
import sys
from pathlib import Path
current_dir = Path(__file__).parent
proj_dir = current_dir.parent



class ExceptionStackFormatter:
    """异常堆栈信息格式化器"""

    def __init__(self, return_third_pkg: bool = False, return_stack_layer: int = 20, return_docstring: bool = True) -> None:
        """
        Desc:
            Python 程序异常堆栈的格式化输出器
        Args:
            return_third_pkg: 是否返回第三方库的源码
            return_stack_layer: 追溯异常堆栈的最大深度
        """
        self.return_third_pkg = return_third_pkg
        self.return_stack_layer = return_stack_layer
        self.return_docstring = return_docstring

    @staticmethod
    def strip_comment(line: str) -> str:
        """去除行内注释，保留字符串内的#，只处理行尾注释"""
        in_single_quote = False
        in_double_quote = False
        escape = False
        comment_pos = None

        for idx, char in enumerate(line):
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            # 处理字符串引号
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            # 处理注释（不在字符串内时）
            elif char == "#" and not in_single_quote and not in_double_quote:
                comment_pos = idx
                break

        return line[:comment_pos].rstrip() if comment_pos is not None else line.rstrip()

    @staticmethod
    def has_unclosed_tokens(s: str) -> bool:
        """检查字符串是否存在未闭合的括号/方括号/花括号"""
        stack = []
        bracket_map = {")": "(", "]": "[", "}": "{"}

        for char in s:
            if char in bracket_map.values():  # 左括号入栈
                stack.append(char)
            elif char in bracket_map.keys():  # 右括号匹配
                if not stack or stack[-1] != bracket_map[char]:
                    # 多余右括号，视为已闭合（仅关心未闭合左括号）
                    continue
                stack.pop()

        return len(stack) > 0  # 栈非空=有未闭合括号

    @staticmethod
    def is_third_party_module(module: Optional[str]) -> bool:
        """判断模块是否为第三方库（包括标准库和第三方安装库）"""
        if module is None:
            return False

        try:
            # 获取模块文件路径
            if module not in sys.modules:
                return False
            module_file = inspect.getfile(sys.modules[module])
            module_file = os.path.normpath(module_file)

            # 处理__pycache__路径的情况
            if "__pycache__" in module_file:
                module_file = module_file.replace("__pycache__", "")
                module_file = module_file.replace(".pyc", ".py").replace(".pyo", ".py")
                module_file = os.path.normpath(module_file)

            # 获取标准库路径（通过os模块的实际位置）
            import os as os_module
            standard_lib_dir = os.path.dirname(os.path.dirname(os_module.__file__))
            standard_lib_dir = os.path.normpath(standard_lib_dir)

            # 获取所有site-packages路径（系统和用户级别）
            site_packages_dirs = site.getsitepackages() + [site.getusersitepackages()]
            site_packages_dirs = [
                os.path.normpath(d)
                for d in site_packages_dirs
                if os.path.exists(d)
            ]

            # 辅助函数：检查文件是否在指定路径下（处理符号链接和跨平台问题）
            def is_in_base_path(file_path: str, base_path: str) -> bool:
                file_path = os.path.realpath(file_path)
                base_path = os.path.realpath(base_path)
                try:
                    return os.path.commonpath([file_path, base_path]) == base_path
                except ValueError:
                    return False

            # 检查是否在标准库路径
            if is_in_base_path(module_file, standard_lib_dir):
                return True
            # 检查是否在任何site-packages路径
            for sp_dir in site_packages_dirs:
                if is_in_base_path(module_file, sp_dir):
                    return True
            # 否则为用户程序
            return False
        except (TypeError, OSError, AttributeError, ValueError):
            return False

    @staticmethod
    def extract_function_body(frame: inspect.FrameInfo) -> Optional[str]:
        """提取函数或类方法的完整源码，并剔除文档字符串"""
        try:
            if frame.function == "<module>":
                return None  # 模块顶层，不在函数内

            func_name = frame.function
            locals_dict = frame.frame.f_locals
            globals_dict = frame.frame.f_globals
            func_obj = None

            # 1. 在局部变量中查找函数/类方法
            for name, obj in locals_dict.items():
                if inspect.isclass(obj):
                    # 检查类的方法（包括实例方法、静态方法等）
                    for method_name, method_obj in inspect.getmembers(obj):
                        if (
                            (inspect.isfunction(method_obj) or inspect.ismethod(method_obj))
                            and method_name == func_name
                        ):
                            func_obj = method_obj
                            break
                elif inspect.isfunction(obj) or inspect.ismethod(obj):
                    if obj.__name__ == func_name:
                        func_obj = obj
                        break

            # 2. 局部变量找不到则在全局变量中查找
            if func_obj is None:
                for name, obj in globals_dict.items():
                    if inspect.isfunction(obj) or inspect.ismethod(obj):
                        if obj.__name__ == func_name:
                            func_obj = obj
                            break

            if func_obj is None:
                return None

            # 3. 提取源码并移除文档字符串
            source_code = inspect.getsource(func_obj)
            tree = ast.parse(source_code)
            func_node = tree.body[0]  # 假设源码仅包含一个函数/类定义

            # NOTE: 检查是否存在文档字符串节点
            docstring = ast.get_docstring(func_node)
            if all([
                docstring,
                func_node.body,
                isinstance(func_node.body[0], ast.Expr),
                ExceptionStackFormatter().return_docstring,
                ]):
                doc_expr = func_node.body[0]
                # 将源码按行分割，计算文档字符串的位置
                lines = source_code.split("\n")
                cum_line_lens = [0]  # 累计每行的起始索引（包含换行符）
                for line in lines[:-1]:
                    cum_line_lens.append(cum_line_lens[-1] + len(line) + 1)  # +1 代表换行符
                if lines[-1]:
                    cum_line_lens.append(cum_line_lens[-1] + len(lines[-1]))
                # 计算文档字符串在源码中的起始和结束索引
                doc_start = cum_line_lens[doc_expr.lineno - 1] + doc_expr.col_offset
                doc_end = cum_line_lens[doc_expr.end_lineno - 1] + doc_expr.end_col_offset
                # 移除文档字符串
                source_without_doc = source_code[:doc_start] + source_code[doc_end:]
                return source_without_doc
            else:
                return source_code

        except (OSError, TypeError, AttributeError, SyntaxError):
            return None

    def format(self) -> str:
        """格式化当前异常的堆栈信息，支持多行代码拼接"""
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_traceback is None:
            return "当前没有异常信息"

        exception_message = f"{exc_type.__name__}: {exc_value}"

        # 增大上下文行数确保覆盖多行语句
        frames = inspect.trace(context=100)
        stack_results = []

        for i, frame in enumerate(frames):
            # 获取完整报错代码
            full_error_code = ""
            try:
                filename = frame.filename
                # 优先从文件读取完整内容（最可靠）
                if filename != "<stdin>":
                    with open(filename, "r", encoding="utf-8") as f:
                        file_lines = f.readlines()

                    current_idx = frame.lineno - 1  # 转换为0-based索引
                    if not (0 <= current_idx < len(file_lines)):
                        raise ValueError("无效行号")

                    # 初始化当前行列表
                    full_line_parts = [file_lines[current_idx]]

                    # 向后拼接（处理续行）
                    next_idx = current_idx + 1
                    while next_idx < len(file_lines):
                        current_combined = "".join(full_line_parts) + file_lines[next_idx]
                        stripped_combined = self.strip_comment(current_combined)
                        # 有未闭合括号或反斜杠结尾=续行
                        if self.has_unclosed_tokens(stripped_combined) or stripped_combined.endswith("\\"):
                            full_line_parts.append(file_lines[next_idx])
                            next_idx += 1
                        else:
                            break

                    # 向前拼接（处理前序续行）
                    prev_idx = current_idx - 1
                    while prev_idx >= 0:
                        prev_line_stripped = self.strip_comment(file_lines[prev_idx])
                        temp_combined = file_lines[prev_idx] + "".join(full_line_parts)
                        temp_combined_stripped = self.strip_comment(temp_combined)
                        if self.has_unclosed_tokens(temp_combined_stripped) or prev_line_stripped.endswith("\\"):
                            full_line_parts.insert(0, file_lines[prev_idx])
                            prev_idx -= 1
                        else:
                            break

                    full_error_code = "".join(full_line_parts).strip()
                else:
                    # stdin模式：从扩大后的上下文拼接
                    if frame.code_context:
                        current_ctx_idx = frame.index  # 上下文列表中当前行的索引
                        code_lines = frame.code_context
                        full_line_parts = [code_lines[current_ctx_idx]]

                        # 向后拼接上下文
                        next_ctx_idx = current_ctx_idx + 1
                        while next_ctx_idx < len(code_lines):
                            current_combined = "".join(full_line_parts) + code_lines[next_ctx_idx]
                            stripped_combined = self.strip_comment(current_combined)
                            if self.has_unclosed_tokens(stripped_combined) or stripped_combined.endswith("\\"):
                                full_line_parts.append(code_lines[next_ctx_idx])
                                next_ctx_idx += 1
                            else:
                                break

                        # 向前拼接上下文
                        prev_ctx_idx = current_ctx_idx - 1
                        while prev_ctx_idx >= 0:
                            prev_line_stripped = self.strip_comment(code_lines[prev_ctx_idx])
                            temp_combined = code_lines[prev_ctx_idx] + "".join(full_line_parts)
                            temp_combined_stripped = self.strip_comment(temp_combined)
                            if self.has_unclosed_tokens(temp_combined_stripped) or prev_line_stripped.endswith("\\"):
                                full_line_parts.insert(0, code_lines[prev_ctx_idx])
                                prev_ctx_idx -= 1
                            else:
                                break

                        full_error_code = "".join(full_line_parts).strip()
            except Exception:
                # 异常回退到原有逻辑，但修复了context索引问题
                if frame.code_context and 0 <= frame.index < len(frame.code_context):
                    full_error_code = frame.code_context[frame.index].strip()
                else:
                    full_error_code = ""

            # 原有逻辑保留
            if i < self.return_stack_layer:
                module_name = frame.frame.f_globals.get("__name__")
                code_type = "第三方库" if self.is_third_party_module(module_name) else "用户程序"
                # 根据需要是否返回第三方库的源码
                if code_type == '第三方库' and not self.return_third_pkg:
                    continue

                # NOTE: exec(compiled_code, exec_globals) 是 self.execute_py_file 执行 py 程序文件的场景
                # 此时，堆栈的第一条异常代码为 exec(compiled_code, exec_globals)，需要过滤
                # NOTE: 注意：此时的堆栈编号从 1 开始，默认从 0 开始，有变化
                if code_type == '用户程序' and full_error_code == 'exec(compiled_code, exec_globals)':
                    continue

                exception_source = self.extract_function_body(frame)
                formatted_source_part = ""

                if exception_source:
                    formatted_source = exception_source.replace("\n", "\n        ").rstrip()
                    formatted_source_part = f"    - 参考源码: ```python\n        {formatted_source}\n    ```\n"

                stack_entry = (
                    f"异常堆栈-{i}:\n"
                    f"    - 代码文件：{filename}\n"
                    f"    - 代码类型：{code_type}\n"
                    f"    - 异常代码：{full_error_code}\n"
                    f"{formatted_source_part}"
                )
                stack_results.append(stack_entry)

        result = f"异常信息：{exception_message}\n" + "\n".join(stack_results)

        output_path = proj_dir / 'inputs/code_exception_stack_info.txt'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
            print(f'✅ 文件已保存到: {output_path}\n')
        return result

    def execute_py_file(self, file_path: str) -> str:
        """执行指定的.py文件，如果执行异常则格式化并返回堆栈信息"""
        if not os.path.isfile(file_path):
            return f"文件不存在: {file_path}"

        if not file_path.endswith('.py'):
            return f"不是有效的Python文件: {file_path}"

        # 将文件所在目录添加到模块搜索路径
        file_dir = os.path.dirname(os.path.abspath(file_path))
        original_sys_path = sys.path.copy()
        sys.path.insert(0, file_dir)

        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()

            # 创建执行命名空间
            exec_globals = {
                '__name__': '__main__',
                '__file__': file_path,
            }

            # 🔴 修复核心：用compile()编译代码，指定原文件路径为filename，保留行号上下文
            compiled_code = compile(file_content, file_path, "exec")
            exec(compiled_code, exec_globals)

            return "文件执行成功，无异常"

        except Exception:
            # 异常时格式化堆栈信息
            return self.format()

        finally:
            # 恢复原始搜索路径
            sys.path = original_sys_path


# 单元测试样例
def test_user_code_exception():
    """测试用户程序代码异常"""
    try:
        def divide(a, b):
            """除法函数"""
            return a / b

        divide(10, 0)
    except:
        formatter = ExceptionStackFormatter()
        print("=== 用户程序异常测试 ===")
        print(formatter.format())
        print("\n" + "=" * 50 + "\n")


def test_third_party_exception():
    """测试第三方库异常"""
    try:
        import json
        import requests
        requests.get('/')
        # json.runserver()
    except:
        formatter = ExceptionStackFormatter(return_third_pkg=True, return_stack_layer=20)
        print("=== 第三方库异常测试 ===")
        print(formatter.format())
        print("\n" + "=" * 50 + "\n")


def test_class_method_exception():
    """测试类方法异常"""
    try:
        class Calculator:
            """计算器类"""
            def multiply(self, a, b):
                """乘法方法"""
                return a * b

            def complex_calculation(self, x, y):
                """复杂计算，故意制造类型错误"""
                # 两个字符串相乘会抛出TypeError
                result = self.multiply("string1", "string2")
                return result

        calc = Calculator()
        calc.complex_calculation(5, 10)
    except Exception:
        formatter = ExceptionStackFormatter()
        print("=== 类方法异常测试 ===")
        print(formatter.format())
        print("\n" + "=" * 50 + "\n")


# 新增：测试执行.py文件的功能
def execute_py_file(test_file_path):
    '''
    Desc:
        执行 python 文件，获取结构化的异常报错信息
    '''
    # NOTE: return_stack_layer 返回的堆栈的最大深度
    # NOTE: return_third_pkg 是否返回包含第三包的堆栈
    return_stack_layer = 10
    formatter = ExceptionStackFormatter(return_third_pkg=True, return_stack_layer=return_stack_layer)
    print("=== 执行外部.py文件异常测试 ===")
    print(formatter.execute_py_file(test_file_path))
    print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    # test_user_code_exception()
    # test_third_party_exception()
    # test_class_method_exception()

    # NOTE: test_file_path 报错的源文件
    test_file_path = proj_dir / 'utils/utils.py'
    execute_py_file(test_file_path.as_posix())