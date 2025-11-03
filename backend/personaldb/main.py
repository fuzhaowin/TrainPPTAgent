#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date  : 2025/8/12
# @Desc  : 使用FastAPI实现API，接收JSON或RabbitMQ消息，下载七牛云文件，读取内容并生成embedding向量

import os
import json
import requests
import uvicorn
import logging
import asyncio
import uuid
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Request
from pydantic import BaseModel, ValidationError
from typing import List, Optional
import embedding_utils
from embedding_utils import cache_decorator
from urllib.parse import urlparse
from utils.validators import validate_url, sanitize_filename
from core.magic_pdf_converter import MagicPDFConverter
from core.markitdown_converter import MarkItDownConverter
from core.chunkers.semantic_chunker import SemanticChunker
from core.chunkers.fast_chunker import FastChunker

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 创建临时下载目录
TEMP_DIR = "temp_download"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# ======== 通用校验与错误映射工具函数 ========
def _to_int_or_error(name: str, value, min_value: int = 0) -> int:
    """
    将传入值转换为int并进行下限校验；失败则抛422。
    """
    try:
        iv = int(value)
    except Exception:
        raise HTTPException(status_code=422, detail=f"参数 {name} 必须为整数")
    if iv < min_value:
        raise HTTPException(status_code=422, detail=f"参数 {name} 必须≥{min_value}")
    return iv

def _is_embedding_backend_error(msg: str) -> bool:
    """
    识别典型嵌入后端不可用错误信息，统一映射为 503。
    """
    patterns = [
        "Expected Embeddings to be non-empty",  # chromadb空向量
        "Ollama embeddings失败",               # ollama返回非200
        "Failed to establish a connection",    # 连接失败
        "Connection refused",                  # 服务拒绝连接
        "Model not found",                     # 模型不存在
        "no such model",                       # ollama 未拉取模型
    ]
    m = msg.lower()
    return any(p.lower() in m for p in patterns)

def _raise_embedding_503(extra: str = ""):
    hint = "嵌入模型不可用或未安装，请检查 EMBEDDING_PROVIDER/EMBEDDING_MODEL 及后端服务。"
    if extra:
        hint = f"{hint} 详情：{extra}"
    raise HTTPException(status_code=503, detail=hint)

# RabbitMQ消息处理类

class SearchQuery(BaseModel):
    # 统一语义：允许传入 int 或 str，但默认值为 0
    # 实际在端点中通过 _to_int_or_error 强制为非负整数
    userId: Optional[int | str] = 0
    query: str
    keyword: Optional[str] = ""
    topk: Optional[int] = 3

@app.post("/search")
def search_personal_knowledge_base(query: SearchQuery):
    """
    搜索个人知识库
    """
    try:
        logger.info(f"收到搜索请求: {query}")
        # 统一 userId 语义：转换为非负整数，缺省为 0（先校验后初始化后端，避免后端错误遮蔽入参错误）
        user_id_int = _to_int_or_error("userId", query.userId if query.userId is not None else 0, min_value=0)
        embedder = embedding_utils.EmbeddingModel()
        chroma = embedding_utils.ChromaDB(embedder)
        collection_name = f"user_{user_id_int}"

        result = chroma.query2collection(
            collection=collection_name,
            query_documents=[query.query],
            keyword=query.keyword,
            topk=query.topk
        )
        logger.info(f"搜索成功: {result}")
        return result
    except HTTPException as he:
        # 直接透传校验/参数类错误，例如 422
        raise he
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@cache_decorator
def _get_markdown_content(file_path: str, file_name: str) -> str:
    """
    根据文件类型选择合适的转换器，将文件内容转换为Markdown格式。
    PDF文件使用MagicPDFConverter（MinerU），其他文件使用MarkitdownConverter。
    """
    # 获取文件扩展名, 是否可以使用MinerU，如果不用显卡速度太慢
    USE_MINERU = os.environ.get("USE_MINERU", "false")
    if USE_MINERU.lower() == "true":
        CAN_USE_MINERU = True
    else:
        CAN_USE_MINERU = False
    file_extension = os.path.splitext(file_name)[1].lower() if file_name else ""

    # 根据文件类型选择转换器
    if CAN_USE_MINERU and file_extension == '.pdf':
        # 使用 MinerU (MagicPDFConverter) 处理PDF
        logger.info(f"使用PDF转换器(MinerU)处理文件: {file_path}")
        converter = MagicPDFConverter(output_dir="./output_pdf")
        content, _ = converter.convert_pdf_file(file_path)
        return True, content
    else:
        # 使用 markitdown 处理其他文件
        logger.info(f"使用Markitdown转换器处理文件: {file_path}")
        converter = MarkItDownConverter(use_magic_pdf=False)  #use_magic_pdf设定是否使用MinerU
        content, _ = converter.convert_file(file_path)
        return True, content


