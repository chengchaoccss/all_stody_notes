"""
时间采样关键帧提取器。

根据指定的时间间隔，精准跳转到对应帧位置进行采样。
不逐帧遍历，使用 cv2.CAP_PROP_POS_MSEC 精准定位。
"""

from typing import Generator

import cv2
import numpy as np

from app.extractor.base import BaseExtractor, ExtractedFrame


class TimeExtractor(BaseExtractor):
    """
    时间采样提取器。

    按固定时间间隔跳转并提取帧，不做逐帧遍历。

    Attributes:
        interval_sec: 采样间隔（秒）
    """

    def __init__(self, interval_sec: float = 1.0, use_gpu: bool = False) -> None:
        super().__init__(use_gpu=use_gpu)
        self.interval_sec = interval_sec

    def extract(self, video_path: str, **kwargs) -> Generator[ExtractedFrame, None, None]:
        """
        按时间间隔提取关键帧。

        通过 CAP_PROP_POS_MSEC 精准跳转到目标时间点，
        避免暴力逐帧读取，提升大视频处理效率。

        Args:
            video_path: 视频文件路径

        Yields:
            ExtractedFrame: 提取的关键帧
        """
        cap = cv2.VideoCapture(video_path)
        try:
            fps: float = cap.get(cv2.CAP_PROP_FPS)
            total_frames: int = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration_sec: float = total_frames / fps if fps > 0 else 0.0

            current_time: float = 0.0
            frame_counter: int = 0

            while current_time < duration_sec:
                # 精准跳转到目标时间位置（毫秒）
                cap.set(cv2.CAP_PROP_POS_MSEC, current_time * 1000.0)
                ret, frame = cap.read()
                if not ret:
                    break

                frame_index = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
                yield ExtractedFrame(
                    frame=frame,
                    timestamp_sec=round(current_time, 3),
                    frame_index=max(frame_index, 0),
                )

                frame_counter += 1
                current_time += self.interval_sec
        finally:
            cap.release()
