"""
游戏状态手动操作 API

提供玩家手动修改游戏状态的接口（不经过 AI 裁定）：
- PATCH  /api/sessions/{sid}/players/{name}/hp       更新血量
- PATCH  /api/sessions/{sid}/players/{name}/effects  更新状态效果
- PATCH  /api/sessions/{sid}/players/{name}/resources 更新资源
- POST   /api/sessions/{sid}/next-round              切换回合
- GET    /api/sessions/{sid}/logs                    查看操作日志
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from core.session import get_session_manager
from core import state as state_ops
from models.request import (
    UpdateHpRequest,
    UpdateEffectRequest,
    UpdateResourceRequest,
    StateOperationResponse,
    NextRoundRequest,
    NextRoundResponse,
)

router = APIRouter()


def _get_state(session_id: str):
    """
    获取会话状态的辅助函数

    不存在则抛出 404
    """
    sm = get_session_manager()
    state = sm.get_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"会话 '{session_id}' 不存在")
    return state


@router.patch(
    "/{session_id}/players/{player_name}/hp",
    response_model=StateOperationResponse,
)
async def update_hp(session_id: str, player_name: str, request: UpdateHpRequest):
    """
    更新玩家血量

    delta 为正数表示回血，负数表示扣血

    请求示例：
    {"delta": -3, "reason": "受到火球术伤害"}
    """
    state = _get_state(session_id)

    result = state_ops.update_player_hp(state, player_name, request.delta, request.reason)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return StateOperationResponse(
        success=True,
        message=result["message"],
        player_state=state.get_player(player_name),
    )


@router.patch(
    "/{session_id}/players/{player_name}/effects",
    response_model=StateOperationResponse,
)
async def update_effects(session_id: str, player_name: str, request: UpdateEffectRequest):
    """
    施加或移除状态效果

    请求示例：
    {"action": "add", "effect": "中毒"}
    {"action": "remove", "effect": "中毒"}
    """
    state = _get_state(session_id)

    if request.action == "add":
        result = state_ops.apply_status_effect(state, player_name, request.effect)
    else:
        result = state_ops.remove_status_effect(state, player_name, request.effect)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return StateOperationResponse(
        success=True,
        message=result["message"],
        player_state=state.get_player(player_name),
    )


@router.patch(
    "/{session_id}/players/{player_name}/resources",
    response_model=StateOperationResponse,
)
async def update_resources(
    session_id: str, player_name: str, request: UpdateResourceRequest
):
    """
    更新玩家资源

    请求示例：
    {"resource_name": "金币", "delta": -50, "reason": "购买装备"}
    """
    state = _get_state(session_id)

    result = state_ops.update_player_resource(
        state, player_name, request.resource_name, request.delta, request.reason
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return StateOperationResponse(
        success=True,
        message=result["message"],
        player_state=state.get_player(player_name),
    )


@router.post(
    "/{session_id}/next-round",
    response_model=NextRoundResponse,
)
async def advance_round(session_id: str, request: NextRoundRequest):
    """
    切换到下一回合

    不指定 next_player 则按顺序轮转

    请求示例：
    {}
    {"next_player": "玩家B"}
    """
    state = _get_state(session_id)

    result = state_ops.next_round(state, request.next_player)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return NextRoundResponse(
        success=True,
        message=result["message"],
        current_round=result["current_round"],
        current_player=result["current_player"],
    )


@router.get("/{session_id}/logs")
async def get_logs(session_id: str):
    """
    查看操作日志

    返回该会话的所有操作历史记录
    """
    state = _get_state(session_id)

    return {
        "success": True,
        "session_id": session_id,
        "logs": state.action_logs,
        "total": len(state.action_logs),
    }
