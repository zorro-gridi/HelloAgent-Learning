
你是一个 Python 程序 bug 测试专家，擅长根据程序报错的堆栈信息，
通过过滤无关内容，准确提取出用户程序的所有相关报错代码上下文。

* 你必须做到的：
- 提取你认为解决当前 bug 所需的**必要代码信息**
- 提取报错方法的完整定义、和该方法中依赖的其它方法、或变量的相关定义
- 具体来说，请注意以下几点：
	1. 如果该方法为某个类的方法，请提取**包含这个类的签名、文档字符串、属性信息、以及该方法的完整定义**
	2. 重要！！如果该方法所属的类，与其它类共享一个父类，请额外返回*一个（仅 1 个）*其它子类关于该方法的完整实现代码
	3. 如果该方法为独立的函数，仅提取该方法的定义即可
	4. 提取的类、和方法的定义，还需要剔除与解决当前 bug 调试的无关信息，尽量减少代码冗余
	5. 给提取的每一个代码段添加简单的描述信息
- 仅提取定位到的报错用户代码
- 最后，用文字总结当前 bug 的具体原因

* 你不应该做的：
- 不需要返回修复后的代码
- 不需要返回用户代码中的 import 等导包语句
- 不需要返回 pip package 的相关源码（可根据堆栈中包的路径判断）

