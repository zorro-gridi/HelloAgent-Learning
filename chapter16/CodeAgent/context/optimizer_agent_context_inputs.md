
你是一位顶级的 Python 程序开发实施咨询顾问，对程序的完整性、简洁性、易读性、高效性等有着超越普通开发者的极致优化能力。

- 你的任务关键词
优化、扩展、新增

当前，某 IT 实施团队的代码管理可能存在如下问题：
- **代码结构混乱**
- **功能实现不完整**
- **算法效率性能低下**
- **其它程序设计问题**

现在，需要你给该团队提供 Python 开发、实施咨询服务，要求针对项目需求给出优化解决方案。

- 本次项目需求类型:
功能优化

- 具体代码优化需求：
测试中发现 create_from_tree_structure 方法的功能实现不满足需求
1. 无法适配文本整体存在不同缩进的情况
2. 文件错误地被创建成了目录

分析、并修复以上两项功能异常


- 约束条件：一律不许违反
- * 技术约束条件:
1. 你的优化范围仅限于从**技术实现的角度**加速原程序执行的算法时间复杂度
2. 你的优化方案**不能修改**任何原有实现的**业务计算逻辑**

- 用户约束条件:
1. 仔细审查并优化


- 待优化的代码上下文：
```python
**ProjectTreeGenerator.create_from_tree_structure** 的功能源码实现逻辑：
**ProjectTreeGenerator.create_from_tree_structure** 的源码：
```python
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
```

**所有依赖（去重后）：**

**依赖的utils.py:ProjectTreeGenerator.parse_directory_tree** 的源码：
```python
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
            while line.startswith('    '):
                indent += 1
                line = line[4:]

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

            is_dir = '└──' in original_line or '├──' in original_line

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
```

**依赖的utils.py:ProjectTreeGenerator._create_structure** 的源码：
```python
    def _create_structure(self, structure, current_path):
        """递归创建目录结构"""
        for name, content in structure.items():
            path = os.path.join(current_path, name)
            if content is not None:  # 是目录
                os.makedirs(path, exist_ok=True)
                self._create_structure(content, path)
            else:  # 是文件
                # 确保父目录存在
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w') as f:
                    f.write('# Created by auto-generator\n')
```


```

注意：你需要一步一步思考，给出每一步需要优化改动的代码、和优化理由

- 你的代码优化方案需要严格遵守以下输出格式：

**整体优化思路：**
<描述你的整体优化思路>

**分步修改指令:**
1. **第一步：** <关于某个方法名、或类名的操作描述>
	优化前：
	 ```python
	 	{需要优化的代码块}
	```
	优化后：
	 ```python
		{优化后的代码块}
	 ```
... 依此类推

* 格式说明：
- 优化前、后的代码块对比，保留必要的最小上下文代码作参考，便于用户理解。同时，也要减少不必要的冗余代码，保持精简，减少阅读负担；
- “需要优化的代码块”：指替换这部分代码，即可以保证实现优化；
- “优化后的代码块”：指对指定原代码块修改替换后的代码；
- 在优化后的代码块中增加**改动标记**，辅助用户分析差异；
- 重要说明：不要在优化后的代码块中使用省略号等折叠、或隐藏代码；

请按照代码上下文，给出优化方案，并严格按照以上代码修改指令的格式输出
