"""
配置管理模块
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置类
    """

    # ===== OpenAI 配置 =====
    # API密钥，必须在.env中设置，无默认值
    OPENAI_API_KEY: str

    # API基础地址，留空则使用官方地址
    # 如果你用代理或第三方服务，在这里填写
    OPENAI_BASE_URL: str = ""

    # 嵌入模型：将文本转为向量，用于相似度检索
    # text-embedding-3-small 性价比高，维度1536
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # 对话模型：生成裁定回答
    # gpt-4o 支持 Function Calling，效果最好
    LLM_MODEL: str = "gpt-4o"

    # ===== 向量数据库配置 =====
    # ChromaDB 持久化存储路径
    # 规则书向量化后存在这里，重启不丢失
    CHROMA_PATH: str = "./storage/vector_store"

    # ===== 文档处理配置 =====
    # chunk_size: 每个文本块的最大字符数
    # 太大：检索不精确，可能包含无关内容
    # 太小：上下文断裂，规则描述不完整
    # 500是经验值，适合规则书这种结构化文档
    CHUNK_SIZE: int = 500

    # chunk_overlap: 相邻块的重叠字符数
    # 作用：避免重要信息被切断在两个块的边界
    # 通常设为 chunk_size 的 10%-20%
    CHUNK_OVERLAP: int = 100

    # ===== RAG 检索配置 =====
    # 检索时返回最相关的 K 个文档块
    # 太少：可能漏掉关键规则
    # 太多：增加 token 消耗，可能引入噪音
    RETRIEVAL_TOP_K: int = 5

    # ===== 会话配置 =====
    # 对话历史保留条数（用于多轮对话）
    MAX_HISTORY_LENGTH: int = 10

    # 会话过期时间（秒），24小时
    SESSION_TTL: int = 86400

    # ===== Pydantic Settings 配置 =====
    model_config = SettingsConfigDict(
        # 指定 .env 文件路径
        env_file=".env",
        # .env 文件编码
        env_file_encoding="utf-8",
        # 忽略 .env 中存在但类中未定义的变量
        extra="ignore",
    )


# 创建全局配置实例
# 其他模块直接 `from config import settings` 即可使用
settings = Settings()


# ===== 派生路径配置 =====
# 使用 Path 对象处理路径，跨平台兼容
BASE_DIR = Path(__file__).parent
VECTOR_STORE_PATH = BASE_DIR / settings.CHROMA_PATH
