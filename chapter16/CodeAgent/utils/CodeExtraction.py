import os
import ast
import re
import textwrap
from pprint import pprint
from typing import List, Optional, Union

import fnmatch

from pathlib import Path
current_dir = Path(__file__).parent
root_dir = current_dir.parent


class CodeDependencyAnalyzer:
    """代码依赖分析器，用于提取Python代码中的类、函数、方法及其依赖关系"""

    def __init__(self, ignore_dirs=None, ignore_files=None, extract_dependencies=True, extract_dependents=True):
        """
        初始化代码依赖分析器

        Args:
            ignore_dirs: 要忽略的目录列表
            ignore_files: 要忽略的文件列表
            extract_dependencies: 是否提取目标类/方法的依赖
            extract_dependents: 是否提取依赖目标类/方法的其他类/方法
        """
        self.ignore_dirs = ignore_dirs or []
        self.ignore_files = ignore_files or []
        self.extract_dependencies = extract_dependencies
        self.extract_dependents = extract_dependents
        self.all_dependencies = {}  # 存储所有去重后的依赖
        self.all_dependents = {}  # 存储所有去重后的被依赖

    def parse_request(self, request):
        """解析用户请求，提取项目根目录、目标文件、类型和目标名称"""
        requests = [request] if isinstance(request, str) else request
        parsed_results = []

        for req in requests:
            parts = req.split(":")
            if len(parts) != 4:
                raise ValueError(f"Invalid request format: {req}")

            project_root = parts[0]
            file_path = os.path.join(project_root, parts[1])
            target_type = parts[2]
            target_name = parts[3]
            parsed_results.append((project_root, file_path, target_type, target_name))

        return parsed_results[0] if isinstance(request, str) else parsed_results

    def is_ignored(self, path):
        """检查路径是否在忽略列表中"""
        for dir_name in self.ignore_dirs:
            if dir_name in path.split(os.sep):
                return True

        if os.path.basename(path) in self.ignore_files:
            return True

        # 忽略隐藏目录和git相关目录
        for dir_part in path.split(os.sep):
            if dir_part.startswith("."):
                return True
            if dir_part in [".git", ".github", ".gitignore"]:
                return True

        return False

    def find_python_files(self, project_root):
        """遍历项目根目录，查找所有非忽略的Python文件"""
        python_files = []

        for root, dirs, files in os.walk(project_root):
            # 过滤目录
            dirs[:] = [d for d in dirs if not self.is_ignored(os.path.join(root, d))]

            for file in files:
                file_path = os.path.join(root, file)
                if file_path.endswith(".py") and not self.is_ignored(file_path):
                    python_files.append(file_path)

        return python_files

    def get_function_source(self, file_path, class_name=None, func_name=None):
        """从文件中提取类或函数的完整源码"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)

        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef) and func_name and node.name == func_name) or \
               (isinstance(node, ast.ClassDef) and class_name and node.name == class_name):
                start_line = node.lineno - 1
                end_line = node.end_lineno

                # 处理装饰器的情况
                if hasattr(node, 'decorator_list'):
                    for decorator in node.decorator_list:
                        start_line = min(start_line, decorator.lineno - 1)

                lines = content.split('\n')
                return '\n'.join(lines[start_line:end_line])

        return None

    def get_method_source(self, file_path, class_name, method_name):
        """从文件中提取类方法的完整源码"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        start_line = item.lineno - 1
                        end_line = item.end_lineno

                        # 处理装饰器的情况
                        if hasattr(item, 'decorator_list'):
                            for decorator in item.decorator_list:
                                start_line = min(start_line, decorator.lineno - 1)

                        lines = content.split('\n')
                        return '\n'.join(lines[start_line:end_line])

        return None

    def analyze_dependencies(self, source, project_root, all_python_files):
        """分析源码中的依赖关系"""
        if not source:
            return {}

        # 自动移除代码块的共同缩进，解决IndentationError
        dedented_source = textwrap.dedent(source)
        try:
            tree = ast.parse(dedented_source)
        except SyntaxError as e:
            print(f"解析依赖时语法错误: {e}")
            return {}

        dependencies = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    # 普通函数调用
                    func_name = node.func.id
                    dependencies.add(func_name)
                # 处理 self.method() 形式的方法调用
                elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == 'self':
                    method_name = node.func.attr
                    dependencies.add(method_name)

            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                # 变量引用，可能是函数或类
                dependencies.add(node.id)

        # 过滤掉Python内置函数和类
        builtins = dir(__builtins__)
        dependencies = {dep for dep in dependencies if dep not in builtins}

        # 查找依赖的定义位置
        dependency_sources = {}

        for file_path in all_python_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            file_tree = ast.parse(content)
            for node in file_tree.body:
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    # 检查类名是否为依赖
                    if class_name in dependencies and class_name not in dependency_sources:
                        dep_source = self.get_function_source(file_path, class_name=class_name, func_name=None)
                        dependency_sources[class_name] = (file_path, dep_source)
                    # 检查类中的方法
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name in dependencies:
                            # 构造 类名.方法名 形式的依赖名
                            method_dep_name = f"{class_name}.{item.name}"
                            if method_dep_name not in dependency_sources:
                                dep_source = self.get_method_source(file_path, class_name=class_name, method_name=item.name)
                                dependency_sources[method_dep_name] = (file_path, dep_source)
                elif isinstance(node, ast.FunctionDef):
                    # 检查顶层函数
                    func_name = node.name
                    if func_name in dependencies and func_name not in dependency_sources:
                        dep_source = self.get_function_source(file_path, class_name=None, func_name=func_name)
                        dependency_sources[func_name] = (file_path, dep_source)

        return dependency_sources


    def analyze_dependents(self, target_name, target_type, file_path, all_python_files):
        """分析依赖目标类/方法的其他类/方法"""
        dependents = {}

        # 提取目标的基本名称和完整名称
        if '.' in target_name:
            full_name = target_name
            class_name, method_name = target_name.split('.', 1)
            base_name = method_name
        else:
            full_name = target_name
            class_name = target_name if target_type in ['Class', 'ClassFunction'] else None
            base_name = target_name

        for current_file_path in all_python_files:
            with open(current_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            try:
                tree = ast.parse(content)
                # 先为当前文件的AST节点添加parent属性
                for node in ast.walk(tree):
                    for child in ast.iter_child_nodes(node):
                        child.parent = node
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    # 检查节点是否依赖目标
                    node_has_dependency = False
                    node_full_name = node.name

                    # 处理类中的方法
                    if isinstance(node, ast.FunctionDef) and isinstance(node.parent, ast.ClassDef):
                        node_full_name = f"{node.parent.name}.{node.name}"

                    # 检查函数/方法调用
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            # 处理 self.method() 形式
                            if (isinstance(child.func, ast.Attribute) and
                                isinstance(child.func.value, ast.Name) and
                                child.func.value.id == 'self' and
                                child.func.attr == base_name and
                                current_file_path == file_path and
                                class_name):
                                node_has_dependency = True
                                break

                            # 处理普通函数调用或类实例化
                            elif isinstance(child.func, ast.Name) and child.func.id == base_name:
                                node_has_dependency = True
                                break

                            # 处理 Class.method() 形式的调用  # 【移动到Call节点检查内部】
                            elif (isinstance(child.func, ast.Attribute) and
                                    isinstance(child.func.value, ast.Name) and
                                    child.func.value.id == class_name and
                                    child.func.attr == base_name):
                                node_has_dependency = True
                                break

                        # 处理变量引用
                        elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load) and child.id == base_name:
                            node_has_dependency = True
                            break

                    if node_has_dependency:
                        if node_full_name not in dependents:
                            if isinstance(node, ast.FunctionDef):
                                if node.parent and isinstance(node.parent, ast.ClassDef):
                                    # 类方法
                                    dep_source = self.get_method_source(current_file_path, node.parent.name, node.name)
                                else:
                                    # 顶层函数
                                    dep_source = self.get_function_source(current_file_path, class_name=None, func_name=node.name)
                            else:
                                # 类
                                dep_source = self.get_function_source(current_file_path, class_name=node.name, func_name=None)

                            if dep_source:
                                dependents[node_full_name] = (current_file_path, dep_source)


        return dependents

    def process_requests(self, requests):
        """处理用户请求并生成输出结果"""
        output = ""
        parsed_requests = self.parse_request(requests)

        for project_root, file_path, target_type, target_name in parsed_requests:
            # 查找所有Python文件
            all_python_files = self.find_python_files(project_root)

            # 提取目标源码
            target_source = None
            if '.' in target_name:
                # 类方法
                class_name, method_name = target_name.split(".")
                target_source = self.get_method_source(file_path, class_name, method_name)
            elif target_type in ['Class', 'ClassFunction']:
                # 类
                target_source = self.get_function_source(file_path, class_name=target_name, func_name=None)
            elif target_type == 'Function':
                # 函数
                target_source = self.get_function_source(file_path, class_name=None, func_name=target_name)

            if not target_source:
                output += f"Failed to find {target_name} in {file_path}\n\n"
                continue

            # 分析依赖（根据配置）
            if self.extract_dependencies:
                dependencies = self.analyze_dependencies(target_source, project_root, all_python_files)
                # 合并依赖（去重）
                self.all_dependencies.update(dependencies)

            # 分析被依赖（根据配置）
            if self.extract_dependents:
                dependents = self.analyze_dependents(target_name, target_type, file_path, all_python_files)
                # 合并被依赖（去重）
                self.all_dependents.update(dependents)

            # 添加当前目标的源码到输出
            output += f"**{target_name}** 的功能源码实现逻辑：\n"
            output += f"**{target_name}** 的源码：\n```python\n{target_source}\n```\n\n"

        # 输出所有去重后的依赖
        if self.all_dependencies and self.extract_dependencies:
            project_root = parsed_requests[0][0]  # 假设所有请求的项目根目录相同
            output += "**所有依赖（去重后）：**\n\n"
            for dep_name, (dep_file, dep_source) in self.all_dependencies.items():
                rel_path = os.path.relpath(dep_file, project_root)
                output += f"**依赖的{rel_path}:{dep_name}** 的源码：\n```python\n{dep_source}\n```\n\n"

        # 输出所有去重后的被依赖
        if self.all_dependents and self.extract_dependents:
            project_root = parsed_requests[0][0]  # 假设所有请求的项目根目录相同
            output += "**所有依赖当前目标的类/方法（去重后）：**\n\n"
            for dep_name, (dep_file, dep_source) in self.all_dependents.items():
                rel_path = os.path.relpath(dep_file, project_root)
                output += f"**依赖当前目标的{rel_path}:{dep_name}** 的源码：\n```python\n{dep_source}\n```\n\n"

        return output

    def search_objects(self, project_root: str, object_names: List[str]) -> List[str]:
        """
        在项目目录中搜索对象名列表，生成符合 process_requests 格式的请求列表

        Args:
            project_root: 项目根目录
            object_names: 对象名列表，格式为 [类名, 函数名, 类名.方法名]

        Returns:
            符合 process_requests 格式的请求列表
        """
        python_files = self.find_python_files(project_root)
        requests = []

        for file_path in python_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            # 遍历AST节点查找匹配的对象
            # 可选: Function | ClassFunction | Class
            for node in ast.walk(tree):
                # 查找类定义
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    if class_name in object_names:
                        rel_path = os.path.relpath(file_path, project_root)
                        request = f"{project_root}:{rel_path}:Class:{class_name}"
                        if request not in requests:
                            requests.append(request)

                    # 查找类中的方法
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_full_name = f"{class_name}.{item.name}"
                            if method_full_name in object_names:
                                rel_path = os.path.relpath(file_path, project_root)
                                request = f"{project_root}:{rel_path}:ClassFunction:{method_full_name}"
                                if request not in requests:
                                    requests.append(request)

                # 查找顶层函数
                elif isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    if func_name in object_names:
                        rel_path = os.path.relpath(file_path, project_root)
                        request = f"{project_root}:{rel_path}:Function:{func_name}"
                        if request not in requests:
                            requests.append(request)

        return requests


