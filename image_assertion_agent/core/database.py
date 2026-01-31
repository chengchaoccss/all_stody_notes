"""
数据库模块 - SQLite持久化存储
"""
import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import settings
from ..models.schemas import AssertionResult, ObjectDetail
from .logger import logger


class Database:
    """SQLite数据库管理器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        settings.ensure_directories()
        self.db_path = settings.DATABASE_PATH
        self._local = threading.local()
        self._init_database()
        self._initialized = True
        logger.info(f"数据库初始化完成: {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """获取线程本地的数据库连接"""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0,
            )
            self._local.connection.row_factory = sqlite3.Row
            # 启用外键约束
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection

    @contextmanager
    def _get_cursor(self):
        """获取数据库游标的上下文管理器"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            cursor.close()

    def _init_database(self):
        """初始化数据库表"""
        with self._get_cursor() as cursor:
            # 任务表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    expectation TEXT,
                    image_hash TEXT,
                    image_path TEXT,
                    image_type TEXT DEFAULT 'base64',
                    expect_image_hash TEXT,
                    expect_image_path TEXT,
                    expect_image_type TEXT,
                    status TEXT DEFAULT 'pending',
                    comparison_mode TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_ms REAL,
                    retry_count INTEGER DEFAULT 0
                )
            """)

            # 断言结果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assertion_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    assertion_passed BOOLEAN,
                    confidence REAL,
                    expected_description TEXT,
                    actual_description TEXT,
                    object_match BOOLEAN,
                    quantity_match BOOLEAN,
                    image_match BOOLEAN,
                    image_similarity REAL,
                    match_location TEXT,
                    comparison_mode TEXT,
                    expected_quantity INTEGER,
                    actual_quantity INTEGER,
                    detected_objects TEXT,
                    reason TEXT,
                    raw_response TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                )
            """)

            # API调用日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    attempt INTEGER,
                    request_time TEXT NOT NULL,
                    response_time TEXT,
                    duration_ms REAL,
                    success BOOLEAN,
                    error TEXT,
                    prompt_type TEXT,
                    raw_response TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_logs_task ON api_logs(task_id)")

        logger.log_db_operation("初始化数据库表")

    def _compute_image_hash(self, image_data: bytes) -> str:
        """计算图片哈希值"""
        return hashlib.sha256(image_data).hexdigest()[:16]

    def _save_image(self, image_data: bytes, prefix: str = "test") -> tuple[str, str]:
        """保存图片到文件系统，返回(hash, path)"""
        image_hash = self._compute_image_hash(image_data)
        # 按日期组织目录
        date_dir = settings.IMAGE_STORAGE_PATH / datetime.now().strftime("%Y%m%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{prefix}_{image_hash}.jpg"
        file_path = date_dir / filename

        if not file_path.exists():
            file_path.write_bytes(image_data)
            logger.debug(f"图片已保存: {file_path}")

        return image_hash, str(file_path)

    def _load_image(self, image_path: str) -> Optional[bytes]:
        """从文件系统加载图片"""
        path = Path(image_path)
        if path.exists():
            return path.read_bytes()
        return None

    # ========== 任务操作 ==========

    def create_task(
        self,
        task_id: str,
        expectation: str,
        image_data: Optional[bytes] = None,
        image_type: str = "base64",
        expect_image_data: Optional[bytes] = None,
        expect_image_type: Optional[str] = None,
        comparison_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """创建任务"""
        now = datetime.now().isoformat()

        # 保存图片
        image_hash, image_path = None, None
        if image_data:
            image_hash, image_path = self._save_image(image_data, "test")

        expect_image_hash, expect_image_path = None, None
        if expect_image_data:
            expect_image_hash, expect_image_path = self._save_image(expect_image_data, "expect")

        with self._get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tasks (
                    task_id, expectation, image_hash, image_path, image_type,
                    expect_image_hash, expect_image_path, expect_image_type,
                    status, comparison_mode, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
                (
                    task_id,
                    expectation,
                    image_hash,
                    image_path,
                    image_type,
                    expect_image_hash,
                    expect_image_path,
                    expect_image_type,
                    comparison_mode,
                    now,
                ),
            )

        logger.log_db_operation("创建任务", task_id)
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务"""
        with self._get_cursor() as cursor:
            cursor.execute(
                """
                SELECT t.*, r.assertion_passed, r.confidence, r.expected_description,
                       r.actual_description, r.object_match, r.quantity_match,
                       r.image_match, r.image_similarity, r.match_location,
                       r.expected_quantity, r.actual_quantity, r.detected_objects, r.reason
                FROM tasks t
                LEFT JOIN assertion_results r ON t.task_id = r.task_id
                WHERE t.task_id = ?
            """,
                (task_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_task_dict(row)

    def _row_to_task_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转换为任务字典"""
        task = dict(row)

        # 加载图片数据 (可选，根据需要加载)
        image_data = None
        if task.get("image_path"):
            image_bytes = self._load_image(task["image_path"])
            if image_bytes:
                import base64
                image_data = base64.b64encode(image_bytes).decode("utf-8")

        expect_image_data = None
        if task.get("expect_image_path"):
            expect_bytes = self._load_image(task["expect_image_path"])
            if expect_bytes:
                import base64
                expect_image_data = base64.b64encode(expect_bytes).decode("utf-8")

        # 构建结果
        result = None
        if task.get("assertion_passed") is not None:
            detected_objects = []
            if task.get("detected_objects"):
                try:
                    detected_objects = json.loads(task["detected_objects"])
                except json.JSONDecodeError:
                    pass

            result = {
                "assertion_passed": bool(task["assertion_passed"]),
                "confidence": task.get("confidence", 0.0),
                "expected_description": task.get("expected_description", ""),
                "actual_description": task.get("actual_description", ""),
                "object_match": bool(task.get("object_match", False)),
                "quantity_match": bool(task.get("quantity_match", False)),
                "image_match": task.get("image_match"),
                "image_similarity": task.get("image_similarity"),
                "match_location": task.get("match_location"),
                "comparison_mode": task.get("comparison_mode"),
                "expected_quantity": task.get("expected_quantity"),
                "actual_quantity": task.get("actual_quantity"),
                "detected_objects": detected_objects,
                "reason": task.get("reason", ""),
            }

        return {
            "task_id": task["task_id"],
            "status": task["status"],
            "expectation": task["expectation"] or "",
            "image_data": image_data,
            "image_type": task.get("image_type", "base64"),
            "expect_image_data": expect_image_data,
            "expect_image_type": task.get("expect_image_type"),
            "result": result,
            "error": task.get("error"),
            "created_at": task["created_at"],
            "completed_at": task.get("completed_at"),
            "duration_ms": task.get("duration_ms"),
            "retry_count": task.get("retry_count", 0),
        }

    def update_task_status(
        self,
        task_id: str,
        status: str,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
        retry_count: Optional[int] = None,
    ):
        """更新任务状态"""
        updates = ["status = ?"]
        params = [status]

        if status in ("completed", "failed"):
            updates.append("completed_at = ?")
            params.append(datetime.now().isoformat())

        if error is not None:
            updates.append("error = ?")
            params.append(error)

        if duration_ms is not None:
            updates.append("duration_ms = ?")
            params.append(duration_ms)

        if retry_count is not None:
            updates.append("retry_count = ?")
            params.append(retry_count)

        params.append(task_id)

        with self._get_cursor() as cursor:
            cursor.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?",
                params,
            )

        logger.log_db_operation(f"更新任务状态: {status}", task_id)

    def save_assertion_result(
        self,
        task_id: str,
        result: AssertionResult,
        raw_response: Optional[str] = None,
    ):
        """保存断言结果"""
        now = datetime.now().isoformat()

        # 序列化detected_objects
        detected_objects_json = json.dumps(
            [obj.model_dump() for obj in result.detected_objects],
            ensure_ascii=False,
        )

        with self._get_cursor() as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO assertion_results (
                    task_id, assertion_passed, confidence, expected_description,
                    actual_description, object_match, quantity_match, image_match,
                    image_similarity, match_location, comparison_mode,
                    expected_quantity, actual_quantity, detected_objects, reason,
                    raw_response, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    task_id,
                    result.assertion_passed,
                    result.confidence,
                    result.expected_description,
                    result.actual_description,
                    result.object_match,
                    result.quantity_match,
                    result.image_match,
                    result.image_similarity,
                    result.match_location,
                    result.comparison_mode,
                    result.expected_quantity,
                    result.actual_quantity,
                    detected_objects_json,
                    result.reason,
                    raw_response,
                    now,
                ),
            )

        logger.log_db_operation("保存断言结果", task_id)

    def get_all_tasks(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """获取所有任务"""
        with self._get_cursor() as cursor:
            cursor.execute(
                """
                SELECT t.*, r.assertion_passed, r.confidence, r.expected_description,
                       r.actual_description, r.object_match, r.quantity_match,
                       r.image_match, r.image_similarity, r.match_location,
                       r.expected_quantity, r.actual_quantity, r.detected_objects, r.reason
                FROM tasks t
                LEFT JOIN assertion_results r ON t.task_id = r.task_id
                ORDER BY t.created_at DESC
                LIMIT ? OFFSET ?
            """,
                (limit, offset),
            )
            rows = cursor.fetchall()

        return [self._row_to_task_dict(row) for row in rows]

    def get_task_count(self) -> int:
        """获取任务总数"""
        with self._get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM tasks")
            return cursor.fetchone()[0]

    def clear_all_tasks(self):
        """清空所有任务"""
        with self._get_cursor() as cursor:
            cursor.execute("DELETE FROM api_logs")
            cursor.execute("DELETE FROM assertion_results")
            cursor.execute("DELETE FROM tasks")

        logger.log_db_operation("清空所有任务")

    # ========== API日志操作 ==========

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
        now = datetime.now().isoformat()

        with self._get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO api_logs (
                    task_id, attempt, request_time, response_time, duration_ms,
                    success, error, prompt_type, raw_response
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    task_id,
                    attempt,
                    now,
                    now if duration_ms else None,
                    duration_ms,
                    success,
                    error,
                    prompt_type,
                    raw_response[:5000] if raw_response else None,  # 限制存储大小
                ),
            )

    def get_api_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """获取任务的API调用日志"""
        with self._get_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM api_logs WHERE task_id = ? ORDER BY attempt
            """,
                (task_id,),
            )
            rows = cursor.fetchall()

        return [dict(row) for row in rows]


# 全局数据库实例
db = Database()