def process_and_vectorize_local_file(file_name: str, temp_file_path: str, id: int, user_id: int|str, file_type: str, url: str, folder_id: int):
    """
    从本地文件路径处理文件、进行向量化并存储
    """
    # 步骤2: 使用适当的转换器读取文件内容
    logger.info(f"开始读取文件内容: {temp_file_path}")
    
    status, markdown_content = _get_markdown_content(temp_file_path, file_name)

    if not markdown_content or not markdown_content.strip():
        logger.error(f"文件内容为空或无效: {temp_file_path}")
        raise ValueError("文件内容为空或无效")
    logger.info(f"文件内容读取成功，准备进行分块。")

    # 对Markdown格式进行Trunk(分块)
    documents = _chunk_text(markdown_content)
    if not documents:
        raise ValueError("分块后内容为空")
    logger.info(f"内容分块成功，共 {len(documents)} 块。")
    # 调试输出：首块预览，便于定位嵌入失败原因
    try:
        preview = documents[0] if documents else ""
        print(f"[DEBUG] chunk_count={len(documents)} first_chunk='{preview[:120].replace('\n',' ')}'...")
    except Exception as _:
        pass

    # 步骤3: 基础环境检查
    provider = os.getenv("EMBEDDING_PROVIDER")
    model = os.getenv("EMBEDDING_MODEL")
    if not provider or not model:
        logger.error("缺少嵌入模型配置：请设置 EMBEDDING_PROVIDER 与 EMBEDDING_MODEL")
        raise ValueError("缺少嵌入模型配置：请设置 EMBEDDING_PROVIDER 与 EMBEDDING_MODEL")

    # 步骤4: 使用embedding_utils生成embedding向量并插入向量
    logger.info("初始化embedding模型")
    embedder = embedding_utils.EmbeddingModel()
    chroma = embedding_utils.ChromaDB(embedder)
    logger.info(f"开始插入文件 {id} 的向量")
    try:
        embedding_result = chroma.insert_file_vectors(
            file_name=file_name,
            user_id=user_id,
            file_id=id,
            file_type=file_type or "unknown",
            url=url or "",
            folder_id=folder_id or 0,
            documents=documents
        )
        # 兜底：即使插入成功也校验返回结构
        data = embedding_result.get("data", []) if isinstance(embedding_result, dict) else []
        if not data or any((not one.get("embedding")) for one in data if isinstance(one, dict)):
            _raise_embedding_503("嵌入结果为空或无效")
    except Exception as e:
        msg = str(e)
        logger.error(f"插入向量阶段失败: {msg}", exc_info=True)
        if _is_embedding_backend_error(msg):
            _raise_embedding_503(msg)
        raise
    logger.info("向量插入成功")

    result = {
        "id": id,
        "file_name": file_name,
        "userId": user_id,
        "fileType": file_type,
        "url": url,
        "folderId": folder_id,
        "embedding_result": embedding_result,
        "markdown_content": markdown_content
    }
    logger.info(f"处理OK。。。")
    return result