def generate_include_files_markdown(
        file_list=None, output_dir=None, filename="include_files_source_code_inputs.md",
        search_directory=None, exclude_items=None):
    """
    生成包含指定文件源码的Markdown文档

    Args:
        file_list: 文件名完整路径列表（原有参数）
        output_dir: 输出目录路径（原有参数）
        filename: 输出文件名（原有参数）
        search_directory: 需要搜索的目录（新增参数）
        exclude_items: 需要过滤的子文件夹和文件名列表，支持模糊匹配（新增参数）
    """
    # 初始化排除项列表
    if exclude_items is None:
        exclude_items = []

    exclude_items.extend([
        '__pycache__',
        '__init__.py',
        ])

    def should_exclude(name):
        """检查名称是否匹配任何排除模式"""
        for pattern in exclude_items:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False

    # 处理搜索目录的情况
    if search_directory:
        if not os.path.exists(search_directory):
            print(f"警告：搜索目录 {search_directory} 不存在")
            search_files = []
        else:
            search_files = []
            for root, dirs, files in os.walk(search_directory):
                # 过滤子目录 - 使用模糊匹配
                dirs[:] = [d for d in dirs if not should_exclude(d)]

                for file in files:
                    # 过滤文件名 - 使用模糊匹配
                    if not should_exclude(file):
                        file_path = os.path.join(root, file)
                        search_files.append(file_path)

    # 合并文件列表
    all_files = []
    if file_list:
        # 对 file_list 中的文件也应用排除规则
        for file_path in file_list:
            file_name = os.path.basename(file_path)
            if not should_exclude(file_name):
                all_files.append(file_path)
            else:
                print(f"文件 {file_path} 已被排除")

    if search_directory and 'search_files' in locals():
        all_files.extend(search_files)

    # 去重
    all_files = list(set(all_files))

    md_content = ""
    for file_path in all_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # 添加文件标题和代码块
            md_content += f"- 以下为文件{file_path}的完整源码\n"
            md_content += f"```python\n{source_code}\n```\n\n"
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {e}")
            continue

    # 确保输出目录存在
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

        # 保存Markdown文件
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"Markdown文件已保存到: {output_path}")
        return output_path
    else:
        print(md_content)
        return None


