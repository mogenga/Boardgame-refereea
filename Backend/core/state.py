"""
游戏状态操作模块

职责：
- 封装所有状态修改操作（扣血、加效果、切换回合等）
- 每个操作自带合法性校验和日志记录
- 被两个地方调用：
  1. API 层：玩家手动操作（api/state.py）
  2. LLM 层：AI 通过 Function Calling 自动操作（Phase 3）

为什么要单独封装？
- 手动操作和 AI 操作共用同一套逻辑，保证行为一致
- 状态校验集中管理，不会遗漏
"""

from loguru import logger

from models.game import GameState


def update_player_hp(state: GameState, player_name: str, delta: int, reason: str = "") -> dict:
    """
    更新玩家血量

    Args:
        state: 当前游戏状态
        player_name: 目标玩家
        delta: 血量变化量（正数回血，负数扣血）
        reason: 变更原因

    Returns:
        操作结果 {"success": bool, "message": str, "old_hp": int, "new_hp": int}
    """
    player = state.get_player(player_name)
    if player is None:
        return {"success": False, "message": f"玩家 '{player_name}' 不存在"}

    old_hp = player.hp
    # 计算新血量，限制在 [0, max_hp] 范围内
    player.hp = max(0, min(player.hp + delta, player.max_hp))
    new_hp = player.hp

    # 构建日志
    if delta > 0:
        action_text = f"{player_name} 回复 {delta} 点生命值"
    elif delta < 0:
        action_text = f"{player_name} 受到 {abs(delta)} 点伤害"
    else:
        action_text = f"{player_name} 血量未变化"

    log_msg = f"{action_text} ({old_hp} → {new_hp})"
    if reason:
        log_msg += f"，原因: {reason}"

    state.add_log(log_msg)
    logger.info(f"[状态变更] {log_msg}")

    return {
        "success": True,
        "message": log_msg,
        "old_hp": old_hp,
        "new_hp": new_hp,
    }


def apply_status_effect(state: GameState, player_name: str, effect: str) -> dict:
    """
    施加状态效果

    Args:
        state: 当前游戏状态
        player_name: 目标玩家
        effect: 效果名称（如 "中毒"、"护盾"）

    Returns:
        操作结果
    """
    player = state.get_player(player_name)
    if player is None:
        return {"success": False, "message": f"玩家 '{player_name}' 不存在"}

    if effect in player.status_effects:
        return {"success": False, "message": f"{player_name} 已有 '{effect}' 效果，无法重复施加"}

    player.status_effects.append(effect)

    log_msg = f"{player_name} 获得状态效果: {effect}"
    state.add_log(log_msg)
    logger.info(f"[状态变更] {log_msg}")

    return {"success": True, "message": log_msg}


def remove_status_effect(state: GameState, player_name: str, effect: str) -> dict:
    """
    移除状态效果

    Args:
        state: 当前游戏状态
        player_name: 目标玩家
        effect: 效果名称

    Returns:
        操作结果
    """
    player = state.get_player(player_name)
    if player is None:
        return {"success": False, "message": f"玩家 '{player_name}' 不存在"}

    if effect not in player.status_effects:
        return {"success": False, "message": f"{player_name} 没有 '{effect}' 效果"}

    player.status_effects.remove(effect)

    log_msg = f"{player_name} 移除状态效果: {effect}"
    state.add_log(log_msg)
    logger.info(f"[状态变更] {log_msg}")

    return {"success": True, "message": log_msg}


def update_player_resource(state: GameState, player_name: str,
                           resource_name: str, delta: int, reason: str = "") -> dict:
    """
    更新玩家资源

    Args:
        state: 当前游戏状态
        player_name: 目标玩家
        resource_name: 资源名称（如 "金币"、"木材"）
        delta: 变化量（正数增加，负数减少）
        reason: 变更原因

    Returns:
        操作结果
    """
    player = state.get_player(player_name)
    if player is None:
        return {"success": False, "message": f"玩家 '{player_name}' 不存在"}

    old_value = player.resources.get(resource_name, 0)
    new_value = old_value + delta

    # 资源不能为负
    if new_value < 0:
        return {
            "success": False,
            "message": f"{player_name} 的 {resource_name} 不足: 当前 {old_value}，需要 {abs(delta)}"
        }

    player.resources[resource_name] = new_value

    log_msg = f"{player_name} {resource_name}: {old_value} → {new_value} ({'+'if delta > 0 else ''}{delta})"
    if reason:
        log_msg += f"，原因: {reason}"

    state.add_log(log_msg)
    logger.info(f"[状态变更] {log_msg}")

    return {
        "success": True,
        "message": log_msg,
        "old_value": old_value,
        "new_value": new_value,
    }


def next_round(state: GameState, next_player: str | None = None) -> dict:
    """
    切换到下一回合

    Args:
        state: 当前游戏状态
        next_player: 指定下一个行动玩家，None则按顺序轮转

    Returns:
        操作结果
    """
    if state.phase != "playing":
        return {"success": False, "message": f"当前游戏阶段为 '{state.phase}'，无法切换回合"}

    player_names = list(state.players.keys())
    if not player_names:
        return {"success": False, "message": "没有玩家"}

    old_round = state.round
    old_player = state.current_player

    if next_player:
        # 指定下一个玩家
        if next_player not in state.players:
            return {"success": False, "message": f"玩家 '{next_player}' 不存在"}
        state.current_player = next_player
    else:
        # 按顺序轮转
        # 找到当前玩家的索引，移动到下一个
        if old_player in player_names:
            current_idx = player_names.index(old_player)
            next_idx = (current_idx + 1) % len(player_names)
        else:
            next_idx = 0
        state.current_player = player_names[next_idx]

    # 当轮转回第一个玩家时，回合数+1
    if player_names.index(state.current_player) == 0 and old_player != "":
        state.round += 1

    log_msg = f"回合切换: {old_player} → {state.current_player}"
    if state.round != old_round:
        log_msg += f" (进入第{state.round}回合)"

    state.add_log(log_msg)
    logger.info(f"[状态变更] {log_msg}")

    return {
        "success": True,
        "message": log_msg,
        "current_round": state.round,
        "current_player": state.current_player,
    }