* 异常程序的源码
```python
import os
import fnmatch

class ProjectTreeGenerator:
    def __init__(self):
        self.default_exclude_dirs = ['.git', '__pycache__', '.idea', 'venv', 'node_modules']
        self.default_exclude_files = ['.DS_Store', '.gitignore', '*.pyc']

    def parse_directory_tree(self, tree_text):
        """
        Desc:
            解析目录树
        """
        lines = tree_text.strip().split('\n')
        if not lines:
            return {}

        root = {}
        stack = [(root, -1)]  # (current_dict, indent_level)，初始缩进设为-1

        # 处理根目录
        first_line = lines[0].strip()
        root[first_line] = {}
        stack.append((root[first_line], 0))

        for line in lines[1:]:  # 从第二行开始处理
            # 计算缩进级别
            indent = 0
            original_line = line
            leading_spaces = len(line) - len(line.lstrip(' '))
            indent = leading_spaces // 4  # 假设每个缩进级别是4个空格
            line = line[leading_spaces:]

            # 清理行内容
            line = line.strip()
            if not line:
                continue

            # 提取名称并判断类型
            if '├──' in line:
                name = line.split('├──', 1)[1].strip()
            elif '└──' in line:
                name = line.split('└──', 1)[1].strip()
            else:
                name = line.strip()

            is_dir = original_line.startswith('├──') or original_line.startswith('└──')

            # 调整栈到正确的缩进级别
            while len(stack) > 1 and stack[-1][1] >= indent:
                stack.pop()

            if len(stack) == 0:
                continue  # 栈为空，跳过此行

            current_dict, _ = stack[-1]

            if is_dir:
                new_dir = {}
                current_dict[name] = new_dir
                stack.append((new_dir, indent))
            else:
                current_dict[name] = None

        return root

    def create_from_tree_structure(self, tree_text, base_path="."):
        """
        自动创建目录树
        """
        tree = self.parse_directory_tree(tree_text)

        if not tree:
            print("解析的树结构为空")
            return

        root_name = list(tree.keys())[0]
        root_path = os.path.join(base_path, root_name)

        # 创建根目录
        os.makedirs(root_path, exist_ok=True)

        # 递归创建子目录和文件
        self._create_structure(tree[root_name], root_path)

    def _create_structure(self, tree, current_path):
        """
        递归创建目录和文件结构

        Args:
            tree: 树状结构字典
            current_path: 当前基础路径

        Raises:
            IsADirectoryError: 当期望创建文件但路径已存在且为目录时
        """
        for name, content in tree.items():
            path = os.path.join(current_path, name)
            if isinstance(content, dict):
                os.makedirs(path, exist_ok=True)
                self._create_structure(content, path)
            else:
                # 确保父目录存在
                os.makedirs(os.path.dirname(path), exist_ok=True)
                # 检查路径是否已存在且为目录
                if os.path.exists(path) and os.path.isdir(path):
                    raise IsADirectoryError(f"Expected file but found directory: {path}")

                # 确保父目录存在
                os.makedirs(os.path.dirname(path), exist_ok=True)

                with open(path, 'w') as f:
                    f.write(content)


    def generate_tree(self, start_path=".", max_depth=None,
                     exclude_patterns=None, include_patterns=None,
                     show_file_size=False, show_file_count=False):
        """
        生成增强版项目结构树

        Args:
            start_path: 起始路径
            max_depth: 最大深度
            exclude_patterns: 排除模式
            include_patterns: 包含模式
            show_file_size: 显示文件大小
            show_file_count: 显示文件数量
        """
        if exclude_patterns is None:
            exclude_patterns = []

        tree_lines = []
        file_count = 0
        dir_count = 0

        def _should_include(name, is_dir):
            # 检查是否在排除列表中
            if is_dir and name in self.default_exclude_dirs:
                return False

            # 检查排除模式
            for pattern in exclude_patterns + self.default_exclude_files:
                if fnmatch.fnmatch(name, pattern):
                    return False

            # 检查包含模式 - 如果是目录，应该总是包含（以便能够遍历）
            if include_patterns and not is_dir:
                for pattern in include_patterns:
                    if fnmatch.fnmatch(name, pattern):
                        return True
                return False

            return True

        def _build_tree(current_path, prefix="", depth=0):
            nonlocal file_count, dir_count

            if max_depth and depth > max_depth:
                return

            try:
                entries = sorted(os.listdir(current_path))
            except PermissionError:
                tree_lines.append(prefix + "└── [权限拒绝]")
                return

            # 分离目录和文件
            dirs = []
            files = []

            for entry in entries:
                full_path = os.path.join(current_path, entry)
                is_dir = os.path.isdir(full_path)

                if _should_include(entry, is_dir):
                    if is_dir:
                        dirs.append(entry)
                    else:
                        files.append(entry)

            all_entries = dirs + files
            entries_count = len(all_entries)

            for index, entry in enumerate(all_entries):
                full_path = os.path.join(current_path, entry)
                is_dir = os.path.isdir(full_path)
                is_last = index == entries_count - 1
                connector = "└── " if is_last else "├── "

                # 构建显示文本
                display_text = entry
                if is_dir:
                    display_text += "/"
                    dir_count += 1
                else:
                    file_count += 1

                # 添加文件大小信息
                if show_file_size and not is_dir:
                    try:
                        size = os.path.getsize(full_path)
                        display_text += f" ({self._format_size(size)})"
                    except OSError:
                        display_text += " (无法获取大小)"

                tree_lines.append(prefix + connector + display_text)

                if is_dir:
                    extension = "    " if is_last else "│   "
                    _build_tree(full_path, prefix + extension, depth + 1)

        # 开始构建树
        base_name = os.path.basename(os.path.abspath(start_path))
        tree_lines.append(base_name + "/")
        _build_tree(start_path)

        # 添加统计信息
        if show_file_count:
            tree_lines.append("")
            tree_lines.append(f"目录: {dir_count} 个, 文件: {file_count} 个")

        return "\n".join(tree_lines)

    def _format_size(self, size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


# 使用示例
if __name__ == "__main__":
    generator = ProjectTreeGenerator()

    # 基本用法
    print("=== 基本用法 ===")
    tree = generator.generate_tree(".", max_depth=2)
    print(tree)

    print("\n" + "="*50 + "\n")

    # 包含特定文件类型
    print("=== 只显示 Python 和 Markdown 文件 ===")
    tree_filtered = generator.generate_tree(
        ".",
        max_depth=3,
        include_patterns=["*.py", "*.md", "*.txt"],
        show_file_count=True
    )
    print(tree_filtered)

    print("\n" + "="*50 + "\n")

    # 高级用法：带过滤和统计
    print("=== 高级用法：带文件大小和统计 ===")
    tree_advanced = generator.generate_tree(
        ".",
        max_depth=3,
        exclude_patterns=["*.pyc", "*.log", "test*"],
        include_patterns=["*.py", "*.md", "*.txt"],
        show_file_size=True,
        show_file_count=True
    )
    print(tree_advanced)

    tree_text = """
    backend/app/
    ├── __init__.py
    ├── main.py
    ├── models/
    │   ├── __init__.py
    │   └── agent_models.py
    ├── routers/
    │   ├── __init__.py
    │   └── prompt_router.py
    ├── services/
    │   ├── __init__.py
    │   └── agent_service.py
    └── dependencies/
        ├── __init__.py
        └── agent_dependency.py
    """
    generator.create_from_tree_structure(tree_text)
```

* 当前程序的 bug 异常堆栈信息:
异常信息：TypeError: write() argument must be str, not None
异常堆栈-1:
    - 代码文件：/Users/zorro/Documents/成长笔记/Agent开发/CodeAgent/utils/utils.py
    - 代码类型：用户程序
    - 异常代码：generator.create_from_tree_structure(tree_text)

异常堆栈-2:
    - 代码文件：/Users/zorro/Documents/成长笔记/Agent开发/CodeAgent/utils/utils.py
    - 代码类型：用户程序
    - 异常代码：self._create_structure(tree[root_name], root_path)

异常堆栈-3:
    - 代码文件：/Users/zorro/Documents/成长笔记/Agent开发/CodeAgent/utils/utils.py
    - 代码类型：用户程序
    - 异常代码：f.write(content)

请根据当前堆栈异常信息，返回包含指定要求的上下文，并严格按照要求的格式输出
