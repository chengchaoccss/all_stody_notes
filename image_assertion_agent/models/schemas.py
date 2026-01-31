"""
数据模型定义 - 使用Pydantic定义请求和响应的JSON Schema
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class ObjectDetail(BaseModel):
    """检测到的物品详情"""

    name: str = Field(..., description="物品名称")
    quantity: int = Field(..., ge=0, description="物品数量")
    confidence: float = Field(..., ge=0.0, le=1.0, description="检测置信度")
    description: str = Field(default="", description="物品详细描述")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "运动鞋",
                "quantity": 2,
                "confidence": 0.95,
                "description": "白色Nike运动鞋，Air Jordan系列",
            }
        }


class AssertionResult(BaseModel):
    """图像断言结果"""

    assertion_passed: bool = Field(..., description="断言是否通过（预期是否完全满足）")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="整体判断的置信度，0.0-1.0之间"
    )
    expected_description: str = Field(..., description="用户的预期描述")
    actual_description: str = Field(..., description="图片中实际看到的内容描述")
    object_match: bool = Field(..., description="物品类型是否匹配")
    quantity_match: bool = Field(..., description="数量是否匹配")
    expected_quantity: Optional[int] = Field(
        default=None, description="预期数量（如果用户指定了）"
    )
    actual_quantity: Optional[int] = Field(
        default=None, description="实际检测到的数量"
    )
    detected_objects: List[ObjectDetail] = Field(
        default_factory=list, description="检测到的物品列表"
    )
    reason: str = Field(..., description="判断理由的详细说明")

    class Config:
        json_schema_extra = {
            "example": {
                "assertion_passed": True,
                "confidence": 0.92,
                "expected_description": "这张图里面有一双运动鞋",
                "actual_description": "图片中可以看到一双白色的Nike运动鞋，放置在木地板上",
                "object_match": True,
                "quantity_match": True,
                "expected_quantity": 2,
                "actual_quantity": 2,
                "detected_objects": [
                    {
                        "name": "运动鞋",
                        "quantity": 2,
                        "confidence": 0.95,
                        "description": "白色Nike运动鞋",
                    }
                ],
                "reason": "图片中确实存在一双（两只）运动鞋，物品类型和数量均符合预期",
            }
        }


class AssertionRequest(BaseModel):
    """断言请求（通过base64上传图片）"""

    image_base64: str = Field(..., description="图片的Base64编码")
    expectation: str = Field(
        ..., min_length=1, description="预期描述，如'这张图里面有一双运动鞋'"
    )
    image_format: str = Field(
        default="jpeg", description="图片格式，如 jpeg, png, webp"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "image_base64": "/9j/4AAQSkZJRg...",
                "expectation": "这张图里面有一双运动鞋",
                "image_format": "jpeg",
            }
        }


class AssertionURLRequest(BaseModel):
    """断言请求（通过URL）"""

    image_url: str = Field(..., description="图片URL地址")
    expectation: str = Field(
        ..., min_length=1, description="预期描述，如'这张图里面有一双运动鞋'"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "image_url": "https://example.com/shoes.jpg",
                "expectation": "这张图里面有一双运动鞋",
            }
        }


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(..., description="服务状态")
    config_valid: bool = Field(..., description="配置是否有效")
    message: Optional[str] = Field(default=None, description="额外信息")


class TaskResponse(BaseModel):
    """任务响应"""

    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态: pending, processing, completed, failed")
    expectation: str = Field(..., description="预期描述")
    image_data: Optional[str] = Field(default=None, description="图片数据(base64或URL)")
    image_type: str = Field(default="base64", description="图片类型: base64 或 url")
    result: Optional[AssertionResult] = Field(default=None, description="断言结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    created_at: str = Field(..., description="创建时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")


class TaskListResponse(BaseModel):
    """任务列表响应"""

    tasks: List[TaskResponse] = Field(default_factory=list, description="任务列表")
    total: int = Field(..., description="总数")
