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
    """帧提取响应模型。"""
    status: str = Field(default="success", description="处理状态")
    total_frames_extracted: int = Field(..., description="提取的关键帧总数")
    output_dir: str = Field(..., description="输出目录路径")
    timestamps: list[float] = Field(default_factory=list, description="关键帧时间戳列表（秒）")


# ========== 全局约束 ==========
MAX_VIDEO_DURATION_SEC: int = 600  # 单视频最长 10 分钟
SUPPORTED_VIDEO_EXTENSIONS: set[str] = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm"}
DEFAULT_FRAME_QUALITY: int = 95  # JPEG 输出质量
