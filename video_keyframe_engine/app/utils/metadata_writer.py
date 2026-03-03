"""
元数据写入模块。

将关键帧提取结果的元信息保存为 metadata.json 文件。
"""

import json
import os
from typing import Optional


class MetadataWriter:
    """
    元数据 JSON 写入器。

    在输出目录中生成 metadata.json 文件，记录提取过程的完整信息。
    """

    def __init__(self, output_dir: str) -> None:
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def write(
        self,
        video_path: str,
        mode: str,
        total_frames_extracted: int,
        timestamps: list[float],
        algorithm: Optional[str] = None,
        algorithm_config: Optional[dict] = None,
        time_interval_sec: Optional[float] = None,
    ) -> str:
        """
        写入 metadata.json 文件。

        Args:
            video_path: 源视频路径
            mode: 提取模式
            total_frames_extracted: 提取的关键帧总数
            timestamps: 关键帧时间戳列表
            algorithm: 算法类型名称（algorithm 模式下）
            algorithm_config: 算法配置参数（algorithm 模式下）
            time_interval_sec: 时间采样间隔（time 模式下）

        Returns:
            metadata.json 文件路径
        """
        metadata: dict = {
            "video_path": video_path,
            "mode": mode,
            "total_frames_extracted": total_frames_extracted,
            "timestamps": timestamps,
        }

        if algorithm is not None:
            metadata["algorithm"] = algorithm

        if algorithm_config is not None:
            metadata["algorithm_config"] = algorithm_config

        if time_interval_sec is not None:
            metadata["time_interval_sec"] = time_interval_sec

        filepath = os.path.join(self.output_dir, "metadata.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return filepath
