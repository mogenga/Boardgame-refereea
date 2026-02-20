"""
会话管理模块

职责：
- 创建、读取、更新、删除游戏会话
- 将 GameState 存储在内存中

"""

import uuid
from datetime import datetime

from loguru import logger

from config import settings
from models.game import GameState, PlayerState
from models.request import PlayerInitInfo


class SessionManager:
    """
    会话管理器

    管理所有游戏会话的生命周期：创建 → 读取 → 更新 → 删除
    """

    def __init__(self):
        # 会话存储：session_id → GameState
        self._sessions: dict[str, GameState] = {}

    def create_session(self, game_name: str, players: list[PlayerInitInfo]) -> GameState:
        """
        创建新游戏会话

        Args:
            game_name: 游戏名称（必须是已上传规则书的游戏）
            players: 玩家初始化信息列表

        Returns:
            创建好的 GameState
        """
        # 1. 生成唯一会话ID
        # uuid4 生成随机ID，取前8位作为短ID，方便使用
        session_id = uuid.uuid4().hex[:8]

        # 2. 构建玩家状态字典
        players_dict = {}
        for p in players:
            players_dict[p.name] = PlayerState(
                name=p.name,
                hp=p.hp,
                max_hp=p.max_hp,
                mp=p.mp,
                max_mp=p.max_mp,
                resources=p.resources,
            )

        # 3. 创建游戏状态
        game_state = GameState(
            session_id=session_id,
            game_name=game_name,
            players=players_dict,
            # 第一个玩家作为初始行动玩家
            current_player=players[0].name if players else "",
            phase="playing",
        )

        # 4. 记录初始日志
        player_names = ", ".join(p.name for p in players)
        game_state.add_log(f"游戏会话创建: {game_name}, 玩家: {player_names}")

        # 5. 存储
        self._sessions[session_id] = game_state

        logger.info(f"会话创建成功: id={session_id}, game={game_name}, players={player_names}")
        return game_state

    def get_session(self, session_id: str) -> GameState | None:
        """
        获取会话状态

        Args:
            session_id: 会话ID

        Returns:
            GameState 或 None（会话不存在时）
        """
        return self._sessions.get(session_id)

    def update_session(self, session_id: str, game_state: GameState) -> bool:
        """
        更新会话状态

        每次状态变更后调用此方法保存

        Args:
            session_id: 会话ID
            game_state: 更新后的游戏状态

        Returns:
            是否更新成功
        """
        if session_id not in self._sessions:
            logger.warning(f"更新失败，会话不存在: {session_id}")
            return False

        self._sessions[session_id] = game_state
        return True

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话ID

        Returns:
            是否删除成功
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"会话已删除: {session_id}")
            return True

        logger.warning(f"删除失败，会话不存在: {session_id}")
        return False

    def reset_session(self, session_id: str) -> GameState | None:
        """
        重置会话到初始状态

        保留玩家列表和游戏名称，重置血量、回合等

        Args:
            session_id: 会话ID

        Returns:
            重置后的 GameState 或 None
        """
        state = self._sessions.get(session_id)
        if state is None:
            return None

        # 重置每个玩家的状态
        for player in state.players.values():
            player.hp = player.max_hp
            if player.mp is not None:
                player.mp = player.max_mp
            player.status_effects = []
            # 资源不重置，因为初始资源可能各不相同

        # 重置全局状态
        state.round = 1
        state.phase = "playing"
        state.global_effects = []
        state.chat_history = []

        # 重置当前玩家为第一个
        player_names = list(state.players.keys())
        state.current_player = player_names[0] if player_names else ""

        # 保留旧日志，添加重置记录
        state.add_log("游戏状态已重置")

        logger.info(f"会话已重置: {session_id}")
        return state

    def list_sessions(self) -> list[dict]:
        """
        列出所有活跃会话的摘要

        Returns:
            会话摘要列表
        """
        summaries = []
        for sid, state in self._sessions.items():
            summaries.append({
                "session_id": sid,
                "game_name": state.game_name,
                "phase": state.phase,
                "round": state.round,
                "player_count": len(state.players),
                "created_at": state.created_at.isoformat(),
            })
        return summaries


# ===== 全局单例 =====
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """
    获取会话管理器单例

    使用方式：
        from core.session import get_session_manager
        sm = get_session_manager()
        state = sm.create_session(...)
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
