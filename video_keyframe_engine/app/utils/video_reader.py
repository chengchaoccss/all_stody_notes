"""
视频读取与校验工具模块。

提供视频文件的存在性校验、格式校验、元信息读取等功能。
"""

import os
from dataclasses import dataclass

import cv2

from app.config import MAX_VIDEO_DURATION_SEC, SUPPORTED_VIDEO_EXTENSIONS


@dataclass(frozen=True)
class VideoInfo:
    """
    视频元信息数据类。

    Attributes:
        path: 视频文件绝对路径
        fps: 帧率
        total_frames: 总帧数
        width: 视频宽度（像素）
        height: 视频高度（像素）
        duration_sec: 视频时长（秒）
        codec: 编码格式
    """
    path: str
    fps: float
    total_frames: int
    width: int
    height: int
    duration_sec: float
    codec: str


class VideoReaderError(Exception):
    """视频读取异常。"""
    pass


def validate_video(video_path: str) -> VideoInfo:
    """
    校验视频文件并返回元信息。

    校验内容：
    1. 文件是否存在
    2. 文件扩展名是否支持
    3. 文件是否可以被 OpenCV 打开
    4. 视频时长是否超过限制

    Args:
        video_path: 视频文件路径

    Returns:
        VideoInfo: 视频元信息

    Raises:
        VideoReaderError: 校验失败时抛出
    """
    # 检查文件存在性
    if not os.path.isfile(video_path):
        raise VideoReaderError(f"视频文件不存在: {video_path}")

    # 检查扩展名
    _, ext = os.path.splitext(video_path)
    if ext.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
        raise VideoReaderError(
            f"不支持的视频格式: {ext}，支持的格式: {SUPPORTED_VIDEO_EXTENSIONS}"
        )

    # 尝试打开视频
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise VideoReaderError(f"无法打开视频文件: {video_path}")

    try:
        fps: float = cap.get(cv2.CAP_PROP_FPS)
        total_frames: int = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width: int = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height: int = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 获取编码格式
        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])

        # 计算时长
        duration_sec: float = total_frames / fps if fps > 0 else 0.0

        # 检查时长限制
        if duration_sec > MAX_VIDEO_DURATION_SEC:
            raise VideoReaderError(
                f"视频时长 {duration_sec:.1f}s 超过最大限制 {MAX_VIDEO_DURATION_SEC}s"
            )

        # 视频过短自动降级警告（不抛异常，让调用方处理）
        if duration_sec < 1.0 and total_frames < 2:
            raise VideoReaderError(
                f"视频过短（{duration_sec:.3f}s, {total_frames} 帧），无法有效提取关键帧"
            )

        return VideoInfo(
            path=os.path.abspath(video_path),
            fps=fps,
            total_frames=total_frames,
            width=width,
            height=height,
            duration_sec=round(duration_sec, 3),
            codec=codec,
        )
    finally:
        cap.release()
