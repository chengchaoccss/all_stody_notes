"""
异步任务管理器 - 管理图像断言任务的异步执行
支持SQLite持久化存储和完整日志记录
"""
import base64
import threading
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

from ..models.schemas import AssertionResult
from .database import db
from .logger import logger, set_trace_id


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"      # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"        # 失败


class AssertionTask:
    """断言任务"""

    def __init__(
        self,
        task_id: str,
        expectation: str,
        image_data: Optional[str] = None,  # base64或URL
        image_type: str = "base64",  # base64 或 url
        image_format: str = "jpeg",
        expect_image_data: Optional[str] = None,  # 预期图片 base64或URL
        expect_image_type: Optional[str] = None,  # 预期图片类型
        expect_image_format: str = "jpeg",
    ):
        self.task_id = task_id
        self.expectation = expectation
        self.image_data = image_data
        self.image_type = image_type
        self.image_format = image_format
        self.expect_image_data = expect_image_data
        self.expect_image_type = expect_image_type
        self.expect_image_format = expect_image_format
        self.status = TaskStatus.PENDING
        self.result: Optional[AssertionResult] = None
        self.error: Optional[str] = None
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.duration_ms: Optional[float] = None
        self.retry_count: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "expectation": self.expectation,
            "image_data": self.image_data,
            "image_type": self.image_type,
            "expect_image_data": self.expect_image_data,
            "expect_image_type": self.expect_image_type,
            "status": self.status.value,
            "result": self.result.model_dump() if self.result else None,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_db_dict(cls, data: dict) -> "AssertionTask":
        """从数据库字典创建任务对象"""
        task = cls(
            task_id=data["task_id"],
            expectation=data.get("expectation", ""),
            image_data=data.get("image_data"),
            image_type=data.get("image_type", "base64"),
            expect_image_data=data.get("expect_image_data"),
            expect_image_type=data.get("expect_image_type"),
        )
        task.status = TaskStatus(data.get("status", "pending"))
        task.error = data.get("error")
        task.duration_ms = data.get("duration_ms")
        task.retry_count = data.get("retry_count", 0)

        if data.get("created_at"):
            task.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])

        # 解析结果
        if data.get("result"):
            from ..models.schemas import AssertionResult, ObjectDetail
            result_data = data["result"]
            detected_objects = [
                ObjectDetail(**obj) for obj in result_data.get("detected_objects", [])
            ]
            task.result = AssertionResult(
                assertion_passed=result_data.get("assertion_passed", False),
                confidence=result_data.get("confidence", 0.0),
                expected_description=result_data.get("expected_description", ""),
                actual_description=result_data.get("actual_description", ""),
                object_match=result_data.get("object_match", False),
                quantity_match=result_data.get("quantity_match", False),
                image_match=result_data.get("image_match"),
                image_similarity=result_data.get("image_similarity"),
                match_location=result_data.get("match_location"),
                comparison_mode=result_data.get("comparison_mode"),
                expected_quantity=result_data.get("expected_quantity"),
                actual_quantity=result_data.get("actual_quantity"),
                detected_objects=detected_objects,
                reason=result_data.get("reason", ""),
            )

        return task


