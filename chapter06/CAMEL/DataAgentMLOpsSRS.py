from colorama import Fore
from camel.societies import RolePlaying
from camel.utils import print_text_animated

# 定义协作任务
task_prompt = """
## **DataAgent：基于MLOps全流程的功能需求规划**

### **总体设计原则**

- **流程驱动**：每个阶段输入明确，输出清晰，阶段之间无缝衔接。
- **智能决策**：在每个关键节点，Agent都能根据数据和任务上下文，智能选择并学习使用最佳工具。
- **闭环验证**：每个阶段都有子需求计划、任务清单、并根据任务执行结果，进行质量检查和单元测试，确保流程可继续。

------

### **分阶段功能需求详述**

#### **第一阶段：需求解析与规划**

- **目标**：将用户模糊的自然语言需求，转化为结构化的、可执行的技术任务清单。
- **核心能力**：**领域知识理解**：识别任务领域（如金融交易、销售预测），理解核心指标（如收益率、准确率）。**任务分解能力**：将宏观任务分解为标准流水线步骤（数据获取→ETL→分析→建模→评估→可视化→部署）。**约束条件识别**：识别用户隐含的约束，如时间成本、预算、精度要求、法律合规性。**初始技术规划**：基于任务复杂度，初步判断技术栈范围（如是否需要深度学习库）。

#### **第二阶段：数据获取与接入**

- **目标**：根据任务要求，从正确、可靠的来源获取原始数据。
- **核心能力**：**数据源智能推荐**：根据任务关键词（如“纳斯达克100指数”）自动推荐数据源（如Yahoo Finance、Quandl、聚宽、网络爬虫等），并对比可用性、成本和权限。**接口适配与调用**：自动检索所选数据源API文档，生成数据请求代码（处理认证、参数、频率等）。**多格式数据加载**：支持本地文件（CSV, Excel）、数据库（SQL, NoSQL）等多种数据接入方式，并自动选择对应的加载库（如`pandas`, `sqlalchemy`）。

#### **第三阶段：数据探索与清洗（ETL）**

- **目标**：理解数据现状，并进行清洗、转换，为分析和建模做准备。
- **核心能力**：**自动数据剖析**：自动生成数据概况报告（如使用`pandas-profiling`或`ydata-profiling`），识别缺失值、异常值、数据分布等。**数据质量问题诊断与修复建议**：根据剖析结果，智能推荐清洗策略（如均值填充、异常值剔除），并调用相应的数据处理库（如`pandas`, `numpy`）生成处理代码。**特征工程指导**：根据建模目标，推荐特征变换（如标准化、归一化）或特征创造（如移动平均线）方案，并调用`scikit-learn`等库实施。

#### **第四阶段：数据分析与可视化**

- **目标**：发现数据中的模式、趋势和关联关系，为建模方向提供依据。
- **核心能力**：**分析技术选择**：根据数据特点和业务问题，选择正确的分析方法（如相关性分析、趋势分析、聚类分析）。**可视化方案自动匹配**：自动匹配图表类型与分析目标（时序图、分布图、热力图），并选择最合适的可视化库（如`matplotlib`, `seaborn`, `plotly`）生成代码。**洞察摘要生成**：用自然语言描述关键发现，辅助用户理解。

#### **第五阶段：模型选择与训练**

- **目标**：选择并训练适合的机器学习模型来解决特定问题。
- **核心能力**：**模型推荐引擎**：将任务类型（分类、回归、聚类）和数据特征作为输入，从知识库中推荐候选模型（如线性回归、随机森林、LSTM），并说明推荐理由。**技术文档检索与学习**：自动获取推荐模型库（如`scikit-learn`, `statsmodels`, `PyTorch`）的最新API文档和最佳实践案例。**自动化训练代码生成**：根据文档生成包含数据加载、模型初始化、训练循环、模型保存的完整代码模板。**超参数调优引导**：推荐默认参数，并引导使用自动化调优工具（如`GridSearchCV`, `Optuna`）。

#### **第六阶段：模型评估与验证**

- **目标**：客观评估模型性能，确保其泛化能力。
- **核心能力**：**评估指标匹配**：根据任务类型自动选择评估指标（如分类用准确率/F1，回归用MSE/R²，金融用夏普比率/最大回撤）。**自动化评估代码生成**：生成模型在训练集、验证集和测试集上的评估代码。**验证方法选择**：自动采用正确的验证方法（如时间序列分割、k折交叉验证）。**结果对比与解释**：对比多个模型的性能，并生成易于理解的评估报告。

#### **第七阶段：系统实现与部署**

- **目标**：将训练好的模型和分析逻辑转化为可运行的应用程序。
- **核心能力**：**部署方案推荐**：根据用户需求（如一次性报告、实时API、定时任务），推荐部署框架（如`Flask`/`FastAPI/mlflow`创建Web服务，`Streamlit`/`Gradio`创建UI，`Airflow`调度任务）。**部署代码脚手架生成**：检索选定框架的文档，生成可部署的应用代码框架。**打包与配置辅助**：生成依赖文件（`requirements.txt`）和基础配置文件（如Dockerfile）。

#### **第八阶段：监控与维护**

- **目标**：确保系统长期稳定运行，并能适应数据变化。
- **核心能力**：**监控指标定义**：推荐监控指标（如模型预测精度下降、数据分布偏移）。**再训练触发机制设计**：建议再训练的条件（如性能阈值、时间周期）。**维护脚本生成**：生成数据更新、模型重新训练的维护脚本。

------

### **贯穿始终的横切面需求**

1. **知识管理**：一个持续更新的工具/框架/案例RAG知识库，为每个阶段的决策提供信息支持。
2. **代码执行与沙箱**：一个安全、隔离的环境，用于执行生成的代码，并捕获输出和错误。
3. **上下文传递**：每个阶段的输出（如处理后的数据、训练好的模型）和元数据（如数据模式、模型参数）必须能无缝传递给下一阶段。
4. **用户交互与确认**：在关键决策点（如选择昂贵的数据源、删除大量数据、部署模型）需要与用户确认。

这份需求规划将DataAgent定位为一个高度自主的、贯穿MLOps全生命周期的AI协作者，其核心价值在于将最佳实践和工具知识转化为具体的、可执行的解决方案。

任务：评审并优化以上需求说明书
要求：
1. 优化需求的架构，让系统的设计更健壮，符合MLOps全流程的任务需求；
2. 优化需求描述语言，加强可读性，消除二义性；
3. 输出优化后的需求说明书，使用 markdown 格式。
"""

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import ChatGPTConfig
from camel.agents import ChatAgent

