import asyncio
import json
import re
import os
import base64
import dotenv
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
import time
import logging
from pydantic import BaseModel
import uuid
import httpx
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import UploadFile, File, HTTPException, Form
from fastapi import FastAPI, HTTPException, Query, Request, Response
from outline_client import A2AOutlineClientWrapper
from content_client import A2AContentClientWrapper
from typing import Any, Dict, Optional, List
from tempfile import NamedTemporaryFile
from template.qwen_vl_2dgrounding import (
    build_prompt_for_template,
    infer_with_openai_compat,
    merge_template_types,
)
try:
    # 部分版本脚本提供 safe_json_loads / parse_json_fenced
    from template.qwen_vl_2dgrounding import safe_json_loads, parse_json_fenced  # type: ignore
except Exception:
    safe_json_loads = None  # type: ignore
    parse_json_fenced = None  # type: ignore

logger = logging.getLogger(__name__)
dotenv.load_dotenv()

# 加载统一环境配置
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    dotenv.load_dotenv(env_file)
else:
    dotenv.load_dotenv()

OUTLINE_API = os.environ.get("OUTLINE_API", f"http://{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('OUTLINE_API_PORT', '10001')}")
CONTENT_API = os.environ.get("CONTENT_API", f"http://{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('CONTENT_API_PORT', '10011')}")
app = FastAPI()

# Allow CORS for the frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AipptRequest(BaseModel):
    content: str
    language: str
    model: str
    stream: bool

async def stream_agent_response(prompt: str, language: str = "chinese"):
    """A generator that yields parts of the agent response."""
    outline_wrapper = A2AOutlineClientWrapper(session_id=uuid.uuid4().hex, agent_url=OUTLINE_API)
    async for chunk_data in outline_wrapper.generate(prompt, language=language):
        logger.info(f"生成大纲输出的chunk_data: {chunk_data}")
        if chunk_data["type"] == "text":
            yield chunk_data["text"]


@app.post("/tools/aippt_outline")
async def aippt_outline(request: AipptRequest):
    assert request.stream, "只支持流式的返回大纲"
    logger.info(f"前端*outline***=====>用户输入：{request.language}")
    return StreamingResponse(stream_agent_response(request.content, request.language), media_type="text/plain")


@app.post("/tools/aippt_outline_from_file")
async def aippt_outline_from_file(
    user_id: int|str = Form(...),
    file: UploadFile = File(None),  # 允许缺省，这样我们可以决定走 file 或 url
    url: str | None = Form(None),
    folder_id: int|str = Form(0),
    file_type: str | None = Form(None),
    language: str = Form("chinese"),  # 添加language参数，默认为chinese
):
    """
    对齐 personaldb 的 /upload/：
    - 必填: userId, fileId
    - 可选: folderId (默认0), fileType
    - file 与 url 互斥，至少一个
    """
    personaldb_api_url = os.getenv("PERSONAL_DB")
    if not personaldb_api_url:
        raise HTTPException(status_code=500, detail="PERSONAL_DB 未配置")

    # 互斥校验（与 personaldb 完全一致）
    has_file = file is not None
    has_url = bool(url and url.strip())

    # 生成 fileId（字符串更稳；personaldb 会 int()）
    file_id = str(int(time.time() * 1000))

    # 推断 fileType（当上传文件时且未显式传入）
    if has_file and not file_type:
        if file.filename and "." in file.filename:
            file_type = file.filename.rsplit(".", 1)[-1]
        else:
            file_type = "unknown"

    # 组装 multipart/form-data
    # 注意：即使是 url 分支，也仍用 multipart，personaldb 也能解析 form
    data = {
        "userId": str(user_id),
        "fileId": file_id,
        "folderId": str(folder_id),
    }
    if file_type:
        data["fileType"] = file_type
    if has_url:
        data["url"] = url.strip()

    files_payload = None
    if has_file:
        # 读取一次到内存，httpx 需要 (filename, bytes/obj, content_type)
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="文件内容为空")
        files_payload = {
            "file": (
                file.filename or "uploaded_file",
                file_bytes,
                file.content_type or "application/octet-stream",
            )
        }

    upload_url = f"{personaldb_api_url.rstrip('/')}/upload/"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                upload_url,
                data=data,
                files=files_payload,
                timeout=360.0,
            )
            # 不直接 raise，先打日志方便定位
            if resp.status_code >= 400:
                # 打印下游返回体，personaldb 对错误信息写得很清楚
                logger.info(f"[personaldb {resp.status_code}] {resp.text}")
                resp.raise_for_status()

            # personaldb 的处理函数最终会返回一个 JSON（你上游期望里要有 markdown_content）
            try:
                result = resp.json()
            except ValueError:
                raise HTTPException(status_code=502, detail=f"personaldb 返回的不是 JSON：{resp.text}")

            markdown_content = result.get("markdown_content")
            if markdown_content is None:
                raise HTTPException(status_code=500, detail="personaldb 响应缺少 'markdown_content'")
            logger.info(f"本地上传文件*outline***=====>：{ {'language': language} }")

            return StreamingResponse(stream_agent_response(markdown_content, language), media_type="text/plain")

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request to personaldb timed out.")
        except httpx.HTTPStatusError as exc:
            # 透传 personaldb 的错误详情，便于你在日志里看到具体字段问题
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Error connecting to personaldb: {exc}")

