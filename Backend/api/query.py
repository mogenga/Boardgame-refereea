"""
规则问答 API

提供两种问答模式：
- POST /api/query          普通问答（一次性返回完整结果）
- POST /api/query/stream   流式问答（SSE 逐字推送）

完整流程：
1. 接收用户问题和 session_id
2. 从 SessionManager 读取游戏状态
3. 从 RAG 检索相关规则片段
4. 调用 LLM 生成裁定（带 Function Calling）
5. 保存对话历史
6. 返回裁定结果 + 规则出处 + 状态变更
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

from config import settings
from core.rag import get_rag_manager
from core.session import get_session_manager
from core.llm import chat_with_llm, chat_with_llm_stream
from models.request import QueryRequest, QueryResponse

router = APIRouter()


def _prepare_query(request: QueryRequest):
    """
    问答请求的公共准备逻辑

    校验会话 + RAG 检索，供普通和流式接口复用

    Returns:
        (game_state, rule_chunks)
    """
    # 获取游戏会话
    sm = get_session_manager()
    state = sm.get_session(request.session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"会话 '{request.session_id}' 不存在")

    # RAG 检索相关规则
    rag = get_rag_manager()
    rule_chunks = rag.search(
        query=request.question,
        game_name=state.game_name,
    )
    logger.info(f"RAG 检索到 {len(rule_chunks)} 个规则片段")

    return state, rule_chunks


@router.post("", response_model=QueryResponse)
async def query_rule(request: QueryRequest):
    """
    普通规则问答（一次性返回）

    请求示例：
    {
        "session_id": "a3f2b1c9",
        "question": "玩家A对玩家B使用杀，造成3点伤害，护盾如何生效？"
    }
    """
    logger.info(f"收到规则问答: session={request.session_id}, question={request.question}")

    state, rule_chunks = _prepare_query(request)

    # 调用 LLM 裁定
    try:
        result = chat_with_llm(
            question=request.question,
            rule_chunks=rule_chunks,
            game_state=state,
            chat_history=state.chat_history,
        )
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        return QueryResponse(
            success=False,
            error=f"AI 裁定失败: {str(e)}",
        )

    # 保存对话历史
    state.chat_history.append({"role": "user", "content": request.question})
    state.chat_history.append({"role": "assistant", "content": result["answer"]})

    max_len = settings.MAX_HISTORY_LENGTH * 2
    if len(state.chat_history) > max_len:
        state.chat_history = state.chat_history[-max_len:]

    # 保存更新后的状态
    sm = get_session_manager()
    sm.update_session(request.session_id, state)

    logger.info(f"问答完成: answer_len={len(result['answer'])}, changes={len(result['state_changes'])}")

    return QueryResponse(
        success=True,
        answer=result["answer"],
        rule_references=result["rule_references"],
        state_changes=result["state_changes"],
    )


@router.post("/stream")
async def query_rule_stream(request: QueryRequest):
    """
    流式规则问答（SSE 推送）

    返回 text/event-stream 格式，逐步推送数据：

    事件类型：
    - state_change:   状态变更（扣血等），在回答之前推送
    - rule_reference: 规则引用片段
    - answer_chunk:   回答文本片段（逐字推送）
    - done:           结束标记

    客户端使用 EventSource 接收：
        const es = new EventSource('/api/query/stream');
        es.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'answer_chunk') {
                // 追加文字到页面
            }
        };

    请求示例（与普通接口一致）：
    {
        "session_id": "a3f2b1c9",
        "question": "玩家A对玩家B使用杀"
    }
    """
    logger.info(f"收到流式问答: session={request.session_id}, question={request.question}")

    state, rule_chunks = _prepare_query(request)

    def event_generator():
        """
        SSE 事件生成器

        包裹 chat_with_llm_stream，确保异常也能通过 SSE 返回
        """
        try:
            yield from chat_with_llm_stream(
                question=request.question,
                rule_chunks=rule_chunks,
                game_state=state,
                chat_history=state.chat_history,
            )
        except Exception as e:
            logger.error(f"流式 LLM 调用失败: {e}")
            import json
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    # StreamingResponse 让 FastAPI 逐步发送数据，而不是等全部生成完
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # 禁止缓存，确保实时推送
            "Cache-Control": "no-cache",
            # 保持连接
            "Connection": "keep-alive",
        },
    )
