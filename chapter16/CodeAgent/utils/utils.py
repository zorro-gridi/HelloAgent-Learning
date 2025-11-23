import os
import fnmatch
import re

class ProjectTreeGenerator:
    def __init__(self):
        self.default_exclude_dirs = ['.git', '__pycache__', '.idea', 'venv', 'node_modules']
        self.default_exclude_files = ['.DS_Store', '.gitignore', '*.pyc']


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


def write_code_to_files(input_content: str):
    """
    从输入内容中匹配文件名和代码块，将代码写入对应的文件中。

    Args:
        input_content: 包含文件名和代码块的文本内容。
    """
    # 正则表达式模式：匹配文件名和代码块
    pattern = r'^```(\S+)\n([\s\S]+?)\n```$'

    # 查找所有匹配项
    matches = re.findall(pattern, input_content, re.MULTILINE)

    for filename, code in matches:
        # 去除文件名前后的空白字符
        filename = filename.strip()
        # 去除代码前后的空白字符（可选，根据需求调整）
        code = code.strip()

        # 确保文件所在目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # 写入文件
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)

        print(f"成功写入文件：{filename}")



def create_project_files(file_list):
    """
    根据提供的文件列表创建项目文件和目录结构。

    :param file_list: 一个包含文件路径字符串的列表。
    """
    for file_path in file_list:
        try:
            # 获取目录路径
            directory = os.path.dirname(file_path)

            # 如果目录不存在，则创建
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
                print(f"目录已创建: {directory}")

            # 创建文件（如果已存在则不会覆盖）
            with open(file_path, 'a') as f:
                pass  # 'a'模式打开文件，如果文件不存在则创建，如果存在则不做任何操作

            print(f"文件已创建或已存在: {file_path}")

        except OSError as e:
            print(f"创建文件 {file_path} 时出错: {e}")

# 你的文件列表
files_to_create = [
"package.json",
"vite.config.ts",
"src/main.ts",
"src/App.vue",
"src/components/Layout/Header.vue",
"src/components/Layout/Footer.vue",
"src/components/Layout/ProcessNavigation.vue",
"src/components/Layout/MainContent.vue",
"src/components/TaskTypes/CodeDebug.vue",
"src/components/TaskTypes/CodeOptimize.vue",
"src/components/TaskTypes/CodeReview.vue",
"src/components/TaskTypes/CodeProofread.vue",
"src/components/Common/CodeEditor.vue",
"src/components/Common/ProcessNode.vue",
"src/types/index.ts",
"src/store/index.ts",
"src/utils/constants.ts",
"index.html",
    ]


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

    create_project_files(files_to_create)
    print("\n操作完成！")


    # with open('/Users/zorro/Documents/成长笔记/Agent开发/CodeAgent/frontend_contents.txt', 'r') as f:
    #     write_code_to_files(f.read())