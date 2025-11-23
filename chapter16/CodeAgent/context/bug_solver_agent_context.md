
你是一位顶尖的 Python 程序 bug 调试解决大师，能够根据已知代码的异常信息、与原因分析，给出完美的 bug 优化解决方案。

- 你的任务关键词
解决、优化、bug调试

* 用户的异常描述
无

* 当前的 bug 源码上下文
根据堆栈异常信息分析，bug出现在文件创建过程中，当尝试写入文件内容时，参数为None导致的TypeError。

提取的相关代码段：

1. ProjectTreeGenerator类定义和__init__方法
```python
class ProjectTreeGenerator:
    def __init__(self):
        self.default_exclude_dirs = ['.git', '__pycache__', '.idea', 'venv', 'node_modules']
        self.default_exclude_files = ['.DS_Store', '.gitignore', '*.pyc']
描述：ProjectTreeGenerator类的基本定义和初始化方法，设置了默认的排除目录和文件模式。

parse_directory_tree方法完整定义

python
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
描述：解析目录树文本的方法，将文本转换为树状结构字典，其中文件节点的值为None。

_create_structure方法完整定义

python
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
描述：递归创建目录和文件结构的方法，当遇到文件节点时尝试写入内容，这里是异常发生的地方。

create_from_tree_structure方法完整定义

python
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
描述：从树状结构文本创建实际目录和文件的方法，调用parse_directory_tree和_create_structure。

Bug原因总结：
在_create_structure方法中，当处理文件节点时，代码尝试将content（从parse_directory_tree解析得到）写入文件。然而在parse_directory_tree方法中，文件节点的值被设置为None。当执行f.write(content)时，由于content为None，而write()方法期望接收字符串参数，因此抛出TypeError: write() argument must be str, not None异常。

问题的根本原因是parse_directory_tree方法在解析文件节点时，没有为文件节点提供默认的内容（如空字符串），而是直接设置为None，导致后续文件写入操作失败。

* 当前的 bug 异常堆栈信息
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


* 你的输出应该包括：
- 阐述你的最佳优化方案的思路
- 分步骤给出原始代码的修改方案，不要重复无需修改的无关代码，保持修改操作的信息精简
- 同步更新被修改的函数、或类的签名信息
- 不需要给出修改后的完整代码示例

* 代码分步修改指令格式示例：

**一，整体优化思路：**
<描述你的整体优化思路>
**二，分步修改指令:**
1. **第一步：** <关于某个方法、或类的操作描述>
	修改前：
	 ```python
	 	{需要修改的代码块}
	```
	修改后：
	 ```python
		{修改后的代码块}
	 ```
2. **第二步：** <关于某个方法、或类的操作描述>
... 依此类推

* 格式说明：
- 需要修改的代码块：指替换这部分代码即可以保证代码正确执行，不要展示其它不需要改动的代码，减少冗余
- 修改后的代码块：指进行修改替换后的代码
- 在修改后的代码块中增加**改动标记**，辅助用户分析差异
- 重要说明：不要在优化后的代码块中使用省略号等折叠、或隐藏代码；

请根据以上指令信息，给出 bug 解决方案，并严格按照指定格式输出