class AipptContentRequest(BaseModel):
    content: str
    language: str = "zh"  #默认中文
    sessionId: str = ""  # 当使用知识库时，需要根据用户的user_id查询对应的知识库
    generateFromUploadedFile: bool = False  # 是否从上传的文件中生成PPT内容
    generateFromWebSearch: bool = True  # 是否从网络搜索中生成PPT内容

async def stream_content_response(markdown_content: str, language, generateFromUploadedFile, generateFromWebSearch, user_id):
    match = re.search(r"(# .*)", markdown_content, flags=re.DOTALL)
    result = markdown_content[match.start():] if match else markdown_content
    logger.info(f"用户输入的markdown大纲是：{result}")

    content_wrapper = A2AContentClientWrapper(session_id=uuid.uuid4().hex, agent_url=CONTENT_API)

    search_engine = []
    if generateFromUploadedFile:
        search_engine.append("KnowledgeBaseSearch")
    if generateFromWebSearch:
        search_engine.append("PaperSearch")

    metadata = {"user_id": user_id, "search_engine": search_engine, "language": language}
    logger.info(f"前端*内容**=====>metadata数据为：{metadata}")

    last_flush = asyncio.get_event_loop().time()

    async for chunk_data in content_wrapper.generate(user_question=result, metadata=metadata):
        logger.info(f"生成正文输出的chunk_data: {chunk_data}")

        # 心跳：每15秒发一次注释，避免某些代理断连接
        now = asyncio.get_event_loop().time()
        if now - last_flush > 10:
            yield b": keep-alive\n\n"
            last_flush = now

        if chunk_data.get("type") == "text":
            # 注意：每条 SSE 事件以空行结束
            payload = chunk_data["text"]
            yield f"data: {payload}\n\n".encode("utf-8")

    # 可选：显式结束信号（前端可据此收尾）
    yield b"data: [DONE]\n\n"

@app.post("/tools/aippt")
async def aippt_content(request: AipptContentRequest):
    markdown_content = request.content
    # 兼容旧字段名：如果 user_id 为空就用 sessionId
    user_id = getattr(request, "user_id", None) or getattr(request, "sessionId", None)

    async def event_generator():
        async for chunk in stream_content_response(
            markdown_content,
            language=request.language,
            generateFromUploadedFile=request.generateFromUploadedFile,
            generateFromWebSearch=request.generateFromWebSearch,
            user_id=user_id
        ):
            yield chunk

    # 关键：SSE 推荐这些头
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.get("/data/{filename}")
async def get_data(filename: str):
    file_path = os.path.join("./template", filename)
    return FileResponse(file_path)

@app.get("/templates")
async def get_templates():
    templates = [
        { "name": "红色通用", "id": "template_1", "cover": "/api/data/template_1.jpg" },
        { "name": "蓝色通用", "id": "template_2", "cover": "/api/data/template_2.jpg" },
        { "name": "紫色通用", "id": "template_3", "cover": "/api/data/template_3.jpg" },
        { "name": "莫兰迪配色", "id": "template_4", "cover": "/api/data/template_4.jpg" },
        # { "name": "图表", "id": "template_6", "cover": "/api/data/template_6.jpg" },
    ]

    return {"data": templates}