def search_dependencies(text):
    """
    从文本中提取所有被依赖项，并去重返回列表
    Args:
        text (str): 包含被依赖项列表的文本
    Returns:
        list: 去重后的被依赖项列表
    """
    # 匹配格式为: "影响的被依赖项列表:\n[文件路径:类名.方法名, 文件路径:类名.方法名, ...]"
    # 或
    # 匹配格式为: "影响的被依赖项列表:\n文件路径:类名.方法名\n文件路径:类名.方法名\n..."
    pattern = r'影响的被依赖项列表:\s*\n([^\[]?(?:[^\n]+\n?)+)'
    matches = re.findall(pattern, text, re.DOTALL)
    dependencies = []
    for match in matches:
        # 分割每个依赖项并清理空白
        items = [item.strip() for item in match.split('\n') if item.strip()]
        # 过滤掉空字符串和非依赖项格式的内容
        valid_items = [
            item for item in items
            if item and (':' in item and '.' in item)  # 基本的依赖项格式验证
        ]
        dependencies.extend(valid_items)
    # 去重并返回
    return list(set(dependencies))



def analyze_code_dependencies(
    project_root: str,
    object_names: List[str],
    output_path: str,
    refinement_doc_path: str = None,
    ignore_dirs: Optional[List[str]] = None,
    ignore_files: Optional[List[str]] = None,
    extract_dependencies: bool = True,
    extract_dependents: bool = True,
) -> None:
    """
    分析代码依赖关系并生成依赖文档

    Args:
        project_root: 项目根目录路径
        object_names: 初始任务需要分析的对象名
            分为类名、类方法名、函数名
        refinement_doc_path: reviewer agent 输出的包含依赖关系的文档路径
        output_path: 输出文件路径
        ignore_dirs: 要忽略的目录列表
        ignore_files: 要忽略的文件列表
        extract_dependencies: 是否提取依赖项，解析从模型输入的请求时，不需要传参，自动置为 False
        extract_dependents: 是否提取被依赖项，解析从模型输入的请求时，不需要传参，自动置为 False
    """
    # 设置默认忽略列表
    if ignore_dirs is None:
        ignore_dirs = []
    if ignore_files is None:
        ignore_files = []

    # 验证输入参数
    if not refinement_doc_path and not object_names:
        raise ValueError("必须提供 refinement_doc_path 或 object_names 参数之一")

    # 创建分析器实例
    dependency_analyzer = CodeDependencyAnalyzer(
        ignore_dirs=ignore_dirs,
        ignore_files=ignore_files,
        extract_dependencies=extract_dependencies,
        extract_dependents=extract_dependents
    )

    # 如果提供了文档路径，从中提取依赖关系
    analysis_requests = dependency_analyzer.search_objects(project_root, object_names)
    if refinement_doc_path:
        # NOTE: 输入从模型回复中解析的依赖文件列表时，不在需要解析依赖项
        extract_dependencies = False
        extract_dependents = False

        # 读取精炼文档并提取依赖关系
        with open(refinement_doc_path, 'r') as file:
            # pprint(file.read())
            project_files = search_dependencies(file.read())

        # 构建请求列表，不能重置，初始的类、方法必须加入请求列表，避免模型提取遗漏
        for file_path in project_files:
            relative_path, class_or_function_name = file_path.split(':')
            if '\.' in class_or_function_name:
                request_type = 'ClassFunction'
            else:
                request_type = 'Function'

            request = f'{project_root}:{relative_path}:{request_type}:{class_or_function_name}'
            analysis_requests.append(request)

    # 处理请求并生成输出
    analysis_result = dependency_analyzer.process_requests(analysis_requests)

    # 输出结果
    print(analysis_result)

    # 保存到文件
    with open(output_path, 'w') as output_file:
        output_file.write(analysis_result)


