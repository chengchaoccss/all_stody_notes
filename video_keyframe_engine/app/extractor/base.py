"""
关键帧提取器基类模块。

所有提取算法必须继承 BaseExtractor 并实现 extract 方法。
使用纯 dict 注册表 + 工厂模式创建提取器，扩展新算法无需修改工厂代码。
"""

from abc import ABC, abstractmethod
from typing import Callable, Generator, Optional

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
    def extract(self, video_path: str, **kwargs) -> Generator[ExtractedFrame, None, None]:
        """
        流式提取关键帧。

        Args:
            video_path: 视频文件路径
            **kwargs: 子类特定参数

        Yields:
            ExtractedFrame: 提取的关键帧
        """
        ...


# 算法提取器构造函数签名
AlgorithmExtractorBuilder = Callable[[AlgorithmConfig, bool], BaseExtractor]


class ExtractorFactory:
    """
    提取器工厂。

    使用纯 dict 注册表管理所有算法提取器。
    扩展新算法只需调用 register() 注册，无需修改工厂类本身。

    内置算法在首次使用时通过 _ensure_defaults_registered() 延迟注册，
    避免循环导入。
    """

    _registry: dict[str, AlgorithmExtractorBuilder] = {}
    _defaults_registered: bool = False

    @classmethod
    def _ensure_defaults_registered(cls) -> None:
        """延迟注册内置算法提取器（避免循环导入）。"""
        if cls._defaults_registered:
            return
        cls._defaults_registered = True

        from app.extractor.frame_diff_extractor import FrameDiffExtractor
        from app.extractor.optical_flow_extractor import OpticalFlowExtractor
        from app.extractor.scene_detect_extractor import SceneDetectExtractor

        defaults: dict[str, type[BaseExtractor]] = {
            AlgorithmType.FRAME_DIFF.value: FrameDiffExtractor,
            AlgorithmType.OPTICAL_FLOW.value: OpticalFlowExtractor,
            AlgorithmType.SCENE_DETECT.value: SceneDetectExtractor,
        }
        for key, extractor_cls in defaults.items():
            cls._registry.setdefault(key, extractor_cls)

    @classmethod
    def register(cls, key: str, builder: AlgorithmExtractorBuilder) -> None:
        """
        注册自定义算法提取器。

        后续扩展 AI 语义帧等新算法时，只需：
            ExtractorFactory.register("semantic", SemanticExtractor)

        Args:
            key: 算法标识（与 AlgorithmType 值对应）
            builder: 提取器构造函数，签名为 (config, use_gpu) -> BaseExtractor
        """
        cls._registry[key] = builder

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
            cls._ensure_defaults_registered()

            registry_key = algorithm_type.value
            builder = cls._registry.get(registry_key)
            if builder is None:
                raise ValueError(
                    f"不支持的算法类型: {algorithm_type}，"
                    f"已注册: {list(cls._registry.keys())}"
                )
            return builder(config, use_gpu)

        raise ValueError(f"不支持的提取模式: {mode}")