# =============================
# 模板初标注：调用 Qwen-VL 对页面进行类型与元素角色识别
# =============================

class AnnotateRequest(BaseModel):
    image_b64: str
    slide_json: Dict[str, Any]
    model: Optional[str] = None
    iou: Optional[float] = 0.25


@app.post("/template/annotate")
async def template_annotate(req: AnnotateRequest):
    api_key = os.environ.get("ALI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ALI_API_KEY 未配置，请在后端 .env 中设置")

    # 写入临时图片文件（支持 data:image/*;base64, 前缀或纯 base64）
    img_b64 = req.image_b64
    if "," in img_b64 and img_b64.startswith("data:"):
        img_b64 = img_b64.split(",", 1)[1]
    try:
        img_bytes = base64.b64decode(img_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="image_b64 不是合法的 base64 图片数据")

    with NamedTemporaryFile(delete=False, suffix=".png") as tf:
        tf.write(img_bytes)
        tmp_img_path = tf.name

    try:
        prompt = build_prompt_for_template()
        model_name = req.model or "qwen3-vl-235b-a22b-instruct"
        model_text = infer_with_openai_compat(
            api_key=api_key,
            image_path_or_url=tmp_img_path,
            prompt=prompt,
            model=model_name,
        )

        # 解析模型返回
        model_obj: Dict[str, Any]
        if safe_json_loads:
            parsed = safe_json_loads(model_text)  # type: ignore
            if not isinstance(parsed, dict):
                # 尝试去掉围栏再解析
                body = parse_json_fenced(model_text) if parse_json_fenced else model_text
                parsed = json.loads(body)
            model_obj = parsed  # type: ignore
        else:
            body = model_text
            # 尝试围栏剥离
            if model_text.strip().startswith("```"):
                if parse_json_fenced:
                    body = parse_json_fenced(model_text)  # type: ignore
            model_obj = json.loads(body)

        merged_slide = merge_template_types(req.slide_json, model_obj, iou_thresh=req.iou or 0.25)

        return {
            "model": model_obj,
            "merged_slide": merged_slide,
        }
    except Exception as e:
        logger.exception("模板初标注失败")
        raise HTTPException(status_code=500, detail=f"模板初标注失败: {e}")
    finally:
        try:
            os.remove(tmp_img_path)
        except Exception:
            pass

# =============================
# 模板重写：将不规范的 JSON 结构标准化为前端 Slide 类型
# =============================

class RewriteRequest(BaseModel):
    slide_json: Dict[str, Any] | None = None
    doc_json: Dict[str, Any] | None = None
    image_b64: Optional[str] = None
    model: Optional[str] = None
    iou: Optional[float] = 0.25
    normalize_theme: bool = True
    strict: bool = False


def _map_page_type_to_slide_type(page_type: str) -> str:
    mapper = {
        "cover": "cover",
        "section": "transition",
        "thankyou": "end",
        "title-content": "content",
        "two-column": "content",
        "image-caption": "content",
        "list": "content",
        "unknown": "content",
    }
    return mapper.get(page_type, "content")


def _default_theme() -> Dict[str, Any]:
    return {
        "backgroundColor": "#ffffff",
        "themeColors": ["#007AFF", "#34C759", "#FF9500", "#5856D6"],
        "fontColor": "#333333",
        "fontName": "Arial",
        "outline": {"style": "solid", "width": 1, "color": "#000000"},
        "shadow": {"h": 0, "v": 0, "blur": 0, "color": "rgba(0,0,0,0.15)"},
    }


