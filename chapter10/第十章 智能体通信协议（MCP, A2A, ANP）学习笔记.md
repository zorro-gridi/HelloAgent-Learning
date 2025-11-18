# 第十章 智能体通信协议（MCP, A2A, ANP）学习笔记

## 概述

当智能体需要与外部世界交互或多个智能体需要协作时，通信协议成为关键。本章介绍了三种核心协议，它们共同构成了智能体通信的基础设施层：

- **MCP (Model Context Protocol)**: 智能体与**工具/资源**之间的标准化通信。
- **A2A (Agent-to-Agent Protocol)**: 智能体之间的**点对点**协作。
- **ANP (Agent Network Protocol)**: 构建**大规模智能体网络**的服务发现与管理。

![image-20251118184246719](/Users/zorro/Documents/成长笔记/Agent开发/HelloAgent-Learning/chapter10/images/3_protocol_vs.png)

简单代码体验三种协议的基本功能

```python
from hello_agents.tools import MCPTool, A2ATool, ANPTool

# 1. MCP：访问工具
mcp_tool = MCPTool()
result = mcp_tool.run({
    "action": "call_tool",
    "tool_name": "add",
    "arguments": {"a": 10, "b": 20}
})
print(f"MCP计算结果: {result}")  # 输出: 30.0

# 2. ANP：服务发现
anp_tool = ANPTool()
anp_tool.run({
    "action": "register_service",
    "service_id": "calculator",
    "service_type": "math",
    "endpoint": "http://localhost:8080"
})
services = anp_tool.run({"action": "discover_services"})
print(f"发现的服务: {services}")

# 3. A2A：智能体通信
a2a_tool = A2ATool("http://localhost:5000")
print("A2A工具创建成功")

```

## 1. MCP (Model Context Protocol)

### 1.1 核心概念与设计理念

- **目标**: 解决智能体与外部工具/服务（如文件系统、数据库、API）集成时的代码重复、维护困难和互操作性差的问题。
- **比喻**: 智能体世界的 **“USB-C”接口**，为各种服务提供统一的访问标准。
- **架构**: 采用**客户端-服务器模式**（Host-Client-Server）。
- **核心能力**: 
  - **Tools（工具）**: 执行操作（如读取文件、查询数据库）。
  - **Resources（资源）**: 提供静态或动态数据（如文件内容、数据库记录）。
  - **Prompts（提示）**: 提供预定义的提示模板。

![image-20251118184645071](/Users/zorro/Documents/成长笔记/Agent开发/HelloAgent-Learning/chapter10/images/mcp_core_capabilities.png)

### 1.2 MCP 协议的工作流程

![image-20251118184907834](/Users/zorro/Documents/成长笔记/Agent开发/HelloAgent-Learning/chapter10/images/mcp_workflow.png)

### 1.3 MCP 对比 Function Calling 

![image-20251118185031816](/Users/zorro/Documents/成长笔记/Agent开发/HelloAgent-Learning/chapter10/images/mcp_vs_functioncall.png)

### 1.4 MCP 的传输方式

MCP 协议的一个重要特性是**传输层无关性**（Transport Agnostic）。这意味着 MCP 协议本身不依赖于特定的传输方式，可以在不同的通信通道上运行。HelloAgents 基于 FastMCP 2.0，提供了完整的传输方式支持，让你可以根据实际场景选择最合适的传输模式。

![image-20251118185239638](/Users/zorro/Documents/成长笔记/Agent开发/HelloAgent-Learning/chapter10/images/mcp_transport_method.png)

### 1.5 在 HelloAgents 中的使用

#### 快速体验

使用 `MCPTool`包装器可以轻松集成 MCP 服务器。

```python
from hello_agents.tools import MCPTool

# 1. 连接到内置演示服务器（内存传输，用于测试）
mcp_tool = MCPTool()
result = mcp_tool.run({"action": "call_tool", "tool_name": "add", "arguments": {"a": 10, "b": 20}})
print(f"MCP计算结果: {result}")  # 输出: 30.0

# 2. 连接到社区服务器（如文件系统，使用 Stdio 传输）
fs_tool = MCPTool(server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])
result = fs_tool.run({"action": "call_tool", "tool_name": "read_file", "arguments": {"path": "README.md"}})
print(result)
```

#### 在智能体中使用：自动展开机制

当将 `MCPTool`添加到智能体时，它会自动将 MCP 服务器提供的所有工具“展开”为智能体可直接调用的独立工具。

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool

llm = HelloAgentsLLM()
agent = SimpleAgent(name="助手", llm=llm)

# 添加 MCP 工具，智能体会自动获得其所有能力
github_tool = MCPTool(
    name="gh", # 工具名前缀
    server_command=["npx", "-y", "@modelcontextprotocol/server-github"]
)
agent.add_tool(github_tool) # 自动展开为 gh_search_repositories 等工具

# 智能体可直接使用这些工具
response = agent.run("搜索一下关于 AI Agent 的最新项目")
```

### 1.6 构建自定义 MCP 服务器

可以封装特定业务逻辑或私有服务。

```python
from hello_agents.protocols import MCPServer

# 1. 创建服务器实例
weather_server = MCPServer(name="weather-server")

# 2. 定义工具函数
def get_weather(city: str) -> str:
    # ... 调用天气API的逻辑 ...
    return json.dumps({"city": city, "temperature": 25, "condition": "晴朗"})

# 3. 注册工具到服务器
weather_server.add_tool(get_weather)

# 4. 运行服务器
if __name__ == "__main__":
    weather_server.run()
