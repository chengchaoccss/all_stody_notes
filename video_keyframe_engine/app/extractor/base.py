"""
关键帧提取器基类模块。

所有提取算法必须继承 BaseExtractor 并实现 extract 方法。
支持工厂模式创建具体提取器实例。
"""

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

from app.config import AlgorithmConfig, AlgorithmType, ExtractionMode


class ExtractedFrame:
    """
    提取的关键帧数据容器。

    Attributes:
        frame: 帧图像数据（numpy 数组）
        timestamp_sec: 帧对应的时间戳（秒）
        frame_index: 帧在视频中的序号
    """

    __slots__ = ("frame", "timestamp_sec", "frame_index")

    def __init__(self, frame: np.ndarray, timestamp_sec: float, frame_index: int) -> None:
        self.frame = frame
        self.timestamp_sec = timestamp_sec
        self.frame_index = frame_index


class BaseExtractor(ABC):
    """
    关键帧提取器抽象基类。

    所有提取算法需实现 extract 生成器方法，以流式方式逐帧产出关键帧，
    避免一次性加载全部帧到内存。

    预留接口：
        - use_gpu: 是否启用 GPU 加速（当前默认 False）
    """

    def __init__(self, use_gpu: bool = False) -> None:
        self.use_gpu = use_gpu

    @abstractmethod
    def extract(self, video_path: str, **kwargs) -> "Generator[ExtractedFrame, None, None]":
        """
        流式提取关键帧。

        Args:
            video_path: 视频文件路径
            **kwargs: 子类特定参数

        Yields:
            ExtractedFrame: 提取的关键帧
        """
        ...


class ExtractorFactory:
    """
    提取器工厂。

    根据模式和算法类型创建对应的提取器实例。
    支持注册自定义提取器以实现扩展（如 AI 语义关键帧）。
    """

    _registry: dict[str, type[BaseExtractor]] = {}

    @classmethod
    def register(cls, key: str, extractor_cls: type[BaseExtractor]) -> None:
        """注册自定义提取器。"""
        cls._registry[key] = extractor_cls

    @classmethod
    def create(
        cls,
        mode: ExtractionMode,
        algorithm_type: Optional[AlgorithmType] = None,
        algorithm_config: Optional[AlgorithmConfig] = None,
        time_interval_sec: float = 1.0,
        use_gpu: bool = False,
    ) -> BaseExtractor:
        """
        根据模式和算法类型创建提取器。

        Args:
            mode: 提取模式
            algorithm_type: 算法类型（仅 algorithm 模式需要）
            algorithm_config: 算法配置
            time_interval_sec: 时间采样间隔（仅 time 模式需要）
            use_gpu: 是否启用 GPU 加速

        Returns:
            具体的 BaseExtractor 实例

        Raises:
            ValueError: 参数不合法时抛出
        """
        if mode == ExtractionMode.TIME:
            from app.extractor.time_extractor import TimeExtractor
            return TimeExtractor(interval_sec=time_interval_sec, use_gpu=use_gpu)

        if mode == ExtractionMode.ALGORITHM:
            if algorithm_type is None:
                raise ValueError("algorithm 模式下必须指定 algorithm_type")

            config = algorithm_config or AlgorithmConfig()

            # 优先从注册表查找（支持扩展）
            registry_key = algorithm_type.value
            if registry_key in cls._registry:
                return cls._registry[registry_key](config=config, use_gpu=use_gpu)

            if algorithm_type == AlgorithmType.FRAME_DIFF:
                from app.extractor.frame_diff_extractor import FrameDiffExtractor
                return FrameDiffExtractor(config=config, use_gpu=use_gpu)

            if algorithm_type == AlgorithmType.OPTICAL_FLOW:
                from app.extractor.optical_flow_extractor import OpticalFlowExtractor
                return OpticalFlowExtractor(config=config, use_gpu=use_gpu)

            if algorithm_type == AlgorithmType.SCENE_DETECT:
                from app.extractor.scene_detect_extractor import SceneDetectExtractor
                return SceneDetectExtractor(config=config, use_gpu=use_gpu)

            raise ValueError(f"不支持的算法类型: {algorithm_type}")

        raise ValueError(f"不支持的提取模式: {mode}")