def _canonicalize_element(e: Dict[str, Any], W: int, H: int, strict: bool) -> Dict[str, Any] | None:
    etype = e.get("type")
    # 预取几何信息
    left = e.get("left")
    top = e.get("top")
    width = e.get("width")
    height = e.get("height")
    rotate = e.get("rotate", 0)

    # 如果没有几何信息但存在 bbox_2d，转为绝对坐标
    bbox = e.get("bbox_2d")
    if (left is None or top is None or width is None or height is None) and isinstance(bbox, list) and len(bbox) == 4 and W and H:
        x1, y1, x2, y2 = bbox
        # bbox 使用 0~1000 相对坐标
        left = int(round(x1 / 1000.0 * W))
        top = int(round(y1 / 1000.0 * H))
        width = int(round((x2 - x1) / 1000.0 * W))
        height = int(round((y2 - y1) / 1000.0 * H))

    # 必要几何缺失时，严格模式下丢弃；非严格则跳过
    if left is None or top is None or width is None or height is None:
        return None if strict else None

    base = {
        "id": str(e.get("id") or uuid.uuid4()),
        "left": left,
        "top": top,
        "width": width,
        "height": height,
        "rotate": rotate,
    }

    # 处理文本
    if etype == "text":
        content = e.get("content")
        if content is None:
            content = ""
        text_el = {
            **base,
            "type": "text",
            "content": content,
            "defaultFontName": e.get("defaultFontName", "Arial"),
            "defaultColor": e.get("defaultColor", "#333333"),
        }
        # 保留 textType 映射
        if e.get("textType"):
            text_el["textType"] = e["textType"]
        # 可选样式
        for k in ["outline", "fill", "lineHeight", "wordSpace", "opacity", "shadow", "paragraphSpace", "vertical"]:
            if k in e:
                text_el[k] = e[k]
        return text_el

    # 图片
    if etype == "image":
        src = e.get("src")
        if not src:
            return None if strict else None
        img_el = {
            **base,
            "type": "image",
            "fixedRatio": bool(e.get("fixedRatio", True)),
            "src": src,
        }
        for k in ["outline", "filters", "clip", "flipH", "flipV", "shadow", "radius", "colorMask", "imageType"]:
            if k in e:
                img_el[k] = e[k]
        return img_el

    # 形状或其他：转为 shape，标记 special 以保证可视化不丢失
    shape_el = {
        **base,
        "type": "shape",
        "viewBox": [1000, 1000],
        "path": e.get("path", "M0 0 L1000 0 L1000 1000 L0 1000 Z"),
        "fixedRatio": bool(e.get("fixedRatio", False)),
        "fill": e.get("fill", "#EFEFEF"),
        "special": True,
    }
    # 尝试继承文本（如果存在）
    if e.get("text"):
        shape_el["text"] = e["text"]
    for k in ["gradient", "pattern", "outline", "opacity", "flipH", "flipV", "shadow", "pathFormula", "keypoints"]:
        if k in e:
            shape_el[k] = e[k]
    return shape_el


def _canonicalize_doc(doc: Dict[str, Any], strict: bool = False) -> Dict[str, Any]:
    width = int(doc.get("width") or 1280)
    height = int(doc.get("height") or 720)
    theme = doc.get("theme") if isinstance(doc.get("theme"), dict) else _default_theme()

    slides_in = doc.get("slides")
    if not isinstance(slides_in, list):
        # 兼容单页结构
        single = {k: v for k, v in doc.items() if k != "slides"}
        slides_in = [single]

    slides_out: List[Dict[str, Any]] = []
    for s in slides_in:
        elements = s.get("elements") if isinstance(s.get("elements"), list) else []
        W = int(s.get("width") or width)
        H = int(s.get("height") or height)

        clean_elems: List[Dict[str, Any]] = []
        for e in elements:
            ce = _canonicalize_element(e, W, H, strict)
            if ce:
                clean_elems.append(ce)

        slide_type = _map_page_type_to_slide_type(s.get("type") or "unknown")
        slides_out.append({
            "id": str(s.get("id") or uuid.uuid4()),
            "elements": clean_elems,
            "background": s.get("background"),
            "animations": s.get("animations"),
            "turningMode": s.get("turningMode"),
            "sectionTag": s.get("sectionTag"),
            "type": slide_type,
        })

    return {
        "slides": slides_out,
        "theme": theme,
        "width": width,
        "height": height,
    }


