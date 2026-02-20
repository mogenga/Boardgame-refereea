"""
游戏会话管理 API

提供游戏会话的创建、查询、重置、删除接口：
- POST   /api/sessions              创建新会话
- GET    /api/sessions/{session_id} 查询会话状态
- POST   /api/sessions/{session_id}/reset  重置会话
- DELETE /api/sessions/{session_id} 删除会话
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from core.session import get_session_manager
from core.rag import get_rag_manager
from models.request import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionStateResponse,
)

router = APIRouter()


@router.post("", response_model=SessionCreateResponse)
async def create_session(request: SessionCreateRequest):
    """
    创建新游戏会话

    会自动校验游戏名称是否已上传规则书

    请求示例：
    {
        "game_name": "三国杀",
        "players": [
            {"name": "玩家A", "hp": 4, "max_hp": 4},
            {"name": "玩家B", "hp": 3, "max_hp": 3}
        ]
    }
    """
    # 1. 校验游戏是否已上传规则书
    rag = get_rag_manager()
    existing_games = rag.list_games()
    if request.game_name not in existing_games:
        raise HTTPException(
            status_code=400,
            detail=f"游戏 '{request.game_name}' 尚未上传规则书，请先上传。已有游戏: {existing_games}"
        )

    # 2. 校验玩家名称不能重复
    names = [p.name for p in request.players]
    if len(names) != len(set(names)):
        raise HTTPException(status_code=400, detail="玩家名称不能重复")

    # 3. 创建会话
    sm = get_session_manager()
    state = sm.create_session(request.game_name, request.players)

    return SessionCreateResponse(
        success=True,
        session_id=state.session_id,
        message=f"会话创建成功，游戏: {request.game_name}，玩家: {', '.join(names)}",
    )


@router.get("/{session_id}", response_model=SessionStateResponse)
async def get_session(session_id: str):
    """
    查询会话完整状态

    返回当前回合、所有玩家状态、全局效果等
    """
    sm = get_session_manager()
    state = sm.get_session(session_id)

    if state is None:
        raise HTTPException(status_code=404, detail=f"会话 '{session_id}' 不存在")

    return SessionStateResponse(success=True, state=state)


@router.post("/{session_id}/reset", response_model=SessionStateResponse)
async def reset_session(session_id: str):
    """
    重置游戏状态

    保留玩家列表和游戏名称，血量回满、效果清空、回合归1
    """
    sm = get_session_manager()
    state = sm.reset_session(session_id)

    if state is None:
        raise HTTPException(status_code=404, detail=f"会话 '{session_id}' 不存在")

    logger.info(f"会话已重置: {session_id}")

    return SessionStateResponse(
        success=True,
        state=state,
        message="游戏状态已重置",
    )


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    结束并删除会话
    """
    sm = get_session_manager()
    success = sm.delete_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"会话 '{session_id}' 不存在")

    return {"success": True, "message": f"会话 '{session_id}' 已删除"}
