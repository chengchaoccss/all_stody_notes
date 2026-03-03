"""
光流法关键帧提取器。

使用 Farneback 密集光流计算相邻帧之间的运动强度。
当运动强度超过阈值时判定为关键帧。
"""

from typing import Generator

import cv2
import numpy as np

from app.config import AlgorithmConfig
from app.extractor.base import BaseExtractor, ExtractedFrame


class OpticalFlowExtractor(BaseExtractor):
    """
    光流法提取器。

    使用 cv2.calcOpticalFlowFarneback 计算密集光流场，
    通过光流向量的平均幅值衡量运动强度。

    Attributes:
        config: 算法配置（threshold, min_interval_sec）
    """

    # Farneback 光流参数
    _FARNEBACK_PARAMS: dict = {
        "pyr_scale": 0.5,
        "levels": 3,
        "winsize": 15,
        "iterations": 3,
        "poly_n": 5,
        "poly_sigma": 1.2,
        "flags": 0,
    }

    def __init__(self, config: AlgorithmConfig, use_gpu: bool = False) -> None:
        super().__init__(use_gpu=use_gpu)
        self.config = config

    def _compute_flow_magnitude(self, prev_gray: np.ndarray, curr_gray: np.ndarray) -> float:
        """
        计算两帧之间光流的平均运动幅值。

        Args:
            prev_gray: 前一帧灰度图
            curr_gray: 当前帧灰度图

        Returns:
            归一化后的运动强度值 [0, 1]
        """
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray,
            curr_gray,
            None,
            **self._FARNEBACK_PARAMS,
        )
        # 计算光流向量幅值
        magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        mean_magnitude: float = float(np.mean(magnitude))

        # 归一化：经验值，通常像素级运动幅值在 0~50 范围内
        normalized: float = min(mean_magnitude / 50.0, 1.0)
        return normalized

    def extract(self, video_path: str, **kwargs) -> Generator[ExtractedFrame, None, None]:
        """
        基于光流法流式提取关键帧。

        算法流程：
        1. 逐帧流式读取
        2. 计算当前帧与前一帧的 Farneback 光流
        3. 运动强度超过阈值且满足最小间隔 → 输出关键帧
        4. 第一帧始终作为关键帧

        对于 1080p 视频，会先缩放到 540p 进行光流计算以提升性能。

        Args:
            video_path: 视频文件路径

        Yields:
            ExtractedFrame: 提取的关键帧
        """
        cap = cv2.VideoCapture(video_path)
        try:
            fps: float = cap.get(cv2.CAP_PROP_FPS)
            min_interval_frames: int = int(self.config.min_interval_sec * fps) if fps > 0 else 0

            prev_gray: np.ndarray | None = None
            last_keyframe_index: int = -min_interval_frames
            frame_index: int = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # 性能优化：对大尺寸帧缩放后再计算光流
                h, w = frame.shape[:2]
                scale_factor = 1.0
                if h > 720:
                    scale_factor = 540.0 / h
                    small_frame = cv2.resize(frame, None, fx=scale_factor, fy=scale_factor)
                else:
                    small_frame = frame

                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)

                if prev_gray is None:
                    timestamp = frame_index / fps if fps > 0 else 0.0
                    yield ExtractedFrame(
                        frame=frame,
                        timestamp_sec=round(timestamp, 3),
                        frame_index=frame_index,
                    )
                    last_keyframe_index = frame_index
                    prev_gray = gray
                    frame_index += 1
                    continue

                # 计算光流运动强度
                motion_score = self._compute_flow_magnitude(prev_gray, gray)

                if motion_score >= self.config.threshold:
                    if (frame_index - last_keyframe_index) >= min_interval_frames:
                        timestamp = frame_index / fps if fps > 0 else 0.0
                        yield ExtractedFrame(
                            frame=frame,
                            timestamp_sec=round(timestamp, 3),
                            frame_index=frame_index,
                        )
                        last_keyframe_index = frame_index

                prev_gray = gray
                frame_index += 1
        finally:
            cap.release()
