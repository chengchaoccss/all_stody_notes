"""
图像视觉断言Agent - FastAPI后端服务
"""
import base64
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings
from ..core.doubao_client import DoubaoVisionClient
from ..models.schemas import (
    AssertionRequest,
    AssertionResult,
    AssertionURLRequest,
    HealthResponse,
)

# 全局客户端实例
vision_client: Optional[DoubaoVisionClient] = None


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
- 支持物品类型匹配和数量匹配
- 返回详细的JSON格式断言结果

## 使用示例

上传一张运动鞋的图片，预期描述为"这张图里面有一双运动鞋"，
服务会返回断言结果，包括物品是否匹配、数量是否正确等信息。
    """,
    version="1.0.0",
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


def get_client() -> DoubaoVisionClient:
    """获取豆包视觉客户端"""
    if vision_client is None:
        raise HTTPException(
            status_code=503,
            detail="服务未正确配置，请检查 DOUBAO_API_KEY 和 DOUBAO_MODEL_ENDPOINT 环境变量",
        )
    return vision_client


@app.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """健康检查接口"""
    valid, error = settings.validate()
    return HealthResponse(
        status="healthy" if valid else "degraded",
        config_valid=valid,
        message=error,
    )


@app.post("/assert/upload", response_model=AssertionResult, tags=["断言"])
async def assert_image_upload(
    image: UploadFile = File(..., description="要分析的图片文件"),
    expectation: str = Form(..., description="预期描述，如'这张图里面有一双运动鞋'"),
):
    """
    通过文件上传进行图像断言

    上传一张图片并提供预期描述，返回断言结果。

    - **image**: 图片文件（支持 jpeg, png, webp 等格式）
    - **expectation**: 预期描述，如"这张图里面有一双运动鞋"
    """
    client = get_client()

    # 验证文件类型
    content_type = image.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只支持图片文件")

    # 读取图片内容
    image_bytes = await image.read()

    # 验证文件大小
    if len(image_bytes) > settings.MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"图片大小超过限制（最大 {settings.MAX_IMAGE_SIZE // 1024 // 1024}MB）",
        )

    # 获取图片格式
    image_format = content_type.split("/")[-1] if "/" in content_type else "jpeg"

    try:
        result = client.assert_image(
            image_bytes=image_bytes,
            expectation=expectation,
            image_format=image_format,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图像分析失败: {str(e)}")


@app.post("/assert/base64", response_model=AssertionResult, tags=["断言"])
async def assert_image_base64(request: AssertionRequest):
    """
    通过Base64编码进行图像断言

    提供图片的Base64编码和预期描述，返回断言结果。

    - **image_base64**: 图片的Base64编码字符串
    - **expectation**: 预期描述，如"这张图里面有一双运动鞋"
    - **image_format**: 图片格式，默认为 jpeg
    """
    client = get_client()

    try:
        # 解码Base64
        image_bytes = base64.b64decode(request.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的Base64编码")

    # 验证文件大小
    if len(image_bytes) > settings.MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"图片大小超过限制（最大 {settings.MAX_IMAGE_SIZE // 1024 // 1024}MB）",
        )

    try:
        result = client.assert_image(
            image_bytes=image_bytes,
            expectation=request.expectation,
            image_format=request.image_format,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图像分析失败: {str(e)}")


@app.post("/assert/url", response_model=AssertionResult, tags=["断言"])
async def assert_image_url(request: AssertionURLRequest):
    """
    通过图片URL进行图像断言

    提供图片URL和预期描述，返回断言结果。

    - **image_url**: 图片的URL地址
    - **expectation**: 预期描述，如"这张图里面有一双运动鞋"
    """
    client = get_client()

    try:
        result = client.assert_image_url(
            image_url=request.image_url,
            expectation=request.expectation,
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
        "upload": "使用 multipart/form-data 上传图片文件",
        "base64": AssertionRequest.model_json_schema(),
        "url": AssertionURLRequest.model_json_schema(),
    }