```

### 1.7 热门的 MCP 服务器概览

![image-20251118185417540](/Users/zorro/Documents/成长笔记/Agent开发/HelloAgent-Learning/chapter10/images/list_of_mcp_server.png)

## 2. A2A (Agent-to-Agent Protocol)

### 2.1 核心概念与设计理念

- **目标**: 解决多智能体协作中的中心化瓶颈问题，实现智能体间的直接对话和任务委托。
- **比喻**: 智能体之间的 **“对话”协议**，像人类团队一样协商协作。
- **架构**: 点对点（P2P）架构，每个智能体既是客户端也是服务器。
- **核心概念**:
  - **Task（任务）**: 需要执行的工作单元。
  - **Artifact（工件）**: 任务执行过程中产生或消耗的数据。

### A2A 中 Agent 协作过程的管理

![image-20251118190052631](/Users/zorro/Documents/成长笔记/Agent开发/HelloAgent-Learning/chapter10/images/a2a_task_livetime.png)

### 2.2 在 HelloAgents 中的使用（概念性实现）

由于 A2A 协议尚在早期，HelloAgents 提供了一个模拟实现的框架。

#### 创建 A2A 智能体服务

```python
from hello_agents.protocols.a2a.implementation import A2AServer

# 创建一个研究员智能体服务
researcher = A2AServer(name="researcher", description="负责搜索资料")

# 定义智能体提供的技能（Skill）
@researcher.skill("research")
def handle_research(query: str) -> str:
    # 模拟研究逻辑
    return f"关于'{query}'的研究结果：..."

# 在后台运行服务
researcher.run(port=5000)
```

#### 智能体间通信

```python
from hello_agents.protocols.a2a.implementation import A2AClient

# 创建客户端连接到研究员智能体
client = A2AClient("http://localhost:5000")

# 调用远程智能体的技能
response = client.execute_skill("research", "AI在教育领域的应用")
print(response.get('result'))
```

#### 使用 A2ATool 包装器

```python
from hello_agents.tools import A2ATool

# 将远程A2A智能体封装为工具，添加到本地智能体中
researcher_tool = A2ATool(agent_url="http://localhost:5000", name="researcher")
local_agent.add_tool(researcher_tool)
# 本地智能体可以像调用普通工具一样让远程智能体工作
```

## 3. ANP (Agent Network Protocol)

### 3.1 核心概念与设计理念

- **目标**: 解决在大规模、动态的智能体网络中，如何发现、连接和选择合适服务提供者的问题。
- **比喻**: 智能体的 **“互联网”** 或 **“服务网格”**。
- **架构**: 通常包含一个或多个**服务发现中心**。
- **核心概念**:
  - **服务注册**: 智能体向网络注册其提供的服务。
  - **服务发现**: 智能体查询网络以找到所需的服务。
  - **负载均衡**: 根据策略（如负载、延迟）选择最优服务实例。

### 3.2 在 HelloAgents 中的使用（概念性实现）

HelloAgents 提供了轻量级的 ANP 实现概念。

```python
from hello_agents.protocols import ANPDiscovery, register_service, discover_service

# 创建服务发现中心
discovery = ANPDiscovery()

# 注册服务（例如，多个计算节点）
register_service(
    discovery=discovery,
    service_id="compute_node_1",
    service_type="compute",
    endpoint="http://node1:8000",
    metadata={"load": 0.3, "cpu_cores": 8}
)

# 发现服务
services = discover_service(discovery, service_type="compute")
# 根据元数据（如负载）选择最佳服务
best_service = min(services, key=lambda s: s.metadata.get("load", 1.0))
```

## 4. 三种协议对比分析

| 特性维度     | MCP (Model Context Protocol)              | A2A (Agent-to-Agent)                 | ANP (Agent Network Protocol)                       |
| :----------- | :---------------------------------------- | :----------------------------------- | :------------------------------------------------- |
| **核心目标** | **工具访问标准化**                        | **智能体间协作**                     | **大规模服务发现与管理**                           |
| **通信关系** | 智能体 (Client) ↔ 工具/资源 (Server)      | 智能体 (Peer) ↔ 智能体 (Peer)        | 智能体 (Client) ↔ 网络注册中心/其他智能体 (Server) |
| **设计理念** | **上下文共享**，提供丰富上下文信息        | **对等通信**，支持对话与协商         | **去中心化服务发现**，构建可扩展网络               |
| **关键能力** | Tools, Resources, Prompts                 | Tasks, Artifacts, 任务生命周期       | 服务注册、发现、路由、负载均衡                     |
| **适用场景** | 增强单个智能体的能力（访问文件、DB、API） | **小规模、任务导向的智能体团队协作** | 大规模、开放、动态的智能体生态系统                 |
| **生态现状** | **相对成熟**，有官方和社区服务器          | **早期阶段**，标准和实现仍在发展     | **概念性为主**，社区探索中                         |
| **选择建议** | **你的智能体需要访问外部服务吗？**        | **你需要多个智能体相互协作吗？**     | **你要构建包含大量智能体的网络吗？**               |

## 5. 总结与建议

1. **优先使用 MCP**: 目前 MCP 生态最成熟，应优先使用社区提供的 MCP 服务器来扩展智能体功能，避免重复造轮子。
2. **理解协议边界**: MCP 管“工具”，A2A 管“协作”，ANP 管“网络”。它们并非互斥，而是可以组合使用。例如，一个智能体通过 ANP 发现另一个智能体（A2A 服务），并与之协作，而该智能体内部可能使用 MCP 来调用工具。
3. **关注发展**: A2A 和 ANP 协议和实现仍在快速演进中，本章提供的更多是概念和初步实践，需持续关注官方动态。
4. **实践路径**: 从构建和使用自定义 MCP 服务器开始，这是当前最实用、收益最高的技能。