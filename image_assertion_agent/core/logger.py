"""
日志模块 - 提供完整的日志记录功能
"""
import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, Optional

from ..config import settings

# 请求追踪ID上下文
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    """获取当前请求的追踪ID"""
    return trace_id_var.get() or str(uuid.uuid4())[:8]


def set_trace_id(trace_id: Optional[str] = None) -> str:
    """设置追踪ID"""
    tid = trace_id or str(uuid.uuid4())[:8]
    trace_id_var.set(tid)
    return tid


class JSONFormatter(logging.Formatter):
    """JSON格式的日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": get_trace_id(),
        }

        # 添加额外字段
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加位置信息
        if record.levelno >= logging.WARNING:
            log_data["location"] = {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
            }

        return json.dumps(log_data, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """控制台友好的格式化器"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        trace_id = get_trace_id()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 基础消息
        msg = f"{color}[{timestamp}] [{record.levelname:8}] [{trace_id}] {record.getMessage()}{self.RESET}"

        # 添加额外数据
        if hasattr(record, "extra_data") and record.extra_data:
            data_str = json.dumps(record.extra_data, ensure_ascii=False, indent=2)
            msg += f"\n  {color}Data: {data_str}{self.RESET}"

        return msg


class AssertionLogger:
    """断言日志记录器"""

    def __init__(self, name: str = "assertion_agent"):
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self):
        """设置日志记录器"""
        # 确保目录存在
        settings.ensure_directories()

        self.logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

        # 清除现有处理器
        self.logger.handlers.clear()

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ConsoleFormatter())
        console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
        self.logger.addHandler(console_handler)

        # 文件处理器 (JSON格式)
        file_handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(JSONFormatter())
        file_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)

    def _log(self, level: int, message: str, extra_data: Optional[dict] = None):
        """内部日志方法"""
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            "(unknown file)",
            0,
            message,
            args=(),
            exc_info=None,
        )
        if extra_data:
            record.extra_data = extra_data
        self.logger.handle(record)

    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._log(logging.DEBUG, message, kwargs if kwargs else None)

    def info(self, message: str, **kwargs):
        """信息日志"""
        self._log(logging.INFO, message, kwargs if kwargs else None)

    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._log(logging.WARNING, message, kwargs if kwargs else None)

    def error(self, message: str, **kwargs):
        """错误日志"""
        self._log(logging.ERROR, message, kwargs if kwargs else None)

    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        self._log(logging.CRITICAL, message, kwargs if kwargs else None)

    # ========== 业务日志方法 ==========

    def log_api_request(
        self,
        endpoint: str,
        method: str,
        task_id: Optional[str] = None,
        expectation: Optional[str] = None,
        has_test_image: bool = False,
        has_expect_image: bool = False,
    ):
        """记录API请求"""
        self.info(
            f"API请求: {method} {endpoint}",
            task_id=task_id,
            expectation=expectation[:100] if expectation else None,
            has_test_image=has_test_image,
            has_expect_image=has_expect_image,
        )

    def log_api_response(
        self,
        endpoint: str,
        status_code: int,
        task_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ):
        """记录API响应"""
        self.info(
            f"API响应: {endpoint} -> {status_code}",
            task_id=task_id,
            status_code=status_code,
            duration_ms=duration_ms,
        )

    def log_doubao_call(
        self,
        task_id: str,
        attempt: int,
        max_attempts: int,
        prompt_type: str,
    ):
        """记录豆包API调用"""
        self.info(
            f"调用豆包API (尝试 {attempt}/{max_attempts})",
            task_id=task_id,
            attempt=attempt,
            max_attempts=max_attempts,
            prompt_type=prompt_type,
        )

    def log_doubao_response(
        self,
        task_id: str,
        success: bool,
        duration_ms: float,
        confidence: Optional[float] = None,
        assertion_passed: Optional[bool] = None,
        raw_response_preview: Optional[str] = None,
    ):
        """记录豆包API响应"""
        level = logging.INFO if success else logging.WARNING
        self._log(
            level,
            f"豆包API响应: {'成功' if success else '失败'}",
            {
                "task_id": task_id,
                "success": success,
                "duration_ms": duration_ms,
                "confidence": confidence,
                "assertion_passed": assertion_passed,
                "raw_response_preview": raw_response_preview[:200] if raw_response_preview else None,
            },
        )

    def log_retry(
        self,
        task_id: str,
        attempt: int,
        reason: str,
        delay_seconds: float,
    ):
        """记录重试"""
        self.warning(
            f"准备重试 (延迟 {delay_seconds:.1f}s)",
            task_id=task_id,
            attempt=attempt,
            reason=reason,
            delay_seconds=delay_seconds,
        )

    def log_low_confidence(
        self,
        task_id: str,
        confidence: float,
        threshold: float,
        will_retry: bool,
    ):
        """记录低置信度"""
        self.warning(
            f"置信度低于阈值: {confidence:.2f} < {threshold:.2f}",
            task_id=task_id,
            confidence=confidence,
            threshold=threshold,
            will_retry=will_retry,
        )

    def log_task_created(self, task_id: str, expectation: str, comparison_mode: Optional[str] = None):
        """记录任务创建"""
        self.info(
            f"任务创建: {task_id}",
            task_id=task_id,
            expectation=expectation[:100] if expectation else "(图片对比)",
            comparison_mode=comparison_mode,
        )

    def log_task_completed(
        self,
        task_id: str,
        assertion_passed: bool,
        confidence: float,
        duration_ms: float,
    ):
        """记录任务完成"""
        self.info(
            f"任务完成: {task_id} -> {'通过' if assertion_passed else '失败'}",
            task_id=task_id,
            assertion_passed=assertion_passed,
            confidence=confidence,
            duration_ms=duration_ms,
        )

    def log_task_failed(self, task_id: str, error: str, duration_ms: Optional[float] = None):
        """记录任务失败"""
        self.error(
            f"任务失败: {task_id}",
            task_id=task_id,
            error=error,
            duration_ms=duration_ms,
        )

    def log_db_operation(self, operation: str, task_id: Optional[str] = None, success: bool = True):
        """记录数据库操作"""
        level = logging.DEBUG if success else logging.ERROR
        self._log(
            level,
            f"数据库操作: {operation}",
            {"task_id": task_id, "success": success},
        )


# 全局日志实例
logger = AssertionLogger()
