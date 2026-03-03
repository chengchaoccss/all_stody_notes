"""
REST API 路由模块。

提供视频关键帧提取的 HTTP 接口，支持同步和异步两种调用方式。
- POST /extract-frames       — 同步提取（阻塞等待结果）
- POST /extract-frames/async — 异步提取（立即返回 task_id）
- GET  /tasks/{task_id}      — 查询异步任务状态和结果
"""

import asyncio
import logging
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, HTTPException

from app.config import (
    AsyncExtractionResponse,
    ExtractionMode,
    ExtractionRequest,
    ExtractionResponse,
    TaskQueryResponse,
    TaskStatus,
)
from app.extractor.base import ExtractorFactory
from app.utils.frame_writer import FrameWriter
from app.utils.metadata_writer import MetadataWriter
from app.utils.video_reader import (
    VideoReaderError,
    validate_path_security,
    validate_video,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ========== 异步任务存储 ==========
# 生产环境应替换为 Redis / 数据库
_task_store: dict[str, dict[str, Any]] = {}

# CPU 密集型任务线程池（避免阻塞事件循环）
_executor = ThreadPoolExecutor(max_workers=4)


def _run_extraction(request: ExtractionRequest) -> ExtractionResponse:
    """
    执行帧提取的同步核心逻辑（在线程池中运行）。

    Args:
        request: 提取请求参数

    Returns:
        ExtractionResponse: 提取结果

    Raises:
        VideoReaderError: 视频校验失败
        ValueError: 参数不合法
        Exception: 算法运行异常
    """
    # 路径安全校验
    validate_path_security(request.video_path, request.output_dir)

    # 视频校验
    validate_video(request.video_path)

    # 创建提取器
    extractor = ExtractorFactory.create(
        mode=request.mode,
        algorithm_type=request.algorithm_type,
        algorithm_config=request.algorithm_config,
        time_interval_sec=request.time_interval_sec,
    )

    # 流式提取并保存
    frame_writer = FrameWriter(output_dir=request.output_dir)
    timestamps: list[float] = []
    frame_count: int = 0

    for extracted_frame in extractor.extract(video_path=request.video_path):
        frame_count += 1
        timestamps.append(extracted_frame.timestamp_sec)
        frame_writer.write(
            frame=extracted_frame.frame,
            index=frame_count,
            timestamp_sec=extracted_frame.timestamp_sec,
        )
        # 释放帧数据引用，协助 GC 回收内存
        extracted_frame.frame = None

    # 写入 metadata.json
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

    return ExtractionResponse(
        status="success",
        total_frames_extracted=frame_count,
        output_dir=request.output_dir,
        timestamps=timestamps,
    )


@router.post("/extract-frames", response_model=ExtractionResponse)
async def extract_frames(request: ExtractionRequest) -> ExtractionResponse:
    """
    同步视频关键帧提取接口。

    通过线程池执行 CPU 密集型提取操作，不阻塞 FastAPI 事件循环。

    Raises:
        HTTPException:
            - 400: 视频文件不存在/路径不安全/参数错误
            - 422: 参数格式校验失败（Pydantic 自动处理）
            - 500: 算法执行异常
    """
    if request.mode == ExtractionMode.ALGORITHM and request.algorithm_type is None:
        raise HTTPException(
            status_code=400,
            detail="algorithm 模式下必须指定 algorithm_type 参数",
        )

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(_executor, _run_extraction, request)
        return result
    except VideoReaderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("关键帧提取过程异常: %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"关键帧提取失败: {str(e)}")


@router.post("/extract-frames/async", response_model=AsyncExtractionResponse)
async def extract_frames_async(request: ExtractionRequest) -> AsyncExtractionResponse:
    """
    异步视频关键帧提取接口。

    立即返回 task_id，提取任务在后台线程池中执行。
    通过 GET /tasks/{task_id} 查询进度和结果。
    """
    if request.mode == ExtractionMode.ALGORITHM and request.algorithm_type is None:
        raise HTTPException(
            status_code=400,
            detail="algorithm 模式下必须指定 algorithm_type 参数",
        )

    # 预校验路径安全和视频合法性（快速失败，避免提交无效任务）
    try:
        validate_path_security(request.video_path, request.output_dir)
        validate_video(request.video_path)
    except VideoReaderError as e:
        raise HTTPException(status_code=400, detail=str(e))

    task_id = uuid.uuid4().hex
    _task_store[task_id] = {"status": TaskStatus.PENDING, "result": None, "error": None}

    # 在后台线程池中启动提取任务
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _background_task, task_id, request)

    return AsyncExtractionResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="任务已提交，请通过 GET /tasks/{task_id} 查询进度",
    )


def _background_task(task_id: str, request: ExtractionRequest) -> None:
    """在后台线程中执行提取任务并更新状态。"""
    _task_store[task_id]["status"] = TaskStatus.RUNNING
    try:
        result = _run_extraction(request)
        _task_store[task_id]["status"] = TaskStatus.COMPLETED
        _task_store[task_id]["result"] = result
    except Exception as e:
        logger.error("异步任务 %s 失败: %s\n%s", task_id, str(e), traceback.format_exc())
        _task_store[task_id]["status"] = TaskStatus.FAILED
        _task_store[task_id]["error"] = str(e)


@router.get("/tasks/{task_id}", response_model=TaskQueryResponse)
async def get_task_status(task_id: str) -> TaskQueryResponse:
    """
    查询异步任务状态。

    Args:
        task_id: 任务 ID

    Returns:
        TaskQueryResponse: 任务当前状态及结果
    """
    task = _task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return TaskQueryResponse(
        task_id=task_id,
        status=task["status"],
        result=task["result"],
        error=task["error"],
    )
