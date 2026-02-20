"""
LLM 调用层

职责：
1. 定义 Function Calling 工具 Schema（告诉 LLM 有哪些函数可调用）
2. 构建 Prompt（规则片段 + 游戏状态 + 对话历史 + 用户问题）
3. 调用 LLM 并处理 Function Calling 响应
4. 执行 Function，更新游戏状态
5. 返回裁定结果 + 规则出处 + 状态变更列表

Function Calling 流程：
    用户问题 → 构建Prompt → 调用LLM(带tools)
         → LLM返回tool_calls → 执行函数 → 结果反馈给LLM
         → LLM生成最终回答
"""

import json
from collections.abc import Generator

from openai import OpenAI
from loguru import logger

from config import settings
from models.game import GameState
from models.request import RuleReference, StateChange
from core import state as state_ops


# ============================================================
# 第一部分：工具定义（Function Calling Schema）
# ============================================================
#
# 这些 Schema 告诉 LLM："你有以下函数可以调用"
# LLM 会根据用户问题判断是否需要调用，以及传什么参数
#
# 格式遵循 OpenAI 的 tools 规范：
# {
#   "type": "function",
#   "function": {
#     "name": "函数名",
#     "description": "函数描述（LLM根据这个判断何时调用）",
#     "parameters": { JSON Schema 定义参数 }
#   }
# }

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_player_hp",
            "description": "更新玩家的血量。造成伤害时delta为负数，治疗回血时delta为正数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "目标玩家的名称",
                    },
                    "delta": {
                        "type": "integer",
                        "description": "血量变化量，负数为扣血，正数为回血",
                    },
                    "reason": {
                        "type": "string",
                        "description": "变更原因，例如'受到杀的伤害'",
                    },
                },
                "required": ["player_name", "delta", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_status_effect",
            "description": "给玩家施加一个状态效果，如中毒、眩晕、护盾等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "目标玩家的名称",
                    },
                    "effect": {
                        "type": "string",
                        "description": "效果名称，如'中毒'、'护盾'、'眩晕'",
                    },
                },
                "required": ["player_name", "effect"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_status_effect",
            "description": "移除玩家身上的一个状态效果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "目标玩家的名称",
                    },
                    "effect": {
                        "type": "string",
                        "description": "要移除的效果名称",
                    },
                },
                "required": ["player_name", "effect"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_player_resource",
            "description": "更新玩家的资源数量（金币、木材等）。增加时delta为正数，消耗时delta为负数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "目标玩家的名称",
                    },
                    "resource_name": {
                        "type": "string",
                        "description": "资源名称，如'金币'、'木材'",
                    },
                    "delta": {
                        "type": "integer",
                        "description": "资源变化量",
                    },
                    "reason": {
                        "type": "string",
                        "description": "变更原因",
                    },
                },
                "required": ["player_name", "resource_name", "delta", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "next_round",
            "description": "结束当前玩家的回合，切换到下一个玩家。仅在需要切换回合时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "next_player": {
                        "type": "string",
                        "description": "指定下一个行动的玩家名称，不指定则按顺序轮转",
                    },
                },
                "required": [],
            },
        },
    },
]


# ============================================================
# 第二部分：Prompt 构建
# ============================================================
#
# System Prompt 定义 AI 的角色和行为规则
# 这是 LLM 的"人设"，决定了它如何理解和回答问题

SYSTEM_PROMPT = """你是一个专业的桌游规则裁判助手。你的职责是：

1. 根据提供的规则原文，准确裁定玩家提出的规则问题
2. 每个裁定必须引用规则原文作为依据，不能凭空编造规则
3. 如果裁定涉及状态变更（扣血、施加效果等），你必须调用相应的函数来更新游戏状态
4. 如果规则书中没有相关规则，明确告知玩家"规则书中未找到相关条款"

回答格式要求：
- 先给出裁定结论
- 然后引用规则原文依据
- 如果有状态变更，说明变更内容

注意事项：
- 严格依据规则原文，不要添加规则书中没有的规则
- 如果规则有歧义，给出最合理的解释并说明理由
- 在调用函数时，确保参数与当前游戏状态中的玩家名称完全匹配
"""


