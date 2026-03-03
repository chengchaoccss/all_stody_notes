"""
REST API 路由模块。

提供视频关键帧提取的 HTTP 接口。
"""

import logging
import traceback

from fastapi import APIRouter, HTTPException

from app.config import (
    AlgorithmConfig,
    ExtractionMode,
    ExtractionRequest,
    ExtractionResponse,
)
from app.extractor.base import ExtractorFactory
from app.utils.frame_writer import FrameWriter
from app.utils.metadata_writer import MetadataWriter
from app.utils.video_reader import VideoReaderError, validate_video

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/extract-frames", response_model=ExtractionResponse)
async def extract_frames(request: ExtractionRequest) -> ExtractionResponse:
    """
    视频关键帧提取接口。

    根据请求参数选择提取模式和算法，流式处理视频并保存关键帧。

    Args:
        request: 帧提取请求参数

    Returns:
        ExtractionResponse: 提取结果

    Raises:
        HTTPException:
            - 400: 视频文件不存在或无法读取
            - 422: 参数校验失败（由 FastAPI/Pydantic 自动处理）
            - 500: 算法执行异常
    """
    # ===== 1. 视频校验 =====
    try:
        video_info = validate_video(request.video_path)
    except VideoReaderError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ===== 2. 参数校验（algorithm 模式必须指定算法类型） =====
    if request.mode == ExtractionMode.ALGORITHM and request.algorithm_type is None:
        raise HTTPException(
            status_code=400,
            detail="algorithm 模式下必须指定 algorithm_type 参数",
        )

    # ===== 3. 创建提取器 =====
    try:
        extractor = ExtractorFactory.create(
            mode=request.mode,
            algorithm_type=request.algorithm_type,
            algorithm_config=request.algorithm_config,
            time_interval_sec=request.time_interval_sec,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ===== 4. 流式提取并保存 =====
    frame_writer = FrameWriter(output_dir=request.output_dir)
    timestamps: list[float] = []
    frame_count: int = 0

    try:
        for extracted_frame in extractor.extract(video_path=request.video_path):
            frame_count += 1
            timestamps.append(extracted_frame.timestamp_sec)

            # 写入帧图片
            frame_writer.write(
                frame=extracted_frame.frame,
                index=frame_count,
                timestamp_sec=extracted_frame.timestamp_sec,
            )

            # 释放帧数据引用，协助 GC 回收内存
            extracted_frame.frame = None

    except Exception as e:
        logger.error("关键帧提取过程异常: %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"关键帧提取失败: {str(e)}",
        )

    # ===== 5. 写入 metadata.json =====
    metadata_writer = MetadataWriter(output_dir=request.output_dir)
    metadata_writer.write(
        video_path=request.video_path,
        mode=request.mode.value,
        total_frames_extracted=frame_count,
        timestamps=timestamps,
        algorithm=request.algorithm_type.value if request.algorithm_type else None,
        algorithm_config=(
            request.algorithm_config.model_dump()
            if request.algorithm_config
            else None
        ),
        time_interval_sec=(
            request.time_interval_sec
            if request.mode == ExtractionMode.TIME
            else None
        ),
    )

    # ===== 6. 构造响应 =====
    return ExtractionResponse(
        status="success",
        total_frames_extracted=frame_count,
        output_dir=request.output_dir,
        timestamps=timestamps,
    )
