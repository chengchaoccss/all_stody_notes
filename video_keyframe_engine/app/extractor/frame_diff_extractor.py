"""
帧差法关键帧提取器。

通过计算相邻帧灰度图的差值均值，当差值超过阈值时判定为关键帧。
支持 min_interval_sec 参数防止爆发式保存。
"""

from typing import Generator

import cv2
import numpy as np

from app.config import AlgorithmConfig
from app.extractor.base import BaseExtractor, ExtractedFrame


class FrameDiffExtractor(BaseExtractor):
    """
    帧差法提取器。

    逐帧流式读取视频，计算相邻帧灰度差值均值。
    差值归一化到 [0, 1] 区间后与阈值比较。

    Attributes:
        config: 算法配置（threshold, min_interval_sec）
    """

    def __init__(self, config: AlgorithmConfig, use_gpu: bool = False) -> None:
        super().__init__(use_gpu=use_gpu)
        self.config = config

    def extract(self, video_path: str, **kwargs) -> Generator[ExtractedFrame, None, None]:
        """
        基于帧差法流式提取关键帧。

        算法流程：
        1. 逐帧读取视频（流式，不缓存全部帧）
        2. 将当前帧转为灰度图
        3. 计算与前一帧灰度差的均值，归一化到 [0, 1]
        4. 差值超过阈值且距上一关键帧满足最小间隔 → 输出关键帧
        5. 第一帧始终作为关键帧输出

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
            last_keyframe_index: int = -min_interval_frames  # 确保第一帧可输出
            frame_index: int = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                if prev_gray is None:
                    # 第一帧始终保存
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

                # 计算帧差均值，归一化到 [0, 1]
                diff = cv2.absdiff(gray, prev_gray)
                diff_score: float = float(np.mean(diff)) / 255.0

                # 判断是否为关键帧
                if diff_score >= self.config.threshold:
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