@app.post("/template/rewrite")
async def template_rewrite(req: RewriteRequest):
    """
    将不规范的 slide/doc JSON 标准化为前端可用的模板 JSON。
    可选：提供截图 image_b64，融合视觉识别结果以完善 textType 与页面类型。
    返回：canonical 标准 JSON；model（如调用了视觉识别）；diagnostics（处理信息）。
    """
    # 选择输入
    if req.doc_json is not None:
        working_doc = req.doc_json
    elif req.slide_json is not None:
        working_doc = {"slides": [req.slide_json], "width": req.slide_json.get("width"), "height": req.slide_json.get("height")}
    else:
        raise HTTPException(status_code=400, detail="必须提供 doc_json 或 slide_json")

    model_obj: Optional[Dict[str, Any]] = None
    merged_slide: Optional[Dict[str, Any]] = None
    diagnostics: Dict[str, Any] = {}

    # 如果提供了截图，则先调用视觉模型进行角色识别，写回合并结果
    tmp_img_path = None
    if req.image_b64:
        api_key = os.environ.get("ALI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="ALI_API_KEY 未配置，请在后端 .env 中设置")
        img_b64 = req.image_b64
        if "," in img_b64 and img_b64.startswith("data:"):
            img_b64 = img_b64.split(",", 1)[1]
        try:
            img_bytes = base64.b64decode(img_b64)
        except Exception:
            raise HTTPException(status_code=400, detail="image_b64 不是合法的 base64 图片数据")
        with NamedTemporaryFile(delete=False, suffix=".png") as tf:
            tf.write(img_bytes)
            tmp_img_path = tf.name

        try:
            prompt = build_prompt_for_template()
            model_name = req.model or "qwen3-vl-235b-a22b-instruct"
            model_text = infer_with_openai_compat(
                api_key=api_key,
                image_path_or_url=tmp_img_path,
                prompt=prompt,
                model=model_name,
            )
            if safe_json_loads:
                parsed = safe_json_loads(model_text)  # type: ignore
                if not isinstance(parsed, dict):
                    body = parse_json_fenced(model_text) if parse_json_fenced else model_text
                    parsed = json.loads(body)
                model_obj = parsed  # type: ignore
            else:
                body = model_text
                if model_text.strip().startswith("```") and parse_json_fenced:
                    body = parse_json_fenced(model_text)  # type: ignore
                model_obj = json.loads(body)

            # 合并回第一张 slide（或单页）
            if "slides" in working_doc and isinstance(working_doc["slides"], list) and working_doc["slides"]:
                merged_slide = merge_template_types(working_doc["slides"][0], model_obj, iou_thresh=req.iou or 0.25)
                working_doc["slides"][0] = merged_slide
            else:
                merged_slide = merge_template_types(working_doc, model_obj, iou_thresh=req.iou or 0.25)
                working_doc = {"slides": [merged_slide], "width": working_doc.get("width"), "height": working_doc.get("height")}
        except Exception as e:
            logger.exception("视觉识别合并失败")
            raise HTTPException(status_code=500, detail=f"视觉识别合并失败: {e}")
        finally:
            if tmp_img_path:
                try:
                    os.remove(tmp_img_path)
                except Exception:
                    pass

    # 进行标准化重写
    canonical = _canonicalize_doc(working_doc, strict=req.strict)
    # 统计信息
    diagnostics["slide_count"] = len(canonical.get("slides", []))
    diagnostics["width"] = canonical.get("width")
    diagnostics["height"] = canonical.get("height")
    diagnostics["normalized_theme"] = bool(canonical.get("theme"))

    return {
        "canonical": canonical,
        "model": model_obj,
        "diagnostics": diagnostics,
    }

class AipptByIDRequest(BaseModel):
    id: str
    language: str = "chinese"  # 添加language字段，默认为chinese

async def aippt_file_id_streamer(id: str, language: str = "chinese"):
    """根据用户的已有的文件数据中的文件id来生成ppt
    id: 文件的id，例如论文的pmid
    """
    yield json.dumps({"type": "status", "message": "正在解析文件..."}, ensure_ascii=False) + '\n'
    paper_markdown = ""
    if not paper_markdown:
        yield json.dumps({"type": "status", "message": "没有找到该文章"}, ensure_ascii=False) + '\n'
        return
    personaldb_api_url = os.getenv("PERSONAL_DB")
    if not personaldb_api_url:
        raise HTTPException(status_code=500, detail="PERSONAL_DB 未配置")
    # 论文名称
    file_name = f"{id}.md"
    data = {
        "userId": id,
        "fileId": id,
        "folderId": 123,
        "fileType": "txt"
    }
    files = {"file": (file_name, paper_markdown, "text/plain")}
    upload_url = f"{personaldb_api_url.rstrip('/')}/upload/"
    response = httpx.post(upload_url, data=data, files=files, timeout=40.0)
    result = response.json()
    if not result.get("id"):
        yield json.dumps({"type": "status", "message": "论文向量化失败，请联系管理员"}, ensure_ascii=False) + '\n'
    yield json.dumps({"type": "status", "message": "正在生成大纲..."}, ensure_ascii=False) + '\n'
    outline = ""
    async for outline_trunk in stream_agent_response(paper_markdown, language):
        outline += outline_trunk
    yield json.dumps({"type": "status", "message": "大纲生成完毕，即将生成PPT..."}, ensure_ascii=False) + '\n'

    match = re.search(r"(# .*)", outline, flags=re.DOTALL)

    if match:
        result = outline[match.start():]
    else:
        result = outline
    logger.info(f"用户输入的markdown大纲是：{result}")
    content_wrapper = A2AContentClientWrapper(session_id=uuid.uuid4().hex, agent_url=CONTENT_API)
    # 传入不同的参数，使用不同的搜索,可以同时使用多个搜索
    search_engine = ["KnowledgeBaseSearch"]
    # 方便测试，这个已经在知识库中插入了对应的数据
    metadata = {"user_id": id, "search_engine": search_engine, "language": language}
    logger.info(f"aippt_by_id**=====>metadata数据为：{metadata}")
    async for chunk_data in content_wrapper.generate(user_question=result, metadata=metadata):
        logger.info(f"生成正文输出的chunk_data: {chunk_data}")
        if chunk_data["type"] == "text":
            slide = chunk_data["text"]
            yield slide + '\n'


@app.post("/tools/aippt_by_id")
async def aippt_by_id(request: AipptByIDRequest):
    return StreamingResponse(aippt_file_id_streamer(request.id, request.language), media_type="application/json; charset=utf-8")


@app.get("/files/{user_id}")
async def list_user_files(user_id: int):
    """
    列出指定用户的所有文件信息
    """
    personaldb_api_url = os.environ["PERSONAL_DB"]
    url = f"{personaldb_api_url}/files/{user_id}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"Error connecting to personaldb: {exc}")
        except httpx.HTTPStatusError as exc:
            # 转发下游服务的错误
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)


