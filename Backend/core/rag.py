"""
RAG 核心模块

RAG = Retrieval Augmented Generation（检索增强生成）

工作流程：
1. 文档入库：PDF → 文本 → 切块 → 向量化 → 存入ChromaDB
2. 检索：问题 → 向量化 → 在ChromaDB中找相似块 → 返回Top-K

本模块职责：
- 解析 PDF/TXT 文件
- 文本切块（chunking）
- 向量化并存入 ChromaDB
- 相似度检索
"""

import os
from pathlib import Path

import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from loguru import logger

from config import settings, VECTOR_STORE_PATH


class RAGManager:
    """
    RAG 管理器

    单例模式使用，整个应用共享一个实例
    """

    def __init__(self):
        """
        初始化 RAG 管理器

        1. 创建 Embedding 模型（文本转向量）
        2. 创建文本切分器
        3. 连接 ChromaDB
        """
        # ===== 1. 初始化 Embedding 模型 =====
        # Embedding 模型将文本转为向量（一串数字）
        # 语义相近的文本，向量也相近
        self.embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL or None,
        )

        # ===== 2. 初始化文本切分器 =====
        # RecursiveCharacterTextSplitter 会尝试按以下顺序切分：
        # 段落(\n\n) → 句子(\n) → 单词(空格) → 字符
        # 尽量保持语义完整性
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            # 中文文档的分隔符
            separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
        )

        # ===== 3. 确保存储目录存在 =====
        VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)

        # ===== 4. 连接 ChromaDB =====
        # persist_directory: 数据持久化到磁盘，重启不丢失
        # collection_name: 集合名称，相当于数据库的表
        self.vector_store = Chroma(
            collection_name="game_rules",
            embedding_function=self.embeddings,
            persist_directory=str(VECTOR_STORE_PATH),
        )

        logger.info(f"RAG Manager 初始化完成，向量库路径: {VECTOR_STORE_PATH}")

    def parse_pdf(self, file_path: str | Path) -> str:
        """
        解析 PDF 文件，提取全部文本

        Args:
            file_path: PDF 文件路径

        Returns:
            提取的文本内容
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        text_parts = []
        page_count = 0

        # PyMuPDF 打开 PDF
        with fitz.open(file_path) as doc:
            page_count = len(doc)  # 在 with 块内获取页数
            for page_num, page in enumerate(doc, start=1):
                # 提取页面文本
                text = page.get_text()
                if text.strip():
                    # 在每页开头添加页码标记，便于后续追溯
                    text_parts.append(f"[第{page_num}页]\n{text}")

        full_text = "\n\n".join(text_parts)
        logger.info(f"PDF解析完成: {file_path.name}, 共{page_count}页, {len(full_text)}字符")

        return full_text

    def parse_txt(self, file_path: str | Path) -> str:
        """
        解析 TXT 文件

        Args:
            file_path: TXT 文件路径

        Returns:
            文件内容
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        logger.info(f"TXT解析完成: {file_path.name}, {len(text)}字符")
        return text

    def add_document(self, file_path: str | Path, game_name: str) -> int:
        """
        将文档添加到向量库

        完整流程：解析 → 切块 → 向量化 → 存储

        Args:
            file_path: 文件路径（PDF或TXT）
            game_name: 游戏名称，作为元数据标签

        Returns:
            入库的文档块数量
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        # 1. 根据文件类型解析
        if suffix == ".pdf":
            text = self.parse_pdf(file_path)
        elif suffix == ".txt":
            text = self.parse_txt(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {suffix}，仅支持 PDF/TXT")

        # 2. 文本切块
        chunks = self.text_splitter.split_text(text)
        logger.info(f"文本切块完成: {len(chunks)}个块")

        if not chunks:
            logger.warning("文档内容为空，无法入库")
            return 0

        # 3. 准备元数据
        # 每个 chunk 都带上 game_name，检索时可以按游戏过滤
        metadatas = [{"game_name": game_name, "chunk_index": i} for i in range(len(chunks))]

        # 4. 生成唯一ID
        # 格式：game_name_chunk_0, game_name_chunk_1, ...
        # 相同游戏重复上传会覆盖旧数据
        ids = [f"{game_name}_chunk_{i}" for i in range(len(chunks))]

        # 5. 添加到向量库
        # add_texts 会自动调用 embedding 模型将文本转为向量
        self.vector_store.add_texts(
            texts=chunks,
            metadatas=metadatas,
            ids=ids,
        )

        logger.info(f"文档入库完成: game={game_name}, chunks={len(chunks)}")
        return len(chunks)

    def delete_game(self, game_name: str) -> bool:
        """
        删除指定游戏的所有规则数据

        Args:
            game_name: 游戏名称

        Returns:
            是否删除成功
        """
        try:
            # ChromaDB 通过 where 条件删除
            self.vector_store._collection.delete(
                where={"game_name": game_name}
            )
            logger.info(f"已删除游戏规则: {game_name}")
            return True
        except Exception as e:
            logger.error(f"删除游戏规则失败: {e}")
            return False

    def search(self, query: str, game_name: str, top_k: int | None = None) -> list[dict]:
        """
        检索相关规则

        Args:
            query: 查询文本（用户问题）
            game_name: 游戏名称，只在该游戏的规则中检索
            top_k: 返回最相关的K个结果

        Returns:
            检索结果列表，每个元素包含：
            - content: 文本内容
            - score: 相似度分数
            - metadata: 元数据
        """
        top_k = top_k or settings.RETRIEVAL_TOP_K

        # similarity_search_with_score 返回 (Document, score) 元组
        # score 越小越相似（欧氏距离）
        results = self.vector_store.similarity_search_with_score(
            query=query,
            k=top_k,
            filter={"game_name": game_name},  # 按游戏过滤
        )

        # 格式化返回结果
        formatted = []
        for doc, score in results:
            formatted.append({
                "content": doc.page_content,
                "score": score,
                "metadata": doc.metadata,
            })

        logger.debug(f"检索完成: query='{query[:50]}...', game={game_name}, 结果数={len(formatted)}")
        return formatted

    def list_games(self) -> list[str]:
        """
        列出所有已入库的游戏名称

        Returns:
            游戏名称列表
        """
        try:
            # 获取所有文档的元数据
            collection = self.vector_store._collection
            result = collection.get(include=["metadatas"])

            # 提取所有 game_name 并去重
            game_names = set()
            for metadata in result.get("metadatas", []):
                if metadata and "game_name" in metadata:
                    game_names.add(metadata["game_name"])

            return sorted(list(game_names))
        except Exception as e:
            logger.error(f"获取游戏列表失败: {e}")
            return []


# ===== 全局单例 =====
# 延迟初始化，首次使用时才创建
_rag_manager: RAGManager | None = None


def get_rag_manager() -> RAGManager:
    """
    获取 RAG 管理器单例

    使用方式：
        from core.rag import get_rag_manager
        rag = get_rag_manager()
        rag.add_document(...)
    """
    global _rag_manager
    if _rag_manager is None:
        _rag_manager = RAGManager()
    return _rag_manager