def process_file_sync(file_name:str, id: int, user_id: int|str, file_type: str, url: str, folder_id: int):
    """
    处理文件下载、读取和生成embedding的同步版本
    """
    if not url:
        logger.error("url为空")
        raise ValueError("url不能为空")

    # 验证URL格式
    if not validate_url(url):
        logger.error(f"无效的URL格式: {url}")
        raise ValueError("url格式无效，必须为以 http(s) 开头的有效URL")

    parsed_url = urlparse(url)
    logger.info(f"解析后的URL: {parsed_url.geturl()}")
    temp_file_path = None
    try:
        # 步骤1: 下载文件
        # file_name = os.path.basename(parsed_url.path) or f"downloaded_file_{user_id}"
        temp_file_path = os.path.join(TEMP_DIR, file_name)
        logger.info(f"开始下载文件: {url}")
        response = requests.get(url, timeout=60, proxies=None)
        response.raise_for_status()
        with open(temp_file_path, 'wb') as f:
            f.write(response.content)
        logger.info(f"文件下载成功: {temp_file_path}")

        return process_and_vectorize_local_file(file_name, temp_file_path, id, user_id, file_type, url, folder_id)

    except requests.exceptions.Timeout as e:
        logger.error(f"下载文件超时: {str(e)}", exc_info=True)
        raise ValueError(f"下载文件超时: {str(e)}")
    except requests.exceptions.RequestException as e:
        logger.error(f"下载文件失败: {str(e)}", exc_info=True)
        raise ValueError(f"下载文件失败: {str(e)}")
    except ValueError as e:
        logger.error(f"处理失败: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"未知错误: {str(e)}", exc_info=True)
        raise ValueError(f"未知错误: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.info(f"临时文件已删除: {temp_file_path}")


@app.post("/upload/")
async def upload_and_vectorize_endpoint(request: Request):
    """
    支持三种内容类型：
    - multipart/form-data（带或不带文件）
    - application/x-www-form-urlencoded
    - application/json

    字段：
    - userId: int
    - fileId: int
    - folderId: int (可选，默认0)
    - fileType: str (可选)
    - url: str (可选，与 file 互斥)
    - file: UploadFile (可选，与 url 互斥)
    """
    temp_file_path = None
    try:
        # 统一解析 body
        content_type = request.headers.get("content-type", "")
        data = {}
        upload_file: UploadFile | None = None

        if "application/json" in content_type:
            data = await request.json()
        else:
            # 对 multipart/form-data 与 x-www-form-urlencoded 都适用
            form = await request.form()
            data = dict(form)
            possible_file = form.get("file")
            if possible_file:
                upload_file = possible_file

        # 参数解析与校验
        userId_raw = data.get("userId")
        fileId_raw = data.get("fileId")

        if userId_raw is None:
            raise HTTPException(status_code=422, detail="缺少或非法参数: userId")
        if fileId_raw is None:
            raise HTTPException(status_code=422, detail="缺少或非法参数: fileId")
        # 强制数值校验
        userId = _to_int_or_error("userId", userId_raw, min_value=0)
        fileId = _to_int_or_error("fileId", fileId_raw, min_value=0)
        folderId = _to_int_or_error("folderId", data.get("folderId", 0), min_value=0)
        fileType = data.get("fileType")
        url = data.get("url")

        # 互斥校验
        has_url = bool(url and str(url).strip())
        has_file = upload_file is not None
        if not has_url and not has_file:
            raise HTTPException(status_code=400, detail="必须提供 'url' 或 'file'")
        if has_url and has_file:
            raise HTTPException(status_code=400, detail="只能提供 'url' 或 'file' 中的一个")

        # 分支：文件上传
        if has_file:
            # 推断 fileType
            if not fileType and upload_file and upload_file.filename:
                fileType = upload_file.filename.split(".")[-1] if "." in upload_file.filename else "unknown"
            safe_name = sanitize_filename(upload_file.filename or "uploaded_file")
            temp_file_name = f"{uuid.uuid4()}_{safe_name}"
            temp_file_path = os.path.join(TEMP_DIR, temp_file_name)
            # 保存上传内容
            content_bytes = await upload_file.read()
            with open(temp_file_path, "wb") as buffer:
                buffer.write(content_bytes)
            logger.info(f"文件上传成功: {temp_file_path}")

            return process_and_vectorize_local_file(
                file_name=safe_name,
                temp_file_path=temp_file_path,
                id=fileId,
                user_id=userId,
                file_type=fileType,
                url="",  # 直接上传无 URL
                folder_id=folderId
            )

        # 分支：URL 下载处理
        else:
            # URL 校验
            if not validate_url(url or ""):
                raise HTTPException(status_code=422, detail="url格式无效，请提供以 http(s) 开头且域名有效的地址")
            file_name = os.path.basename(urlparse(url).path) or f"downloaded_file_{userId}"
            file_name = sanitize_filename(file_name)
            return process_file_sync(
                file_name=file_name,
                id=fileId,
                user_id=userId,
                file_type=fileType,
                url=url,
                folder_id=folderId
            )

    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        logger.error(f"上传和向量化失败: {msg}", exc_info=True)
        if _is_embedding_backend_error(msg):
            _raise_embedding_503(msg)
        raise HTTPException(status_code=500, detail=msg)
    finally:
        pass
        # if temp_file_path and os.path.exists(temp_file_path):
        #     os.remove(temp_file_path)
        #     logger.info(f"临时文件已删除: {temp_file_path}")


class TextVectorizeBody(BaseModel):
    """
    纯文本向量化请求体。
    仅必需字段：content, fileId, fileName
    其余参数均为可选，默认空/0。
    """
    content: str
    fileId: int
    fileName: str
    userId: Optional[int] = 0
    fileType: Optional[str] = None
    url: Optional[str] = ""
    folderId: Optional[int] = 0


def _chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> List[str]:
    """
    使用 SemanticChunker 进行分块。
    """
    text = (text or "").strip()
    if not text:
        return []
    chunker = FastChunker(max_tokens=max_chars)
    chunks = chunker.chunk_text(text)
    return [chunk.content for chunk in chunks]


def process_text_content(
    file_name: str,
    text: str,
    id: int,
    user_id: int = 0,
    file_type: Optional[str] = None,
    folder_id: int = 0,
    url: str = ""
):
    """
    直接对纯文本进行向量化并落库（Chroma）。
    其余参数默认空/0，以满足“无需额外参数”的需求。
    """
    logger.info("开始处理纯文本向量化")
    if not text or not text.strip():
        # 入参问题应返回 422
        raise HTTPException(status_code=422, detail="content 不能为空")

    # 与现有流程保持一致的环境变量校验
    provider = os.getenv("EMBEDDING_PROVIDER")
    model = os.getenv("EMBEDDING_MODEL")
    if not provider or not model:
        logger.error("缺少嵌入模型配置：请设置 EMBEDDING_PROVIDER 与 EMBEDDING_MODEL")
        raise ValueError("缺少嵌入模型配置：请设置 EMBEDDING_PROVIDER 与 EMBEDDING_MODEL")

    documents = _chunk_text(text)
    if not documents:
        # 入参问题应返回 422
        raise HTTPException(status_code=422, detail="content 无有效文本")

    logger.info("初始化 embedding 模型与 Chroma")
    embedder = embedding_utils.EmbeddingModel()
    chroma = embedding_utils.ChromaDB(embedder)

    logger.info(f"插入文本向量：fileId={id}, userId={user_id}")
    try:
        embedding_result = chroma.insert_file_vectors(
            file_name=file_name,
            user_id=user_id or 0,
            file_id=id,
            file_type=file_type or "unknown",
            url=url or "",
            folder_id=folder_id or 0,
            documents=documents
        )
        data = embedding_result.get("data", []) if isinstance(embedding_result, dict) else []
        if not data or any((not one.get("embedding")) for one in data if isinstance(one, dict)):
            _raise_embedding_503("嵌入结果为空或无效")
    except Exception as e:
        msg = str(e)
        logger.error(f"插入文本向量失败: {msg}", exc_info=True)
        if _is_embedding_backend_error(msg):
            _raise_embedding_503(msg)
        raise

    result = {
        "id": id,
        "file_name": file_name,
        "userId": user_id or 0,
        "fileType": file_type or "unknown",
        "url": url or "",
        "folderId": folder_id or 0,
        "embedding_result": embedding_result
    }
    logger.info("纯文本向量化完成")
    return result


# ===== 纯文本向量化接口 =====
@app.post("/vectorize/text")
def vectorize_text_endpoint(body: TextVectorizeBody):
    """
    纯文本向量化：
    - 必填：content, fileId, fileName
    - 可选：userId(默认0), fileType(None), url(""), folderId(0)
    """
    try:
        logger.info(
            f"收到文本向量化请求: fileId={body.fileId}, fileName={body.fileName}, userId={body.userId}"
        )
        # 基础参数校验
        if not body.fileName or not str(body.fileName).strip():
            raise HTTPException(status_code=422, detail="fileName 不能为空")
        _ = _to_int_or_error("fileId", body.fileId, min_value=0)
        _ = _to_int_or_error("userId", body.userId or 0, min_value=0)
        safe_name = sanitize_filename(body.fileName)
        # URL 校验（可选）
        if body.url:
            if not validate_url(body.url):
                raise HTTPException(status_code=422, detail="url格式无效，请提供以 http(s) 开头且域名有效的地址")
        return process_text_content(
            file_name=safe_name,
            text=body.content,
            id=body.fileId,
            user_id=body.userId or 0,
            file_type=body.fileType,
            folder_id=body.folderId or 0,
            url=body.url or ""
        )
    except HTTPException as he:
        # 直接透传 4xx/5xx 的明确错误
        raise he
    except Exception as e:
        msg = str(e)
        logger.error(f"文本向量化失败: {msg}", exc_info=True)
        if _is_embedding_backend_error(msg):
            _raise_embedding_503(msg)
        raise HTTPException(status_code=500, detail=f"文本向量化失败: {msg}")

@app.get("/files/{user_id}")
def list_user_files(user_id: int):
    """
    列出指定用户的所有文件信息
    """
    try:
        logger.info(f"收到列出用户 {user_id} 文件的请求")
        embedder = embedding_utils.EmbeddingModel()
        chroma = embedding_utils.ChromaDB(embedder)

        files = chroma.list_files_by_user(user_id=user_id)

        if not files:
            logger.info(f"用户 {user_id} 没有任何文件。")
            return []

        logger.info(f"成功为用户 {user_id} 找到 {len(files)} 个文件。")
        return files
    except Exception as e:
        logger.error(f"列出用户 {user_id} 的文件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"列出文件失败: {str(e)}")


if __name__ == "__main__":
    """
    主函数入口：启动FastAPI服务
    """
    print("启动Personal DB FastAPI服务...")
    uvicorn.run(app, host="127.0.0.1", port=9100)
