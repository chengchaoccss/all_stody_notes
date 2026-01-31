"""
配置文件 - 豆包API配置
"""
import os
from pathlib import Path
from typing import Optional


class Settings:
    """应用配置"""

    # 豆包API配置
    # 从环境变量读取，或者直接设置
    DOUBAO_API_KEY: str = os.getenv("DOUBAO_API_KEY", "")
    DOUBAO_API_BASE: str = os.getenv("DOUBAO_API_BASE", "https://ark.cn-beijing.volces.com/api/v3")

    # 豆包视觉模型端点ID (需要在火山引擎控制台创建)
    # 推荐使用 doubao-1.5-vision-pro 或 doubao-vision-pro-32k
    DOUBAO_MODEL_ENDPOINT: str = os.getenv("DOUBAO_MODEL_ENDPOINT", "")

    # 服务配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 图片大小限制 (bytes)
    MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # ========== 第一优先级优化配置 ==========

    # API重试配置
    API_MAX_RETRIES: int = int(os.getenv("API_MAX_RETRIES", "3"))  # 最大重试次数
    API_RETRY_BASE_DELAY: float = float(os.getenv("API_RETRY_BASE_DELAY", "2.0"))  # 基础延迟(秒)
    API_RETRY_MAX_DELAY: float = float(os.getenv("API_RETRY_MAX_DELAY", "30.0"))  # 最大延迟(秒)
    API_TIMEOUT: float = float(os.getenv("API_TIMEOUT", "60.0"))  # API调用超时(秒)

    # 置信度阈值配置
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))  # 置信度阈值
    LOW_CONFIDENCE_RETRY: bool = os.getenv("LOW_CONFIDENCE_RETRY", "true").lower() == "true"  # 低置信度是否重试

    # 持久化存储配置
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(Path(__file__).parent / "data")))
    DATABASE_PATH: Path = DATA_DIR / "assertions.db"
    IMAGE_STORAGE_PATH: Path = DATA_DIR / "images"

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", str(Path(__file__).parent / "logs")))
    LOG_FILE: Path = LOG_DIR / "assertion.log"
    LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))  # 保留5个备份

    @classmethod
    def validate(cls) -> tuple[bool, Optional[str]]:
        """验证配置是否完整"""
        if not cls.DOUBAO_API_KEY:
            return False, "DOUBAO_API_KEY 未设置"
        if not cls.DOUBAO_MODEL_ENDPOINT:
            return False, "DOUBAO_MODEL_ENDPOINT 未设置"
        return True, None

    @classmethod
    def ensure_directories(cls):
        """确保必要的目录存在"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.IMAGE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
