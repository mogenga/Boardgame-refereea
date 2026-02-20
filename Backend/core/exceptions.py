"""
统一异常处理模块

职责：
- 定义业务异常类（替代到处写 HTTPException）
- 提供全局异常处理器（注册到 FastAPI）

为什么要统一异常处理？
1. 所有错误返回统一的 JSON 格式，前端只需一套解析逻辑
2. 业务层抛异常，不需要关心 HTTP 状态码
3. 兜底捕获未预期异常，避免返回原始堆栈信息给客户端
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger


class GameError(Exception):
    """
    业务异常基类

    所有业务异常继承这个类，
    全局异常处理器会统一捕获并格式化返回
    """

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class SessionNotFoundError(GameError):
    """会话不存在"""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"会话 '{session_id}' 不存在",
            status_code=404,
        )


class PlayerNotFoundError(GameError):
    """玩家不存在"""

    def __init__(self, player_name: str):
        super().__init__(
            message=f"玩家 '{player_name}' 不存在",
            status_code=404,
        )


class GameNotFoundError(GameError):
    """游戏规则不存在"""

    def __init__(self, game_name: str):
        super().__init__(
            message=f"游戏 '{game_name}' 的规则书尚未上传",
            status_code=404,
        )


class LLMError(GameError):
    """LLM 调用失败"""

    def __init__(self, detail: str = ""):
        message = "AI 裁定服务暂时不可用"
        if detail:
            message += f"（{detail}）"
        super().__init__(message=message, status_code=503)


def register_exception_handlers(app: FastAPI):
    """
    注册全局异常处理器

    在 main.py 中调用：
        register_exception_handlers(app)

    Args:
        app: FastAPI 应用实例
    """

    @app.exception_handler(GameError)
    async def game_error_handler(request: Request, exc: GameError):
        """
        处理所有业务异常

        返回统一格式：
        {"success": false, "error": "错误信息", "detail": ""}
        """
        logger.warning(f"业务异常: {exc.message} | path={request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.message,
                "detail": "",
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        处理 FastAPI 的 HTTPException

        包括参数校验失败（422）、路径不存在（404）等
        """
        logger.warning(f"HTTP异常: {exc.status_code} {exc.detail} | path={request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": str(exc.detail),
                "detail": "",
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """
        兜底：捕获所有未预期异常

        记录完整错误日志，但只返回通用错误信息给客户端
        （不暴露内部堆栈信息，避免安全风险）
        """
        logger.exception(f"未预期异常: {exc} | path={request.url.path}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "服务器内部错误",
                "detail": "请查看服务端日志获取详细信息",
            },
        )
