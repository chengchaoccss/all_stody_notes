"""
全局配置模块。

定义项目运行所需的默认参数、约束和枚举类型。
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ExtractionMode(str, Enum):
    """帧提取模式枚举。"""
    TIME = "time"
    ALGORITHM = "algorithm"


class AlgorithmType(str, Enum):
    """算法类型枚举。"""
    FRAME_DIFF = "frame_diff"
    OPTICAL_FLOW = "optical_flow"
    SCENE_DETECT = "scene_detect"


class AlgorithmConfig(BaseModel):
    """算法配置参数。"""
    threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="算法触发阈值")
    min_interval_sec: float = Field(default=1.0, ge=0.0, description="最小帧间隔（秒），防止爆发式保存")


class ExtractionRequest(BaseModel):
    """帧提取请求参数模型。"""
    video_path: str = Field(..., description="输入视频文件路径")
    mode: ExtractionMode = Field(..., description="提取模式：time 或 algorithm")
    output_dir: str = Field(..., description="输出目录路径")
    time_interval_sec: float = Field(default=1.0, gt=0.0, description="时间采样间隔（秒），仅 time 模式有效")
    algorithm_type: Optional[AlgorithmType] = Field(default=None, description="算法类型，仅 algorithm 模式有效")
    algorithm_config: Optional[AlgorithmConfig] = Field(default=None, description="算法参数配置")


class ExtractionResponse(BaseModel):
    """帧提取同步响应模型。"""
    status: str = Field(default="success", description="处理状态")
    total_frames_extracted: int = Field(..., description="提取的关键帧总数")
    output_dir: str = Field(..., description="输出目录路径")
    timestamps: list[float] = Field(default_factory=list, description="关键帧时间戳列表（秒）")


class TaskStatus(str, Enum):
    """异步任务状态枚举。"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AsyncExtractionResponse(BaseModel):
    """异步提取任务提交响应。"""
    task_id: str = Field(..., description="任务 ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    message: str = Field(default="任务已提交", description="状态描述")


class TaskQueryResponse(BaseModel):
    """任务状态查询响应。"""
    task_id: str = Field(..., description="任务 ID")
    status: TaskStatus = Field(..., description="当前状态")
    result: Optional[ExtractionResponse] = Field(default=None, description="完成后的提取结果")
    error: Optional[str] = Field(default=None, description="失败时的错误信息")


# ========== 全局约束 ==========
MAX_VIDEO_DURATION_SEC: int = 600  # 单视频最长 10 分钟
SUPPORTED_VIDEO_EXTENSIONS: set[str] = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm"}
DEFAULT_FRAME_QUALITY: int = 95  # JPEG 输出质量

# ========== 路径安全 ==========
# 允许访问的视频文件根目录白名单（为空则不限制）
# 生产环境中应配置为具体目录，如 ["/data/videos", "/mnt/media"]
import os as _os
ALLOWED_VIDEO_DIRS: list[str] = _os.environ.get(
    "VKE_ALLOWED_VIDEO_DIRS", ""
).split(":") if _os.environ.get("VKE_ALLOWED_VIDEO_DIRS") else []
ALLOWED_OUTPUT_DIRS: list[str] = _os.environ.get(
    "VKE_ALLOWED_OUTPUT_DIRS", ""
).split(":") if _os.environ.get("VKE_ALLOWED_OUTPUT_DIRS") else []
