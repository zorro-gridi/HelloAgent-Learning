import re
from dataclasses import dataclass
from typing import Dict, List

from autogen_core.models import CreateResult, UserMessage
from autogen_core import (
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TypeSubscription,
    default_subscription,
    message_handler,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_ext.models.openai import OpenAIChatCompletionClient

import yaml
from pathlib import Path
current_dir = Path(__file__).parent

# 读取配置文件
with open(current_dir.parent.parent.parent / 'config.yaml', 'r') as f:
    config = yaml.safe_load(f)



@dataclass
class DiscussionTopic:
    """讨论主题"""
    content: str

@dataclass
class FinalDecision:
    """最终决策"""
    content: str
    reasoning: str

@dataclass
class DiscussionRequest:
    """讨论请求"""
    content: str
    topic: str

@dataclass
class IntermediateOpinion:
    """中间意见交换"""
    content: str
    topic: str
    opinion: str
    round: int
    character: str  # 角色名称

@dataclass
class FinalOpinion:
    """最终意见"""
    opinion: str
    reasoning: str
    character: str


@default_subscription
class CharacterAgent(RoutedAgent):
    """角色代理基类"""

    def __init__(self, model_client: ChatCompletionClient, topic_type: str,
                 num_neighbors: int, max_round: int, character_name: str,
                 character_background: str) -> None:
        super().__init__(f"{character_name}的讨论代理")
        self._topic_type = topic_type
        self._model_client = model_client
        self._num_neighbors = num_neighbors
        self._character_name = character_name
        self._character_background = character_background
        self._history: List[LLMMessage] = []
        self._buffer: Dict[int, List[IntermediateOpinion]] = {}
        self._system_messages = [
            SystemMessage(
                content=(
                    f"你是三国时期的{character_name}。{character_background}\n"
                    "现在参与一个军事战略讨论，主题是：是否在博望坡使用火攻对抗曹军。\n"
                    "请基于你的性格、经历和军事见解发表意见。\n"
                    "每轮讨论中，你需要：\n"
                    "1. 分析当前局势和他人意见\n"
                    "2. 提出自己的观点和理由\n"
                    "3. 与其他角色进行建设性辩论\n"
                    "4. 最终给出明确建议\n"
                    "保持语言风格符合人物特点，发言简洁有力，发言稿不能超过 300 个字。"
                )
            )
        ]
        self._round = 1
        self._max_round = max_round

    @message_handler
    async def handle_request(self, message: DiscussionRequest, ctx: MessageContext) -> None:
        # 添加讨论主题到历史
        self._history.append(UserMessage(content=message.content, source="coordinator"))

        # 使用模型生成回应
        # response = await self._model_client.create(self._system_messages + self._history).content

        response = ''
        stream = self._model_client.create_stream(self._system_messages + self._history)
        async for chunk in stream:  # type: ignore
            if isinstance(chunk, str):
                # The chunk is a string.
                print(chunk, flush=True, end="")
                response += chunk
            else:
                # The final chunk is a CreateResult object.
                assert isinstance(chunk, CreateResult) and isinstance(chunk.content, str)
                # The last response is a CreateResult object with the complete message.
                # print("\n\n------------\n")
                print("The complete response:", flush=True)
                print(chunk.content, flush=True)
                response += chunk.content

        assert isinstance(response, str)

        self._history.append(AssistantMessage(content=response, source=self.metadata["type"]))

        print(f"{'='*60}\n{self._character_name} 第{self._round}轮发言:\n{response}")

        # 提取核心观点
        opinion = self._extract_opinion(response)

        self._round += 1

        if self._round == self._max_round:
            # 最终轮发布最终意见
            await self.publish_message(
                FinalOpinion(
                    opinion=opinion,
                    reasoning=response,
                    character=self._character_name
                ),
                topic_id=DefaultTopicId()
            )
        else:
            # 发布中间意见到专属话题
            await self.publish_message(
                IntermediateOpinion(
                    content=response,
                    topic=message.topic,
                    opinion=opinion,
                    round=self._round,
                    character=self._character_name
                ),
                topic_id=DefaultTopicId(type=self._topic_type),
            )

    @message_handler
    async def handle_opinion(self, message: IntermediateOpinion, ctx: MessageContext) -> None:
        # 缓存邻居的意见
        self._buffer.setdefault(message.round, []).append(message)

        # 检查是否收到所有邻居的意见
        if len(self._buffer[message.round]) == self._num_neighbors:
            print(f"{'='*60}\n{self._character_name} 第{message.round}轮: 收到{self._num_neighbors}位同僚意见")

            # 准备下一轮讨论提示
            prompt = f"以下是其他同僚在第{message.round}轮讨论中的意见：\n"
            for resp in self._buffer[message.round]:
                prompt += f"{resp.character}：{resp.content}\n"

            prompt += (
                f"\n基于以上讨论，请你作为{self._character_name}继续发表看法。\n"
                f"讨论主题：{message.topic}\n"
                "请分析各方观点，提出你的见解，并考虑战术可行性。"
            )

            # 继续讨论
            await self.send_message(
                DiscussionRequest(content=prompt, topic=message.topic),
                self.id
            )

            self._buffer.pop(message.round)

    def _extract_opinion(self, content: str) -> str:
        """从内容中提取核心观点"""
        # 简化实现，实际中可以更复杂的情感分析
        if "支持" in content or "赞成" in content or "可行" in content:
            return "支持火攻"
        elif "反对" in content or "不赞成" in content or "不可行" in content:
            return "反对火攻"
        else:
            return "谨慎考虑"


@default_subscription
class LiuBeiCoordinator(RoutedAgent):
    """刘备-协调者和决策者"""

    def __init__(self, num_characters: int) -> None:
        super().__init__("刘备-决策者")
        self._num_characters = num_characters
        self._buffer: List[FinalOpinion] = []

    @message_handler
    async def handle_topic(self, message: DiscussionTopic, ctx: MessageContext) -> None:
        print(f"{'='*60}\n刘备收到讨论主题:\n{message.content}")

        initial_prompt = (
            f"讨论主题：{message.content}\n\n"
            "作为蜀汉将领，请你就此战术发表看法。\n"
            "考虑因素包括：天时地利、兵力对比、战术风险、后续影响等。\n"
            "请基于历史经验和军事智慧提出建设性意见。\n"
        )

        print(f"{'='*60}\n刘备发起讨论请求")
        await self.publish_message(
            DiscussionRequest(content=initial_prompt, topic=message.content),
            topic_id=DefaultTopicId()
        )

    @message_handler
    async def handle_final_opinions(self, message: FinalOpinion, ctx: MessageContext) -> None:
        self._buffer.append(message)

        if len(self._buffer) == self._num_characters:
            print(f"{'='*60}\n刘备收到所有{self._num_characters}位将领的最终意见")

            # 汇总各方意见并做出决策
            decision = self._make_final_decision(self._buffer)

            # 发布最终决策
            await self.publish_message(
                FinalDecision(content=decision["verdict"], reasoning=decision["reasoning"]),
                topic_id=DefaultTopicId()
            )

            self._buffer.clear()
            print(f"{'='*60}\n刘备发布最终决策:\n{decision['reasoning']}")

    def _make_final_decision(self, opinions: List[FinalOpinion]) -> Dict:
        """基于各方意见做出最终决策"""
        # 分析意见分布
        support_count = len([o for o in opinions if "支持" in o.opinion])
        oppose_count = len([o for o in opinions if "反对" in o.opinion])

        reasoning = "经过与各位将军的深入讨论，我决定：\n\n"
        reasoning += "各方意见汇总：\n"
        for opinion in opinions:
            reasoning += f"- {opinion.character}: {opinion.opinion}\n"

        # 刘备的决策逻辑
        if support_count > oppose_count:
            reasoning += f"\n考虑到多数将军支持火攻，且诸葛亮军师也认为可行，我决定采用火攻之计。"
            reasoning += "但需谨慎安排，确保万无一失。"
            return {"verdict": "采用火攻", "reasoning": reasoning}
        else:
            reasoning += f"\n虽然火攻有其优势，但风险较大。我决定采取更稳妥的战术。"
            return {"verdict": "不采用火攻", "reasoning": reasoning}



async def main():
    # 初始化运行时
    runtime = SingleThreadedAgentRuntime()
    # model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

    Provider = 'ModelScope'
    model_client = OpenAIChatCompletionClient(
        model=config[Provider]['MODEL_NAME'],
        api_key=config[Provider]["API_KEY"],
        base_url=config[Provider]["BASE_URL"],
        model_info={
                "function_calling": False,
                "max_tokens": 4096,
                "context_length": 32768,
                "vision": False,
                "json_output": True,
                "family": "qwen",
                "structured_output": False,
            }
    )

    # 角色背景设定
    character_backgrounds = {
        "刘备": "你为人仁德，重视民心，善于纳谏，决策谨慎。既考虑战术效果，也关心士兵安危和民心向背。",
        "张飞": "你性格勇猛直率，善于突击，偏好主动进攻。重视战术的威猛效果，但有时略显急躁。",
        "关羽": "你武艺高强，重视义气，用兵稳重。善于把握战机，对战术的可行性有独到见解。",
        "赵云": "你胆大心细，善于突击和掩护，用兵灵活。注重战术的突然性和安全性。",
        "诸葛亮": "你深通谋略，熟知天文地理，用兵谨慎而善于奇谋。重视天时地利人和的配合。"
    }

    # 注册角色代理
    characters = {
        "刘备": 'LiuBei',
        "张飞": 'ZhangFei',
        "关羽": 'GuanYu',
        "赵云": 'ZhaoYun',
        "诸葛亮": 'ZhuGeliang',
        }

    for char in characters.keys():
        await CharacterAgent.register(
            runtime,
            f"Character{characters[char]}",
            lambda c=char: CharacterAgent(
                model_client=model_client,
                topic_type=f"Topic{char}",
                num_neighbors=2,  # 每个角色与2个其他角色交流
                max_round=5,     # 10 轮讨论
                character_name=characters[c],
                character_background=character_backgrounds[c]
            ),
        )

    # 注册刘备协调者
    await LiuBeiCoordinator.register(
        runtime,
        "LiuBeiCoordinator",
        lambda: LiuBeiCoordinator(num_characters=5)
    )

    # 设置讨论拓扑（圆桌式交流）
    topology = {
        "刘备": ["张飞", "诸葛亮"],    # 刘备与张飞、诸葛亮直接交流
        "张飞": ["刘备", "关羽"],      # 张飞与刘备、关羽直接交流
        "关羽": ["张飞", "赵云"],      # 关羽与张飞、赵云直接交流
        "赵云": ["关羽", "诸葛亮"],    # 赵云与关羽、诸葛亮直接交流
        "诸葛亮": ["赵云", "刘备"]     # 诸葛亮与赵云、刘备直接交流
    }

    for character, neighbors in topology.items():
        for neighbor in neighbors:
            await runtime.add_subscription(
                TypeSubscription(f"Topic{character}", f"Character{neighbor}")
            )

    # 讨论主题
    topic = (
        "战术讨论：曹操大军压境，我军计划在博望坡设伏。"
        "是否应该采用火攻战术？请考虑以下因素：\n"
        "1. 博望坡的地形特点（狭窄多草木）\n"
        "2. 当前季节和风向条件\n"
        "3. 曹军的兵力部署和行军习惯\n"
        "4. 火攻可能带来的后续影响\n"
        "5. 是否有更优的替代战术"
    )

    # 启动讨论
    runtime.start()
    await runtime.publish_message(DiscussionTopic(content=topic), DefaultTopicId())

    # 等待讨论结束
    await runtime.stop_when_idle()
    await model_client.close()



if __name__ == "__main__":
    import asyncio
    asyncio.run(main())