"""
图像视觉断言Agent - FastAPI后端服务
"""
import base64
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from ..config import settings
from ..core.doubao_client import DoubaoVisionClient
from ..core.task_manager import TaskManager, TaskStatus, task_manager
from ..models.schemas import (
    AssertionRequest,
    AssertionResult,
    AssertionURLRequest,
    HealthResponse,
    TaskResponse,
    TaskListResponse,
)

# 全局客户端实例
vision_client: Optional[DoubaoVisionClient] = None


def process_task_async(
    task_id: str,
    image_bytes: bytes,
    expectation: str,
    image_format: str,
    expect_image_bytes: Optional[bytes] = None,
    expect_image_format: str = "jpeg",
):
    """在后台线程中处理任务"""
    global vision_client

    task_manager.update_task_status(task_id, TaskStatus.PROCESSING)

    try:
        if vision_client is None:
            raise Exception("视觉客户端未初始化")

        result = vision_client.assert_image(
            image_bytes=image_bytes,
            expectation=expectation,
            image_format=image_format,
            expect_image_bytes=expect_image_bytes,
            expect_image_format=expect_image_format,
        )
        task_manager.update_task_status(task_id, TaskStatus.COMPLETED, result=result)
    except Exception as e:
        task_manager.update_task_status(task_id, TaskStatus.FAILED, error=str(e))


def process_url_task_async(
    task_id: str,
    image_url: str,
    expectation: str,
    expect_image_url: Optional[str] = None,
):
    """在后台线程中处理URL任务"""
    global vision_client

    task_manager.update_task_status(task_id, TaskStatus.PROCESSING)

    try:
        if vision_client is None:
            raise Exception("视觉客户端未初始化")

        result = vision_client.assert_image_url(
            image_url=image_url,
            expectation=expectation,
            expect_image_url=expect_image_url,
        )
        task_manager.update_task_status(task_id, TaskStatus.COMPLETED, result=result)
    except Exception as e:
        task_manager.update_task_status(task_id, TaskStatus.FAILED, error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global vision_client

    # 启动时初始化客户端
    valid, error = settings.validate()
    if valid:
        vision_client = DoubaoVisionClient()
        print("豆包视觉客户端初始化成功")
    else:
        print(f"警告: 配置不完整 - {error}")
        print("请设置环境变量 DOUBAO_API_KEY 和 DOUBAO_MODEL_ENDPOINT")

    yield

    # 关闭时清理
    vision_client = None


app = FastAPI(
    title="图像视觉断言Agent",
    description="""
基于豆包视觉大模型的图像断言服务。

## 功能

- 上传图片并描述预期，返回是否满足预期的断言结果
- 支持上传预期图片（局部图），AI会判断测试图中是否包含该内容
- 支持物品类型匹配和数量匹配
- 返回详细的JSON格式断言结果
- 支持异步处理，不阻塞前端

## 使用示例

1. 文字预期：上传一张图片，预期描述为"这张图里面有一双运动鞋"
2. 图片预期：上传测试图+预期图（局部图），AI会判断测试图中是否包含预期图的内容
    """,
    version="1.1.0",
    lifespan=lifespan,
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件目录
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def get_client() -> DoubaoVisionClient:
    """获取豆包视觉客户端"""
    if vision_client is None:
        raise HTTPException(
            status_code=503,
            detail="服务未正确配置，请检查 DOUBAO_API_KEY 和 DOUBAO_MODEL_ENDPOINT 环境变量",
        )
    return vision_client


@app.get("/", response_class=HTMLResponse, tags=["页面"])
async def index():
    """返回前端页面"""
    html_path = Path(__file__).parent.parent / "static" / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>请创建 static/index.html 文件</h1>")


@app.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """健康检查接口"""
    valid, error = settings.validate()
    return HealthResponse(
        status="healthy" if valid else "degraded",
        config_valid=valid,
        message=error,
    )


# ============ 异步任务接口 ============

@app.post("/assert/async/upload", response_model=TaskResponse, tags=["异步断言"])
async def assert_image_upload_async(
    image: UploadFile = File(..., description="要分析的测试图片文件"),
    expectation: str = Form(default="", description="预期描述（可选，如果提供了预期图片）"),
    expect_image: Optional[UploadFile] = File(default=None, description="预期图片（局部图，可选）"),
):
    """
    异步上传图片进行断言（不阻塞）

    - **image**: 测试图片（必需）
    - **expectation**: 文字预期描述（可选，如果提供了预期图片可以为空）
    - **expect_image**: 预期图片/局部图（可选，用于在测试图中查找匹配内容）

    立即返回任务ID，通过 /task/{task_id} 查询结果
    """
    # 验证：至少需要文字预期或预期图片之一
    has_expect_image = expect_image is not None
    if not expectation and not has_expect_image:
        raise HTTPException(status_code=400, detail="请提供预期描述或预期图片")

    # 验证测试图片类型
    content_type = image.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="测试图片格式无效")

    # 读取测试图片
    image_bytes = await image.read()
    if len(image_bytes) > settings.MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"测试图片大小超过限制（最大 {settings.MAX_IMAGE_SIZE // 1024 // 1024}MB）",
        )

    image_format = content_type.split("/")[-1] if "/" in content_type else "jpeg"

    # 处理预期图片
    expect_image_bytes = None
    expect_image_format = "jpeg"
    expect_image_base64 = None

    if has_expect_image:
        expect_content_type = expect_image.content_type or ""
        if not expect_content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="预期图片格式无效")

        expect_image_bytes = await expect_image.read()
        if len(expect_image_bytes) > settings.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"预期图片大小超过限制（最大 {settings.MAX_IMAGE_SIZE // 1024 // 1024}MB）",
            )

        expect_image_format = expect_content_type.split("/")[-1] if "/" in expect_content_type else "jpeg"
        expect_image_base64 = base64.b64encode(expect_image_bytes).decode("utf-8")

    # 创建任务
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    task = task_manager.create_task(
        expectation=expectation,
        image_data=image_base64,
        image_type="base64",
        image_format=image_format,
        expect_image_data=expect_image_base64,
        expect_image_type="base64" if expect_image_base64 else None,
        expect_image_format=expect_image_format,
    )

    # 在后台线程中处理
    thread = threading.Thread(
        target=process_task_async,
        args=(task.task_id, image_bytes, expectation, image_format, expect_image_bytes, expect_image_format),
    )
    thread.start()

    return TaskResponse(
        task_id=task.task_id,
        status=task.status.value,
        expectation=task.expectation,
        image_data=task.image_data,
        image_type=task.image_type,
        expect_image_data=task.expect_image_data,
        expect_image_type=task.expect_image_type,
        created_at=task.created_at.isoformat(),
    )