def build_messages(
    question: str,
    rule_chunks: list[dict],
    game_state: GameState,
    chat_history: list[dict],
) -> list[dict]:
    """
    构建发送给 LLM 的完整消息列表

    消息结构：
    [
        {"role": "system", "content": "系统提示 + 规则片段 + 游戏状态"},
        {"role": "user", "content": "历史问题1"},
        {"role": "assistant", "content": "历史回答1"},
        ...
        {"role": "user", "content": "当前问题"},
    ]

    Args:
        question: 用户当前问题
        rule_chunks: RAG 检索到的规则片段
        game_state: 当前游戏状态
        chat_history: 对话历史

    Returns:
        消息列表
    """
    # 1. 构建系统消息（System Prompt + 动态上下文）
    # 将规则片段和游戏状态注入系统消息
    context_parts = [SYSTEM_PROMPT]

    # 注入检索到的规则片段
    if rule_chunks:
        context_parts.append("\n--- 以下是与问题相关的规则原文 ---")
        for i, chunk in enumerate(rule_chunks, 1):
            context_parts.append(f"\n[规则片段{i}]\n{chunk['content']}")
        context_parts.append("\n--- 规则原文结束 ---")
    else:
        context_parts.append("\n（未检索到相关规则片段，请根据你的知识谨慎回答，并提醒用户规则库中可能缺少相关内容）")

    # 注入当前游戏状态
    context_parts.append(f"\n--- 当前游戏状态 ---\n{game_state.get_state_summary()}\n--- 状态结束 ---")

    system_message = {"role": "system", "content": "\n".join(context_parts)}

    # 2. 构建消息列表
    messages = [system_message]

    # 添加对话历史（最近 N 条）
    for msg in chat_history:
        messages.append(msg)

    # 添加当前问题
    messages.append({"role": "user", "content": question})

    return messages


# ============================================================
# 第三部分：LLM 调用 + Function 执行循环
# ============================================================
#
# 核心流程：
# 1. 调用 LLM（带 tools 定义）
# 2. 如果 LLM 返回 tool_calls → 执行函数 → 结果反馈给 LLM → 再次调用
# 3. 如果 LLM 返回纯文本 → 结束，返回结果
# 4. 循环直到 LLM 不再调用 tool（最多循环 MAX_TOOL_ROUNDS 次防止死循环）

# 最大工具调用轮数，防止 LLM 无限循环调用
MAX_TOOL_ROUNDS = 5


def execute_tool_call(tool_name: str, arguments: dict, game_state: GameState) -> dict:
    """
    执行单个工具调用

    根据 tool_name 路由到对应的 core/state.py 函数

    Args:
        tool_name: 工具名称（与 TOOLS 中定义的 name 对应）
        arguments: LLM 传递的参数
        game_state: 当前游戏状态（会被直接修改）

    Returns:
        执行结果字典
    """
    # 函数路由表：工具名 → 实际函数
    if tool_name == "update_player_hp":
        return state_ops.update_player_hp(
            state=game_state,
            player_name=arguments["player_name"],
            delta=arguments["delta"],
            reason=arguments.get("reason", ""),
        )
    elif tool_name == "apply_status_effect":
        return state_ops.apply_status_effect(
            state=game_state,
            player_name=arguments["player_name"],
            effect=arguments["effect"],
        )
    elif tool_name == "remove_status_effect":
        return state_ops.remove_status_effect(
            state=game_state,
            player_name=arguments["player_name"],
            effect=arguments["effect"],
        )
    elif tool_name == "update_player_resource":
        return state_ops.update_player_resource(
            state=game_state,
            player_name=arguments["player_name"],
            resource_name=arguments["resource_name"],
            delta=arguments["delta"],
            reason=arguments.get("reason", ""),
        )
    elif tool_name == "next_round":
        return state_ops.next_round(
            state=game_state,
            next_player=arguments.get("next_player"),
        )
    else:
        return {"success": False, "message": f"未知工具: {tool_name}"}


def chat_with_llm(
    question: str,
    rule_chunks: list[dict],
    game_state: GameState,
    chat_history: list[dict],
) -> dict:
    """
    与 LLM 对话，支持 Function Calling

    这是核心函数，完成以下流程：
    1. 构建消息
    2. 调用 LLM
    3. 处理 tool_calls（如果有）
    4. 返回最终结果

    Args:
        question: 用户问题
        rule_chunks: RAG 检索到的规则片段
        game_state: 当前游戏状态
        chat_history: 对话历史

    Returns:
        {
            "answer": "AI的裁定回答",
            "state_changes": [StateChange, ...],
            "rule_references": [RuleReference, ...],
        }
    """
    # 初始化 OpenAI 客户端
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL or None,
    )

    # 构建初始消息
    messages = build_messages(question, rule_chunks, game_state, chat_history)

    # 记录所有状态变更
    state_changes: list[StateChange] = []

    # Function Calling 循环
    for round_num in range(MAX_TOOL_ROUNDS):
        logger.info(f"LLM 调用第 {round_num + 1} 轮")

        # 调用 LLM
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",  # LLM自动决定是否调用工具
        )

        # 获取 LLM 的回复
        assistant_message = response.choices[0].message

        # 将 assistant 的回复加入消息列表（保持上下文连续）
        messages.append(assistant_message.model_dump())

        # 检查是否有 tool_calls
        if not assistant_message.tool_calls:
            # 没有 tool_calls → LLM 已经给出最终回答
            logger.info("LLM 返回最终回答（无 tool_calls）")
            break

        # 有 tool_calls → 逐个执行
        logger.info(f"LLM 请求调用 {len(assistant_message.tool_calls)} 个工具")

        for tool_call in assistant_message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            logger.info(f"执行工具: {func_name}({func_args})")

            # 执行函数
            result = execute_tool_call(func_name, func_args, game_state)

            logger.info(f"工具执行结果: {result}")

            # 记录状态变更
            state_changes.append(StateChange(
                action=func_name,
                player=func_args.get("player_name"),
                details=func_args,
                reason=func_args.get("reason", ""),
            ))

            # 将工具执行结果反馈给 LLM
            # 这样 LLM 才知道函数执行的结果，据此生成最终回答
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    # 提取最终回答
    answer = assistant_message.content or "（AI 未生成回答文本）"

    # 构建规则引用
    rule_references = []
    for chunk in rule_chunks:
        rule_references.append(RuleReference(
            content=chunk["content"],
            score=chunk.get("score"),
        ))

    logger.info(f"问答完成: 回答长度={len(answer)}, 状态变更={len(state_changes)}个")

    return {
        "answer": answer,
        "state_changes": state_changes,
        "rule_references": rule_references,
    }


