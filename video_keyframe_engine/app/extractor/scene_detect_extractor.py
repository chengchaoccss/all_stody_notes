"""
场景检测关键帧提取器。

使用 HSV 颜色空间的 H+S 通道直方图 + Bhattacharyya 距离检测场景变化。
去掉 V（亮度）通道以降低对光照变化的敏感度，减少误报。
当相邻帧的直方图距离超过阈值时判定为场景切换，输出关键帧。
"""

from typing import Generator

import cv2
import numpy as np

from app.config import AlgorithmConfig
from app.extractor.base import BaseExtractor, ExtractedFrame


class SceneDetectExtractor(BaseExtractor):
    """
    场景检测提取器。

    基于 HSV 颜色空间中 H（色相）+ S（饱和度）通道直方图的
    Bhattacharyya 距离判断场景切换。

    去掉 V（亮度/明度）通道的原因：
    V 通道对光照变化极其敏感，同一场景下仅因曝光、日照变化就会产生
    大幅 V 值波动，导致大量误报。仅用 H+S 通道可聚焦于真正的颜色
    分布变化，大幅提高场景切换检测的准确性。

    Bhattacharyya 距离越大表示两帧差异越大（0 = 完全相同，1 = 完全不同）。

    Attributes:
        config: 算法配置（threshold, min_interval_sec）
    """

    # 直方图仅使用 H+S 通道（索引 0 和 1），不含 V 通道（索引 2）
    _HIST_CHANNELS: list[int] = [0, 1]
    _HIST_BINS: list[int] = [50, 60]
    _HIST_RANGES: list[float] = [0, 180, 0, 256]

    def __init__(self, config: AlgorithmConfig, use_gpu: bool = False) -> None:
        super().__init__(use_gpu=use_gpu)
        self.config = config

    def _compute_histogram(self, frame: np.ndarray) -> np.ndarray:
        """
        计算帧的 HSV 颜色直方图。

        Args:
            frame: BGR 格式帧图像

        Returns:
            归一化后的直方图
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist(
            [hsv],
            self._HIST_CHANNELS,
            None,
            self._HIST_BINS,
            self._HIST_RANGES,
        )
        cv2.normalize(hist, hist)
        return hist

    def extract(self, video_path: str, **kwargs) -> Generator[ExtractedFrame, None, None]:
        """
        基于场景检测流式提取关键帧。

        算法流程：
        1. 逐帧流式读取
        2. 计算当前帧 HSV 直方图
        3. 使用 Bhattacharyya 距离与前一帧直方图比较
        4. 距离超过阈值且满足最小间隔 → 输出关键帧
        5. 第一帧始终作为关键帧

        Args:
            video_path: 视频文件路径

        Yields:
            ExtractedFrame: 提取的关键帧
        """
        cap = cv2.VideoCapture(video_path)
        try:
            fps: float = cap.get(cv2.CAP_PROP_FPS)
            min_interval_frames: int = int(self.config.min_interval_sec * fps) if fps > 0 else 0

            prev_hist: np.ndarray | None = None
            last_keyframe_index: int = -min_interval_frames
            frame_index: int = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # 性能优化：缩放后计算直方图
                h, w = frame.shape[:2]
                if h > 720:
                    scale = 540.0 / h
                    small_frame = cv2.resize(frame, None, fx=scale, fy=scale)
                else:
                    small_frame = frame

                curr_hist = self._compute_histogram(small_frame)

                if prev_hist is None:
                    # 第一帧始终保存
                    timestamp = frame_index / fps if fps > 0 else 0.0
                    yield ExtractedFrame(
                        frame=frame,
                        timestamp_sec=round(timestamp, 3),
                        frame_index=frame_index,
                    )
                    last_keyframe_index = frame_index
                    prev_hist = curr_hist
                    frame_index += 1
                    continue

                # Bhattacharyya 距离：0 = 相同，1 = 完全不同
                distance: float = cv2.compareHist(
                    prev_hist, curr_hist, cv2.HISTCMP_BHATTACHARYYA
                )

                if distance >= self.config.threshold:
                    if (frame_index - last_keyframe_index) >= min_interval_frames:
                        timestamp = frame_index / fps if fps > 0 else 0.0
                        yield ExtractedFrame(
                            frame=frame,
                            timestamp_sec=round(timestamp, 3),
                            frame_index=frame_index,
                        )
                        last_keyframe_index = frame_index

                prev_hist = curr_hist
                frame_index += 1
        finally:
            cap.release()