@app.post("/assert/async/base64", response_model=TaskResponse, tags=["异步断言"])
async def assert_image_base64_async(request: AssertionRequest):
    """
    异步Base64图片断言（不阻塞）

    支持同时提供测试图片和预期图片的Base64编码

    立即返回任务ID，通过 /task/{task_id} 查询结果
    """
    # 验证
    has_expect_image = request.expect_image_base64 is not None
    if not request.expectation and not has_expect_image:
        raise HTTPException(status_code=400, detail="请提供预期描述或预期图片")

    try:
        image_bytes = base64.b64decode(request.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="测试图片Base64编码无效")

    if len(image_bytes) > settings.MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"测试图片大小超过限制（最大 {settings.MAX_IMAGE_SIZE // 1024 // 1024}MB）",
        )

    # 处理预期图片
    expect_image_bytes = None
    if has_expect_image:
        try:
            expect_image_bytes = base64.b64decode(request.expect_image_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="预期图片Base64编码无效")

        if len(expect_image_bytes) > settings.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"预期图片大小超过限制（最大 {settings.MAX_IMAGE_SIZE // 1024 // 1024}MB）",
            )

    task = task_manager.create_task(
        expectation=request.expectation,
        image_data=request.image_base64,
        image_type="base64",
        image_format=request.image_format,
        expect_image_data=request.expect_image_base64,
        expect_image_type="base64" if has_expect_image else None,
        expect_image_format=request.expect_image_format,
    )

    thread = threading.Thread(
        target=process_task_async,
        args=(task.task_id, image_bytes, request.expectation, request.image_format,
              expect_image_bytes, request.expect_image_format),
    )
    thread.start()

    return TaskResponse(
        task_id=task.task_id,
        status=task.status.value,
        expectation=task.expectation,
        image_data=task.image_data,
        image_type=task.image_type,
        expect_image_data=task.expect_image_data,
        expect_image_type=task.expect_image_type,
        created_at=task.created_at.isoformat(),
    )


@app.post("/assert/async/url", response_model=TaskResponse, tags=["异步断言"])
async def assert_image_url_async(request: AssertionURLRequest):
    """
    异步URL图片断言（不阻塞）

    支持同时提供测试图片URL和预期图片URL

    立即返回任务ID，通过 /task/{task_id} 查询结果
    """
    has_expect_image = request.expect_image_url is not None
    if not request.expectation and not has_expect_image:
        raise HTTPException(status_code=400, detail="请提供预期描述或预期图片URL")

    task = task_manager.create_task(
        expectation=request.expectation,
        image_data=request.image_url,
        image_type="url",
        expect_image_data=request.expect_image_url,
        expect_image_type="url" if has_expect_image else None,
    )

    thread = threading.Thread(
        target=process_url_task_async,
        args=(task.task_id, request.image_url, request.expectation, request.expect_image_url),
    )
    thread.start()

    return TaskResponse(
        task_id=task.task_id,
        status=task.status.value,
        expectation=task.expectation,
        image_data=task.image_data,
        image_type=task.image_type,
        expect_image_data=task.expect_image_data,
        expect_image_type=task.expect_image_type,
        created_at=task.created_at.isoformat(),
    )