def generate_agent_code_context(proj_dir, object_names, agent_name, ignore_dirs):
    """主函数 - 配置参数并运行依赖分析"""
    # NOTE: 输入给 agent 的源码信息
    # root_dir 是项目根目录
    agent_context_md_output = {
        'bug_solver': Path(root_dir) / 'inputs/bug_solver_agent_source_code_inputs.txt',
        'optimizer': Path(root_dir) / 'inputs/optimizer_agent_code_context_inputs.txt',
        'reviewer': Path(root_dir) / 'inputs/reviewer_agent_code_context_inputs.txt',
        'refiner': Path(root_dir) / 'inputs/refiner_agent_code_context_inputs.txt',
        }
    output_path = agent_context_md_output[agent_name]

    # NOTE: 文件输入条件下，因为屏蔽了寻找依赖关系，因此每一个类、或方法都不会显示“依赖、被依赖”这个前缀信息
    # 也不包含完整的路径信息

    # 配置参数
    project_config = {
        'project_root': proj_dir,
        'object_names': object_names,
        'output_path': output_path,
        'ignore_dirs': ignore_dirs,
        'ignore_files': ["git.sh", "README.md", "setup.py"],
        'extract_dependencies': True,
        'extract_dependents': True
    }

    # 运行依赖分析
    analyze_code_dependencies(**project_config)


