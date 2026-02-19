"""
API 请求与响应模型

定义所有 API 接口的输入输出格式：
- 请求体 (Request): 客户端发送的数据
- 响应体 (Response): 服务端返回的数据

命名规范：
- XxxRequest: 请求体
- XxxResponse: 响应体
"""

from pydantic import BaseModel, Field
from models.game import PlayerState, GameState


# ==================== 规则书管理 ====================

class RuleUploadResponse(BaseModel):
    """规则书上传响应"""
    success: bool
    game_name: str
    message: str
    # 入库的文档块数量，便于调试
    chunks_count: int = 0


class RuleDeleteResponse(BaseModel):
    """规则书删除响应"""
    success: bool
    game_name: str
    message: str


class GameListResponse(BaseModel):
    """已入库游戏列表响应"""
    games: list[str]
    total: int


# ==================== 游戏会话管理 ====================

class PlayerInitInfo(BaseModel):
    """
    创建会话时的玩家初始化信息

    客户端可以指定每个玩家的初始状态，
    不指定的字段使用默认值
    """
    name: str
    hp: int = 10
    max_hp: int = 10
    mp: int | None = None
    max_mp: int | None = None
    resources: dict[str, int] = Field(default_factory=dict)


class SessionCreateRequest(BaseModel):
    """
    创建游戏会话请求

    示例：
    {
        "game_name": "三国杀",
        "players": [
            {"name": "玩家A", "hp": 4, "max_hp": 4},
            {"name": "玩家B", "hp": 3, "max_hp": 3}
        ]
    }
    """
    # 游戏名称，必须是已上传规则书的游戏
    game_name: str

    # 玩家列表，至少1人
    players: list[PlayerInitInfo] = Field(min_length=1)


class SessionCreateResponse(BaseModel):
    """创建会话响应"""
    success: bool
    session_id: str
    message: str


class SessionStateResponse(BaseModel):
    """
    查询会话状态响应

    直接返回完整的 GameState
    """
    success: bool
    state: GameState | None = None
    message: str = ""


# ==================== 规则问答 ====================

class QueryRequest(BaseModel):
    """
    规则问答请求

    示例：
    {
        "session_id": "abc123",
        "question": "玩家A对玩家B使用杀，玩家B没有闪，会发生什么？"
    }
    """
    # 会话ID，用于获取当前游戏状态和对话历史
    session_id: str

    # 用户问题
    question: str = Field(min_length=1)

    # 是否流式返回（Phase 4 实现）
    stream: bool = False


class RuleReference(BaseModel):
    """
    规则出处引用

    记录 AI 回答时引用了哪些规则原文
    """
    # 原文内容（可能是截断的片段）
    content: str

    # 来源页码（如果PDF有页码信息）
    page: int | None = None

    # 相似度分数，越高越相关
    score: float | None = None


class StateChange(BaseModel):
    """
    状态变更记录

    记录 AI 通过 Function Calling 做了什么操作
    """
    # 操作类型
    # update_hp: 更新血量
    # apply_effect: 施加状态效果
    # remove_effect: 移除状态效果
    # update_resource: 更新资源
    # next_round: 切换回合
    action: str

    # 目标玩家（如果是玩家相关操作）
    player: str | None = None

    # 变更详情（根据 action 类型不同而不同）
    details: dict = Field(default_factory=dict)

    # 变更原因
    reason: str = ""


class QueryResponse(BaseModel):
    """
    规则问答响应

    示例：
    {
        "success": true,
        "answer": "根据规则，杀造成1点伤害...",
        "rule_references": [...],
        "state_changes": [...]
    }
    """
    success: bool

    # AI 生成的裁定回答
    answer: str = ""

    # 引用的规则原文
    rule_references: list[RuleReference] = Field(default_factory=list)

    # 本次回答触发的状态变更
    state_changes: list[StateChange] = Field(default_factory=list)

    # 错误信息（如果 success=False）
    error: str = ""


# ==================== 状态手动操作 ====================

class UpdateHpRequest(BaseModel):
    """
    更新玩家血量请求

    delta 为正数表示回血，负数表示扣血
    """
    delta: int
    reason: str = "手动调整"


class UpdateEffectRequest(BaseModel):
    """
    更新玩家状态效果请求
    """
    # add: 添加效果, remove: 移除效果
    action: str = Field(pattern="^(add|remove)$")
    effect: str


class UpdateResourceRequest(BaseModel):
    """
    更新玩家资源请求
    """
    resource_name: str
    delta: int
    reason: str = "手动调整"


class StateOperationResponse(BaseModel):
    """状态操作通用响应"""
    success: bool
    message: str
    # 返回操作后的玩家状态
    player_state: PlayerState | None = None


class NextRoundRequest(BaseModel):
    """
    切换回合请求
    """
    # 下一个行动玩家，不指定则按顺序轮转
    next_player: str | None = None


class NextRoundResponse(BaseModel):
    """切换回合响应"""
    success: bool
    message: str
    current_round: int = 0
    current_player: str = ""


# ==================== 通用响应 ====================

class ErrorResponse(BaseModel):
    """
    错误响应

    所有接口在出错时返回统一格式
    """
    success: bool = False
    error: str
    detail: str = ""