@app.get("/task/{task_id}", response_model=TaskResponse, tags=["任务管理"])
async def get_task(task_id: str):
    """获取任务状态和结果"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskResponse(
        task_id=task.task_id,
        status=task.status.value,
        expectation=task.expectation,
        image_data=task.image_data,
        image_type=task.image_type,
        expect_image_data=task.expect_image_data,
        expect_image_type=task.expect_image_type,
        result=task.result,
        error=task.error,
        created_at=task.created_at.isoformat(),
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
    )


@app.get("/tasks", response_model=TaskListResponse, tags=["任务管理"])
async def get_all_tasks(limit: int = 50):
    """获取所有任务列表"""
    tasks = task_manager.get_all_tasks(limit=limit)
    return TaskListResponse(
        tasks=[
            TaskResponse(
                task_id=t.task_id,
                status=t.status.value,
                expectation=t.expectation,
                image_data=t.image_data,
                image_type=t.image_type,
                expect_image_data=t.expect_image_data,
                expect_image_type=t.expect_image_type,
                result=t.result,
                error=t.error,
                created_at=t.created_at.isoformat(),
                completed_at=t.completed_at.isoformat() if t.completed_at else None,
            )
            for t in tasks
        ],
        total=len(tasks),
    )


@app.delete("/tasks", tags=["任务管理"])
async def clear_all_tasks():
    """清空所有任务"""
    task_manager.clear_tasks()
    return {"message": "所有任务已清空"}


# ============ 同步接口（保留兼容） ============

@app.post("/assert/upload", response_model=AssertionResult, tags=["同步断言"])
async def assert_image_upload(
    image: UploadFile = File(..., description="要分析的测试图片文件"),
    expectation: str = Form(default="", description="预期描述"),
    expect_image: Optional[UploadFile] = File(default=None, description="预期图片（局部图，可选）"),
):
    """
    通过文件上传进行图像断言（同步，会阻塞）
    """
    client = get_client()

    has_expect_image = expect_image is not None
    if not expectation and not has_expect_image:
        raise HTTPException(status_code=400, detail="请提供预期描述或预期图片")

    content_type = image.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只支持图片文件")

    image_bytes = await image.read()

    if len(image_bytes) > settings.MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"图片大小超过限制（最大 {settings.MAX_IMAGE_SIZE // 1024 // 1024}MB）",
        )

    image_format = content_type.split("/")[-1] if "/" in content_type else "jpeg"

    # 处理预期图片
    expect_image_bytes = None
    expect_image_format = "jpeg"
    if has_expect_image:
        expect_content_type = expect_image.content_type or ""
        if not expect_content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="预期图片格式无效")

        expect_image_bytes = await expect_image.read()
        expect_image_format = expect_content_type.split("/")[-1] if "/" in expect_content_type else "jpeg"

    try:
        result = client.assert_image(
            image_bytes=image_bytes,
            expectation=expectation,
            image_format=image_format,
            expect_image_bytes=expect_image_bytes,
            expect_image_format=expect_image_format,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图像分析失败: {str(e)}")


@app.post("/assert/base64", response_model=AssertionResult, tags=["同步断言"])
async def assert_image_base64(request: AssertionRequest):
    """通过Base64编码进行图像断言（同步）"""
    client = get_client()

    has_expect_image = request.expect_image_base64 is not None
    if not request.expectation and not has_expect_image:
        raise HTTPException(status_code=400, detail="请提供预期描述或预期图片")

    try:
        image_bytes = base64.b64decode(request.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的Base64编码")

    if len(image_bytes) > settings.MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"图片大小超过限制（最大 {settings.MAX_IMAGE_SIZE // 1024 // 1024}MB）",
        )

    expect_image_bytes = None
    if has_expect_image:
        try:
            expect_image_bytes = base64.b64decode(request.expect_image_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="预期图片Base64编码无效")

    try:
        result = client.assert_image(
            image_bytes=image_bytes,
            expectation=request.expectation,
            image_format=request.image_format,
            expect_image_bytes=expect_image_bytes,
            expect_image_format=request.expect_image_format,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图像分析失败: {str(e)}")


@app.post("/assert/url", response_model=AssertionResult, tags=["同步断言"])
async def assert_image_url(request: AssertionURLRequest):
    """通过图片URL进行图像断言（同步）"""
    client = get_client()

    has_expect_image = request.expect_image_url is not None
    if not request.expectation and not has_expect_image:
        raise HTTPException(status_code=400, detail="请提供预期描述或预期图片URL")

    try:
        result = client.assert_image_url(
            image_url=request.image_url,
            expectation=request.expectation,
            expect_image_url=request.expect_image_url,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图像分析失败: {str(e)}")


@app.get("/schema/result", tags=["Schema"])
async def get_result_schema():
    """获取断言结果的JSON Schema"""
    return AssertionResult.model_json_schema()


@app.get("/schema/request", tags=["Schema"])
async def get_request_schema():
    """获取断言请求的JSON Schema"""
    return {
        "upload": "使用 multipart/form-data 上传图片文件，支持 expect_image 参数上传预期图片",
        "base64": AssertionRequest.model_json_schema(),
        "url": AssertionURLRequest.model_json_schema(),
    }
