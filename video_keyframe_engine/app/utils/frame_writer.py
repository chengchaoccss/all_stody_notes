"""
关键帧图片写入模块。

将提取的关键帧保存为 JPEG 图片文件。
文件命名格式：frame_NNNN_tNNNNNNms.jpg（毫秒精度，无歧义）
"""

import os

import cv2
import numpy as np

from app.config import DEFAULT_FRAME_QUALITY


class FrameWriter:
    """
    关键帧图片写入器。

    负责将帧数据保存到指定输出目录的 frames 子目录中。

    Attributes:
        output_dir: 输出根目录
        frames_dir: 帧图片保存目录
        quality: JPEG 压缩质量
    """

    def __init__(self, output_dir: str, quality: int = DEFAULT_FRAME_QUALITY) -> None:
        self.output_dir = output_dir
        self.frames_dir = os.path.join(output_dir, "frames")
        self.quality = quality

        # 确保目录存在
        os.makedirs(self.frames_dir, exist_ok=True)

    def write(self, frame: np.ndarray, index: int, timestamp_sec: float) -> str:
        """
        将帧保存为 JPEG 图片。

        文件命名规则：frame_NNNN_tNNNNNNms.jpg
        例如：frame_0001_t000230ms.jpg（表示 0.230 秒）

        毫秒精度命名避免了浮点数小数点在文件名中造成的歧义。

        Args:
            frame: 帧图像数据（BGR numpy 数组）
            index: 关键帧序号（从 1 开始）
            timestamp_sec: 帧时间戳（秒）

        Returns:
            保存的文件路径
        """
        timestamp_ms = int(round(timestamp_sec * 1000))
        filename = f"frame_{index:04d}_t{timestamp_ms:06d}ms.jpg"
        filepath = os.path.join(self.frames_dir, filename)

        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.quality]
        cv2.imwrite(filepath, frame, encode_params)

        return filepath
