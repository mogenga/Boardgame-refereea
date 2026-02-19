"""
FastAPI 应用入口

职责：
1. 创建 FastAPI 应用实例
2. 注册所有路由
3. 配置中间件（CORS、日志等）
4. 定义启动/关闭事件
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# 导入路由模块
from api import rules


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    - yield 之前：启动时执行（初始化资源）
    - yield 之后：关闭时执行（清理资源）
    """
    # ===== 启动时 =====
    logger.info("=== 桌游裁判助手 API 启动 ===")

    # 预热 RAG 管理器（首次请求会更快）
    from core.rag import get_rag_manager
    try:
        rag = get_rag_manager()
        games = rag.list_games()
        logger.info(f"RAG 初始化完成，已入库游戏: {games if games else '无'}")
    except Exception as e:
        logger.warning(f"RAG 初始化失败（可能缺少 API Key）: {e}")

    yield  # 应用运行中

    # ===== 关闭时 =====
    logger.info("=== 桌游裁判助手 API 关闭 ===")


# 创建 FastAPI 应用
app = FastAPI(
    title="桌游裁判助手 API",
    description="基于 RAG 的桌游规则问答系统，支持游戏状态管理和 AI 裁定",
    version="0.1.0",
    lifespan=lifespan,
)

# ===== 配置 CORS =====
# 允许前端跨域调用（开发阶段允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 注册路由 =====
# prefix: URL前缀
# tags: OpenAPI文档中的分组标签

# 规则书管理: /api/rules/*
app.include_router(rules.router, prefix="/api/rules", tags=["规则书管理"])

# TODO Phase 2: 游戏会话管理
# app.include_router(sessions.router, prefix="/api/sessions", tags=["游戏会话"])

# TODO Phase 3: 规则问答
# app.include_router(query.router, prefix="/api/query", tags=["规则问答"])

# TODO Phase 2: 状态操作
# app.include_router(state.router, prefix="/api/state", tags=["状态操作"])


# ===== 根路径 =====
@app.get("/", tags=["系统"])
async def root():
    """
    API 根路径，返回基本信息
    """
    return {
        "name": "桌游裁判助手 API",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health", tags=["系统"])
async def health_check():
    """
    健康检查接口

    用于监控系统是否正常运行
    """
    return {"status": "healthy"}