@app.get("/proxy")
async def proxy(request: Request, url: str = Query(..., description="Target absolute URL")):
    """
    透明代理上游资源，转发部分请求头，透传关键响应头，并允许前端同源访问。
    适合图片/音视频等二进制内容。
    """
    HEADERS_TO_FORWARD = {"Range", "User-Agent"}  # 需要时可扩展
    HEADERS_TO_COPY = {
        "Content-Type",
        "Content-Length",
        "Content-Disposition",
        "Accept-Ranges",
        "ETag",
        "Last-Modified",
        "Cache-Control",
        "Expires",
    }
    forward_headers = {}
    for h in HEADERS_TO_FORWARD:
        v = request.headers.get(h)
        if v:
            forward_headers[h] = v

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            upstream = await client.get(url, headers=forward_headers)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Upstream fetch error: {e!s}")

    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail="Upstream error")

    headers = {}
    for h in HEADERS_TO_COPY:
        if h in upstream.headers:
            headers[h] = upstream.headers[h]

    # 允许被前端同源读取
    headers["Access-Control-Allow-Origin"] = "*"
    # 给静态资源加简单缓存（按需调整）
    headers.setdefault("Cache-Control", "public, max-age=86400")

    return StreamingResponse(
        upstream.aiter_bytes(),
        status_code=upstream.status_code,
        headers=headers,
        media_type=upstream.headers.get("Content-Type"),
    )

@app.get("/healthz")
def healthz():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("MAIN_API_PORT", "6800"))
    uvicorn.run(app, host=host, port=port)