import yaml
import re
from pathlib import Path
current_dir = Path(__file__).parent

# 读取配置文件
with open(current_dir.parent.parent.parent / 'config.yaml', 'r') as f:
    config = yaml.safe_load(f)

Provider = 'ModelScope'
model = ModelFactory.create(
    model_platform=ModelPlatformType.MODELSCOPE,
    model_type=config[Provider]['MODEL_NAME'],
    url=config[Provider]['BASE_URL'],
    api_key=config[Provider]['API_KEY'],
    model_config_dict=ChatGPTConfig(temperature=0.2, stream=True).as_dict(),
)

print(Fore.YELLOW + f"协作任务:\n{task_prompt}\n")


# 初始化角色扮演会话
role_play_session = RolePlaying(
    assistant_role_name="AI产品经理",
    user_role_name="数据分析师",
    task_prompt=task_prompt,
    model=model,
)

print(Fore.CYAN + f"具体任务描述:\n{role_play_session.task_prompt}\n")

# 开始协作对话
chat_turn_limit, n = 10, 0
input_msg = role_play_session.init_chat()

while n < chat_turn_limit:
    n += 1
    assistant_response, user_response = role_play_session.step(input_msg)

    print_text_animated(Fore.BLUE + f"数据分析师:\n\n{user_response.msg.content}\n")
    print_text_animated(Fore.GREEN + f"AI产品经理:\n\n{assistant_response.msg.content}\n")

    pattern = r"(?:<\s*CAMEL_TASK_DONE\s*>|\bCAMEL_TASK_DONE\b)"
    done_user = bool(re.search(pattern, user_response.msg.content))
    done_assistant = bool(re.search(pattern, assistant_response.msg.content))
    if done_user and done_assistant:
        print(Fore.MAGENTA + "✅ DataAgent 智能MLOps 需求说明书完成！")
        break

    input_msg = assistant_response.msg

print(Fore.YELLOW + f"总共进行了 {n} 轮协作对话")