# ============================================================
# 第四部分：流式输出（SSE）
# ============================================================
#
# SSE（Server-Sent Events）让服务端逐字推送回答
# 用户体验：看到文字一个个蹦出来，而不是等几秒后一次性出现
#
# 流式 + Function Calling 的难点：
# - Function Calling 阶段不能流式输出（需要先执行完函数）
# - 只有最终回答阶段才流式输出文本
#
# 策略：
# 1. 先用非流式调用处理 Function Calling 循环
# 2. 最后一轮（生成最终回答）用流式调用

def chat_with_llm_stream(
    question: str,
    rule_chunks: list[dict],
    game_state: GameState,
    chat_history: list[dict],
) -> Generator[str, None, None]:
    """
    流式版本的 LLM 对话

    使用 Generator（生成器）逐步 yield 数据：
    - 先 yield 状态变更和规则引用（JSON 格式）
    - 最后 yield 逐字的回答文本

    SSE 数据格式：
        data: {"type": "state_change", "data": {...}}
        data: {"type": "rule_reference", "data": {...}}
        data: {"type": "answer_chunk", "content": "根据"}
        data: {"type": "answer_chunk", "content": "规则"}
        data: {"type": "done", "content": ""}

    Args:
        question: 用户问题
        rule_chunks: RAG 检索到的规则片段
        game_state: 当前游戏状态
        chat_history: 对话历史

    Yields:
        SSE 格式的字符串
    """
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL or None,
    )

    messages = build_messages(question, rule_chunks, game_state, chat_history)
    state_changes: list[StateChange] = []

    # ===== 阶段 1：处理 Function Calling（非流式） =====
    # Function Calling 必须非流式，因为需要完整解析 tool_calls 后执行
    for round_num in range(MAX_TOOL_ROUNDS):
        logger.info(f"[流式] FC阶段 第 {round_num + 1} 轮")

        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message
        messages.append(assistant_message.model_dump())

        if not assistant_message.tool_calls:
            # 没有 tool_calls 了，但这一轮是非流式的
            # 需要把这个回答直接作为结果
            # 先 yield 规则引用和状态变更，再 yield 完整回答
            break

        # 执行工具
        for tool_call in assistant_message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            logger.info(f"[流式] 执行工具: {func_name}({func_args})")
            result = execute_tool_call(func_name, func_args, game_state)

            change = StateChange(
                action=func_name,
                player=func_args.get("player_name"),
                details=func_args,
                reason=func_args.get("reason", ""),
            )
            state_changes.append(change)

            # yield 状态变更事件
            yield f"data: {json.dumps({'type': 'state_change', 'data': change.model_dump()}, ensure_ascii=False)}\n\n"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    # ===== 阶段 1.5：yield 规则引用 =====
    for chunk in rule_chunks:
        ref = RuleReference(content=chunk["content"], score=chunk.get("score"))
        yield f"data: {json.dumps({'type': 'rule_reference', 'data': ref.model_dump()}, ensure_ascii=False)}\n\n"

    # ===== 阶段 2：判断是否需要流式生成最终回答 =====
    if assistant_message.tool_calls:
        # 上一轮有 tool_calls，需要再调一次 LLM 获取最终回答（流式）
        logger.info("[流式] 进入流式生成最终回答")

        stream = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            tools=TOOLS,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield f"data: {json.dumps({'type': 'answer_chunk', 'content': delta.content}, ensure_ascii=False)}\n\n"
    else:
        # 没有 tool_calls，直接输出已有的回答
        answer = assistant_message.content or ""
        yield f"data: {json.dumps({'type': 'answer_chunk', 'content': answer}, ensure_ascii=False)}\n\n"

    # 结束标记
    yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
    logger.info("[流式] 流式输出完成")
