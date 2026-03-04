"""
视频关键帧提取器 —— 本地算法类。

提供统一的 Python API，无需启动 HTTP 服务即可直接调用。
支持四种提取模式：时间采样、帧差法、光流法、场景检测。

典型用法::

    from keyframe_extractor import KeyframeExtractor

    ke = KeyframeExtractor("input.mp4")
    print(ke.video_info)

    result = ke.extract_by_time("output/time", interval_sec=2.0)
    print(result)

    result = ke.extract_by_frame_diff("output/diff", threshold=0.2)
    print(result)
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional

# 确保项目包可被导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import AlgorithmConfig
from app.extractor.base import ExtractedFrame
from app.extractor.frame_diff_extractor import FrameDiffExtractor
from app.extractor.optical_flow_extractor import OpticalFlowExtractor
from app.extractor.scene_detect_extractor import SceneDetectExtractor
from app.extractor.time_extractor import TimeExtractor
from app.utils.frame_writer import FrameWriter
from app.utils.metadata_writer import MetadataWriter
from app.utils.video_reader import VideoInfo, VideoReaderError, validate_video


@dataclass
class ExtractionResult:
    """提取结果。"""
    total_frames: int
    timestamps: list[float]
    output_dir: str
    frame_paths: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"ExtractionResult(total_frames={self.total_frames}, "
            f"output_dir='{self.output_dir}', "
            f"timestamps={self.timestamps})"
        )


class KeyframeExtractor:
    """
    视频关键帧提取器。

    一个视频文件对应一个实例，通过不同方法调用不同提取算法。
    所有算法均为流式处理，内存友好。

    Args:
        video_path: 视频文件路径
        jpeg_quality: 输出 JPEG 质量 (1-100)，默认 95
    """

    def __init__(self, video_path: str, jpeg_quality: int = 95) -> None:
        self._video_path = os.path.abspath(video_path)
        self._jpeg_quality = jpeg_quality
        self._video_info: Optional[VideoInfo] = None

    @property
    def video_info(self) -> VideoInfo:
        """获取视频元信息（首次访问时校验并缓存）。"""
        if self._video_info is None:
            self._video_info = validate_video(self._video_path)
        return self._video_info

    def _run_extraction(
        self,
        extractor,
        output_dir: str,
        mode: str,
        algorithm: Optional[str] = None,
        algorithm_config: Optional[dict] = None,
        time_interval_sec: Optional[float] = None,
    ) -> ExtractionResult:
        """内部通用提取流程。"""
        writer = FrameWriter(output_dir, quality=self._jpeg_quality)
        timestamps: list[float] = []
        frame_paths: list[str] = []
        index = 0

        for extracted_frame in extractor.extract(self._video_path):
            index += 1
            path = writer.write(extracted_frame.frame, index, extracted_frame.timestamp_sec)
            timestamps.append(extracted_frame.timestamp_sec)
            frame_paths.append(path)

        # 写入 metadata.json
        meta_writer = MetadataWriter(output_dir)
        meta_writer.write(
            video_path=self._video_path,
            mode=mode,
            total_frames_extracted=index,
            timestamps=timestamps,
            algorithm=algorithm,
            algorithm_config=algorithm_config,
            time_interval_sec=time_interval_sec,
        )

        return ExtractionResult(
            total_frames=index,
            timestamps=timestamps,
            output_dir=output_dir,
            frame_paths=frame_paths,
        )

    def extract_by_time(
        self,
        output_dir: str,
        interval_sec: float = 1.0,
    ) -> ExtractionResult:
        """
        按固定时间间隔提取关键帧。

        Args:
            output_dir: 输出目录
            interval_sec: 采样间隔（秒），默认 1.0

        Returns:
            ExtractionResult
        """
        extractor = TimeExtractor(interval_sec=interval_sec)
        return self._run_extraction(
            extractor, output_dir,
            mode="time",
            time_interval_sec=interval_sec,
        )

    def extract_by_frame_diff(
        self,
        output_dir: str,
        threshold: float = 0.3,
        min_interval_sec: float = 1.0,
    ) -> ExtractionResult:
        """
        帧差法提取关键帧 —— 检测画面内容突变。

        Args:
            output_dir: 输出目录
            threshold: 差值阈值 (0.0-1.0)，越小越敏感
            min_interval_sec: 最小间隔（秒），防止连续保存

        Returns:
            ExtractionResult
        """
        config = AlgorithmConfig(threshold=threshold, min_interval_sec=min_interval_sec)
        extractor = FrameDiffExtractor(config)
        return self._run_extraction(
            extractor, output_dir,
            mode="algorithm",
            algorithm="frame_diff",
            algorithm_config=config.model_dump(),
        )

    def extract_by_optical_flow(
        self,
        output_dir: str,
        threshold: float = 0.3,
        min_interval_sec: float = 1.0,
    ) -> ExtractionResult:
        """
        光流法提取关键帧 —— 检测运动强度突变。

        Args:
            output_dir: 输出目录
            threshold: 运动强度阈值 (0.0-1.0)，越小越敏感
            min_interval_sec: 最小间隔（秒）

        Returns:
            ExtractionResult
        """
        config = AlgorithmConfig(threshold=threshold, min_interval_sec=min_interval_sec)
        extractor = OpticalFlowExtractor(config)
        return self._run_extraction(
            extractor, output_dir,
            mode="algorithm",
            algorithm="optical_flow",
            algorithm_config=config.model_dump(),
        )

    def extract_by_scene_detect(
        self,
        output_dir: str,
        threshold: float = 0.3,
        min_interval_sec: float = 1.0,
    ) -> ExtractionResult:
        """
        场景检测提取关键帧 —— 基于 HSV 颜色直方图检测场景切换。

        Args:
            output_dir: 输出目录
            threshold: 场景距离阈值 (0.0-1.0)，越小越敏感
            min_interval_sec: 最小间隔（秒）

        Returns:
            ExtractionResult
        """
        config = AlgorithmConfig(threshold=threshold, min_interval_sec=min_interval_sec)
        extractor = SceneDetectExtractor(config)
        return self._run_extraction(
            extractor, output_dir,
            mode="algorithm",
            algorithm="scene_detect",
            algorithm_config=config.model_dump(),
        )
