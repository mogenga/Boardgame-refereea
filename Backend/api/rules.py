"""
规则书管理 API

提供规则书的上传、删除、查询接口：
- POST   /api/rules/upload      上传规则书
- DELETE /api/rules/{game_name} 删除指定游戏的规则
- GET    /api/rules             查询已入库游戏列表
"""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from loguru import logger

from core.rag import get_rag_manager
from models.request import RuleUploadResponse, RuleDeleteResponse, GameListResponse

# 创建路由器
# prefix 和 tags 在 main.py 中注册时指定
router = APIRouter()

# 允许上传的文件类型
ALLOWED_EXTENSIONS = {".pdf", ".txt"}
# 最大文件大小：20MB
MAX_FILE_SIZE = 20 * 1024 * 1024


@router.post("/upload", response_model=RuleUploadResponse)
async def upload_rule(
    file: UploadFile = File(..., description="规则书文件（PDF或TXT）"),
    game_name: str = Form(..., description="游戏名称"),
):
    """
    上传规则书

    将规则书解析、切块、向量化后存入数据库。
    同一游戏重复上传会覆盖旧数据。

    Args:
        file: 上传的文件
        game_name: 游戏名称，用于标识和检索

    Returns:
        上传结果，包含入库的文档块数量
    """
    # ===== 1. 文件校验 =====

    # 检查文件名
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 检查文件扩展名
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}，仅支持 {ALLOWED_EXTENSIONS}"
        )

    # 检查文件大小
    # 先读取内容到内存检查大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大，最大支持 {MAX_FILE_SIZE // 1024 // 1024}MB"
        )

    # 检查游戏名称
    game_name = game_name.strip()
    if not game_name:
        raise HTTPException(status_code=400, detail="游戏名称不能为空")

    logger.info(f"收到规则书上传请求: file={file.filename}, game={game_name}, size={len(content)}")

    # ===== 2. 保存临时文件 =====
    # PyMuPDF 需要文件路径，不能直接处理内存数据
    # 所以先保存到临时文件，处理完再删除

    try:
        # 创建临时文件，保留原扩展名
        with tempfile.NamedTemporaryFile(
            suffix=file_ext,
            delete=False,  # 不自动删除，我们手动删除
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # ===== 3. 调用 RAG 模块处理 =====
        rag = get_rag_manager()

        # 如果同名游戏已存在，先删除旧数据
        existing_games = rag.list_games()
        if game_name in existing_games:
            logger.info(f"游戏 {game_name} 已存在，将覆盖旧数据")
            rag.delete_game(game_name)

        # 添加文档到向量库
        chunks_count = rag.add_document(tmp_path, game_name)

        logger.info(f"规则书上传成功: game={game_name}, chunks={chunks_count}")

        return RuleUploadResponse(
            success=True,
            game_name=game_name,
            message=f"规则书上传成功，已入库 {chunks_count} 个文档块",
            chunks_count=chunks_count,
        )

    except Exception as e:
        logger.error(f"规则书上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"规则书处理失败: {str(e)}")

    finally:
        # ===== 4. 清理临时文件 =====
        if "tmp_path" in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
            logger.debug(f"临时文件已删除: {tmp_path}")


@router.delete("/{game_name}", response_model=RuleDeleteResponse)
async def delete_rule(game_name: str):
    """
    删除指定游戏的规则数据

    Args:
        game_name: 游戏名称

    Returns:
        删除结果
    """
    game_name = game_name.strip()
    if not game_name:
        raise HTTPException(status_code=400, detail="游戏名称不能为空")

    logger.info(f"收到规则删除请求: game={game_name}")

    rag = get_rag_manager()

    # 检查游戏是否存在
    existing_games = rag.list_games()
    if game_name not in existing_games:
        raise HTTPException(status_code=404, detail=f"游戏 '{game_name}' 不存在")

    # 删除
    success = rag.delete_game(game_name)

    if success:
        logger.info(f"规则删除成功: game={game_name}")
        return RuleDeleteResponse(
            success=True,
            game_name=game_name,
            message=f"游戏 '{game_name}' 的规则数据已删除",
        )
    else:
        raise HTTPException(status_code=500, detail="删除失败，请查看日志")


@router.get("", response_model=GameListResponse)
async def list_rules():
    """
    查询已入库的游戏列表

    Returns:
        游戏名称列表和总数
    """
    rag = get_rag_manager()
    games = rag.list_games()

    logger.debug(f"查询游戏列表: {games}")

    return GameListResponse(
        games=games,
        total=len(games),
    )