class TaskManager:
    """任务管理器（带持久化存储）"""

    def __init__(self):
        self._cache: Dict[str, AssertionTask] = {}  # 内存缓存
        self._lock = threading.Lock()

    def create_task(
        self,
        expectation: str,
        image_data: Optional[str] = None,
        image_type: str = "base64",
        image_format: str = "jpeg",
        expect_image_data: Optional[str] = None,
        expect_image_type: Optional[str] = None,
        expect_image_format: str = "jpeg",
    ) -> AssertionTask:
        """创建新任务"""
        task_id = str(uuid.uuid4())

        # 设置追踪ID
        set_trace_id(task_id[:8])

        task = AssertionTask(
            task_id=task_id,
            expectation=expectation,
            image_data=image_data,
            image_type=image_type,
            image_format=image_format,
            expect_image_data=expect_image_data,
            expect_image_type=expect_image_type,
            expect_image_format=expect_image_format,
        )

        # 确定对比模式
        comparison_mode = None
        if expect_image_data:
            comparison_mode = "partial"  # 默认为局部匹配，实际由API层确定

        # 持久化到数据库
        try:
            # 解码图片数据用于存储
            image_bytes = None
            if image_data and image_type == "base64":
                image_bytes = base64.b64decode(image_data)

            expect_image_bytes = None
            if expect_image_data and expect_image_type == "base64":
                expect_image_bytes = base64.b64decode(expect_image_data)

            db.create_task(
                task_id=task_id,
                expectation=expectation,
                image_data=image_bytes,
                image_type=image_type,
                expect_image_data=expect_image_bytes,
                expect_image_type=expect_image_type,
                comparison_mode=comparison_mode,
            )
        except Exception as e:
            logger.error(f"任务持久化失败: {e}", task_id=task_id)

        # 添加到缓存
        with self._lock:
            self._cache[task_id] = task

        logger.log_task_created(task_id, expectation, comparison_mode)
        return task

    def get_task(self, task_id: str) -> Optional[AssertionTask]:
        """获取任务"""
        # 先从缓存获取
        with self._lock:
            if task_id in self._cache:
                return self._cache[task_id]

        # 从数据库获取
        try:
            db_data = db.get_task(task_id)
            if db_data:
                task = AssertionTask.from_db_dict(db_data)
                with self._lock:
                    self._cache[task_id] = task
                return task
        except Exception as e:
            logger.error(f"从数据库获取任务失败: {e}", task_id=task_id)

        return None

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[AssertionResult] = None,
        error: Optional[str] = None,
        raw_response: Optional[str] = None,
        duration_ms: Optional[float] = None,
        retry_count: Optional[int] = None,
    ):
        """更新任务状态"""
        # 更新缓存
        with self._lock:
            task = self._cache.get(task_id)
            if task:
                task.status = status
                task.result = result
                task.error = error
                if duration_ms:
                    task.duration_ms = duration_ms
                if retry_count is not None:
                    task.retry_count = retry_count
                if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                    task.completed_at = datetime.now()

        # 更新数据库
        try:
            db.update_task_status(
                task_id=task_id,
                status=status.value,
                error=error,
                duration_ms=duration_ms,
                retry_count=retry_count,
            )

            # 保存断言结果
            if result:
                db.save_assertion_result(task_id, result, raw_response)

            # 记录日志
            if status == TaskStatus.COMPLETED and result:
                logger.log_task_completed(
                    task_id=task_id,
                    assertion_passed=result.assertion_passed,
                    confidence=result.confidence,
                    duration_ms=duration_ms or 0,
                )
            elif status == TaskStatus.FAILED:
                logger.log_task_failed(
                    task_id=task_id,
                    error=error or "未知错误",
                    duration_ms=duration_ms,
                )

        except Exception as e:
            logger.error(f"更新任务状态到数据库失败: {e}", task_id=task_id)

    def log_api_call(
        self,
        task_id: str,
        attempt: int,
        prompt_type: str,
        success: bool,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
        raw_response: Optional[str] = None,
    ):
        """记录API调用日志"""
        try:
            db.log_api_call(
                task_id=task_id,
                attempt=attempt,
                prompt_type=prompt_type,
                success=success,
                duration_ms=duration_ms,
                error=error,
                raw_response=raw_response,
            )
        except Exception as e:
            logger.error(f"记录API调用日志失败: {e}", task_id=task_id)

    def get_all_tasks(self, limit: int = 50, offset: int = 0) -> List[AssertionTask]:
        """获取所有任务（按时间倒序）"""
        try:
            db_tasks = db.get_all_tasks(limit=limit, offset=offset)
            tasks = []
            for db_data in db_tasks:
                task = AssertionTask.from_db_dict(db_data)
                # 更新缓存
                with self._lock:
                    if task.task_id not in self._cache:
                        self._cache[task.task_id] = task
                tasks.append(task)
            return tasks
        except Exception as e:
            logger.error(f"获取任务列表失败: {e}")
            # 降级到缓存
            with self._lock:
                tasks = list(self._cache.values())
                tasks.sort(key=lambda x: x.created_at, reverse=True)
                return tasks[offset:offset + limit]

    def get_task_count(self) -> int:
        """获取任务总数"""
        try:
            return db.get_task_count()
        except Exception as e:
            logger.error(f"获取任务总数失败: {e}")
            with self._lock:
                return len(self._cache)

    def clear_tasks(self):
        """清空所有任务"""
        with self._lock:
            self._cache.clear()

        try:
            db.clear_all_tasks()
            logger.info("所有任务已清空")
        except Exception as e:
            logger.error(f"清空数据库任务失败: {e}")

    def get_api_logs(self, task_id: str) -> List[dict]:
        """获取任务的API调用日志"""
        try:
            return db.get_api_logs(task_id)
        except Exception as e:
            logger.error(f"获取API日志失败: {e}", task_id=task_id)
            return []


# 全局任务管理器实例
task_manager = TaskManager()
