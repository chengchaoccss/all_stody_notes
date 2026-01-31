"""
异步任务管理器 - 管理图像断言任务的异步执行
"""
import threading
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from ..models.schemas import AssertionResult


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
        }


class TaskManager:
    """任务管理器"""

    def __init__(self):
        self._tasks: Dict[str, AssertionTask] = {}
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
        with self._lock:
            self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[AssertionTask]:
        """获取任务"""
        with self._lock:
            return self._tasks.get(task_id)

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[AssertionResult] = None,
        error: Optional[str] = None,
    ):
        """更新任务状态"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = status
                task.result = result
                task.error = error
                if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                    task.completed_at = datetime.now()

    def get_all_tasks(self, limit: int = 50) -> list:
        """获取所有任务（按时间倒序）"""
        with self._lock:
            tasks = list(self._tasks.values())
            tasks.sort(key=lambda x: x.created_at, reverse=True)
            return tasks[:limit]

    def clear_tasks(self):
        """清空所有任务"""
        with self._lock:
            self._tasks.clear()


# 全局任务管理器实例
task_manager = TaskManager()