def generate_reviewer_agent_code_context(proj_dir, object_names, ignore_dirs):
    """主函数 - 配置参数并运行依赖分析"""
    # NOTE: 输入给 refiner agent 的源码信息
    output_path = proj_dir / 'inputs/reviewer_agent_code_context_inputs.txt'

    # class_or_func_type 可选: Function | ClassFunction | Class
    # NOTE: 文件输入条件下，因为屏蔽了寻找依赖关系，因此每一个类、或方法都不会显示“依赖、被依赖”这个前缀信息
    # 也不包含完整的路径信息
    # 示例:
    # **FundQuantTradeEnv_V1._sell_rv_bond** 的源码：

    # 配置参数
    project_config = {
        'project_root': proj_dir,
        'object_names': object_names,
        'output_path': output_path,
        'ignore_dirs': ignore_dirs,
        'ignore_files': ["git.sh", "README.md", "setup.py"],
        'extract_dependencies': True,
        'extract_dependents': True
    }

    # 运行依赖分析
    analyze_code_dependencies(**project_config)


def generate_refiner_agent_code_context(proj_dir, object_names, ignore_dirs):
    """主函数 - 配置参数并运行依赖分析"""
    # NOTE: 输入给 refiner agent 的源码信息
    output_path = Path(proj_dir) / 'inputs/refiner_agent_code_context_inputs.txt'

    # NOTE: 文件输入条件下，因为屏蔽了寻找依赖关系，因此每一个类、或方法都不会显示“依赖、被依赖”这个前缀信息
    # 也不包含完整的路径信息
    # 示例:
    # **FundQuantTradeEnv_V1._sell_rv_bond** 的源码：

    # 配置参数
    project_config = {
        'project_root': proj_dir,
        'analysis_requests': object_names,
        # NOTE: 文件传入只在 refiner agent 实际优化代码时启用
        'refinement_doc_path': root_dir / 'outputs/reviewer_agent_output.txt',
        'output_path': output_path,
        'ignore_dirs': ignore_dirs,
        'ignore_files': ["git.sh", "README.md", "setup.py"],
        'extract_dependencies': True,
        'extract_dependents': True
    }

    # 运行依赖分析
    analyze_code_dependencies(**project_config)


