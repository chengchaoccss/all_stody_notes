"""
图像视觉断言Agent - 基于豆包视觉大模型的图像断言服务
"""
from .api.main import app
from .config import settings
from .core.doubao_client import DoubaoVisionClient
from .models.schemas import AssertionResult, ObjectDetail

__version__ = "1.0.0"
__all__ = ["app", "settings", "DoubaoVisionClient", "AssertionResult", "ObjectDetail"]
