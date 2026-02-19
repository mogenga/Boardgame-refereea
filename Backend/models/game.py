"""
游戏数据模型

定义游戏状态的核心数据结构：
- PlayerState: 单个玩家的状态
- GameState: 整个游戏会话的状态

使用 Pydantic 模型的好处：
1. 自动数据校验（类型检查、范围检查）
2. 自动序列化（转JSON存Redis、返回API响应）
3. 自动生成 API 文档
"""

from datetime import datetime
from pydantic import BaseModel, Field


class PlayerState(BaseModel):
    """
    玩家状态模型

    记录单个玩家在游戏中的所有状态数据
    """

    # 玩家名称，唯一标识
    name: str

    # 当前血量
    # ge=0 表示 >= 0，不能为负数
    hp: int = Field(default=10, ge=0)

    # 最大血量，用于回血时的上限判断
    max_hp: int = Field(default=10, ge=1)

    # 魔力值（可选，不是所有游戏都有）
    # None 表示该游戏不使用魔力系统
    mp: int | None = None

    # 最大魔力值
    max_mp: int | None = None

    # 状态效果列表
    # 例如：["中毒", "护盾", "眩晕"]
    status_effects: list[str] = Field(default_factory=list)

    # 资源字典
    # 键是资源名称，值是数量
    # 例如：{"金币": 100, "木材": 50}
    resources: dict[str, int] = Field(default_factory=dict)


class GameState(BaseModel):
    """
    游戏会话状态模型

    记录一局游戏的完整状态，包括所有玩家和全局信息
    """

    # 会话唯一标识，用于区分不同的游戏局
    session_id: str

    # 游戏名称，对应规则书
    # 查询规则时用这个名称过滤向量数据库
    game_name: str

    # 当前回合数，从1开始
    round: int = Field(default=1, ge=1)

    # 当前行动玩家的名称
    # 空字符串表示还未开始或回合间隙
    current_player: str = ""

    # 游戏阶段
    # waiting: 等待开始
    # playing: 游戏进行中
    # ended: 游戏已结束
    phase: str = Field(default="waiting")

    # 所有玩家状态
    # 键是玩家名称，值是 PlayerState
    players: dict[str, PlayerState] = Field(default_factory=dict)

    # 全局效果列表
    # 影响所有玩家的效果，例如："全场禁魔"、"双倍伤害回合"
    global_effects: list[str] = Field(default_factory=list)

    # 操作历史日志
    # 记录每次状态变更，便于追溯和调试
    action_logs: list[str] = Field(default_factory=list)

    # 对话历史（用于多轮对话）
    # 存储最近的问答记录，格式：[{"role": "user", "content": "..."}, ...]
    chat_history: list[dict] = Field(default_factory=list)

    # 会话创建时间
    created_at: datetime = Field(default_factory=datetime.now)

    def add_log(self, message: str) -> None:
        """
        添加操作日志

        Args:
            message: 日志内容，例如 "玩家A 对 玩家B 造成3点伤害"
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.action_logs.append(f"[{timestamp}] {message}")

    def get_player(self, player_name: str) -> PlayerState | None:
        """
        获取指定玩家的状态

        Args:
            player_name: 玩家名称

        Returns:
            PlayerState 或 None（玩家不存在时）
        """
        return self.players.get(player_name)

    def get_state_summary(self) -> str:
        """
        生成当前状态的文本摘要

        用于注入到 LLM Prompt 中，让 AI 了解当前游戏状况
        """
        lines = [
            f"当前游戏: {self.game_name}",
            f"回合: {self.round}",
            f"阶段: {self.phase}",
            f"当前行动玩家: {self.current_player or '无'}",
            "",
            "玩家状态:",
        ]

        for name, player in self.players.items():
            effects = ", ".join(player.status_effects) if player.status_effects else "无"
            line = f"  - {name}: HP {player.hp}/{player.max_hp}"
            if player.mp is not None:
                line += f", MP {player.mp}/{player.max_mp}"
            line += f", 状态效果: {effects}"
            if player.resources:
                res = ", ".join(f"{k}:{v}" for k, v in player.resources.items())
                line += f", 资源: {res}"
            lines.append(line)

        if self.global_effects:
            lines.append("")
            lines.append(f"全局效果: {', '.join(self.global_effects)}")

        return "\n".join(lines)