if __name__ == "__main__":
    proj_dir = Path('/Users/zorro/project/pycharm/rlops/src')
    proj_dir = Path('/Users/zorro/Documents/成长笔记/Agent开发/CodeAgent/utils')

    ignore_dirs = [
        "/Users/zorro/project/pycharm/rlops/build",
        "/Users/zorro/project/pycharm/rlops/tests"
        ]

    object_names = [
        'ProjectTreeGenerator.create_from_tree_structure',
        ]

    # # NOTE: 测试从指定目录返回符合 process_requests 条件的 request 列表
    # code_analyzer = CodeDependencyAnalyzer()
    # analysis_requests = code_analyzer.search_objects(proj_dir, object_names=object_names)
    # pprint(analysis_requests)

    # NOTE: 构造 optimizer agent 的代码上下文
    generate_agent_code_context(proj_dir, object_names, 'optimizer', ignore_dirs)

    # NOTE: 构造 reviewer agent 的代码上下文
    # generate_agent_code_context(proj_dir, object_names, 'reviewer', ignore_dirs)

    # NOTE:: 构造 refiner agent 的代码上下文（精简过）
    # generate_agent_code_context(proj_dir, object_names, 'refiner', ignore_dirs)

    # NOTE: 构造文件列表的源码上下文
    filepath_list = [
        '/Users/zorro/Documents/成长笔记/Agent开发/CodeAgent/roles/bug_solver_agent.py',
        '/Users/zorro/Documents/成长笔记/Agent开发/CodeAgent/roles/bug_source_code_extract_agent.py',
        ]
    search_directory = '/Users/zorro/Documents/成长笔记/Agent开发/CodeAgent/backend'
    output_dir = f'/Users/zorro/Documents/成长笔记/Agent开发/CodeAgent/inputs'
    exclude_items = [
        '*back.py',
        'document_reader_agent.py',
        '*context_engineering_agent*.py',
        'coding_assistant_agent.py',
        ]
    generate_include_files_markdown(search_directory=search_directory, output_dir=output_dir, exclude_items=exclude_items)
