"""
配置文件 - 豆包API配置
"""
import os
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

    @classmethod
    def validate(cls) -> tuple[bool, Optional[str]]:
        """验证配置是否完整"""
        if not cls.DOUBAO_API_KEY:
            return False, "DOUBAO_API_KEY 未设置"
        if not cls.DOUBAO_MODEL_ENDPOINT:
            return False, "DOUBAO_MODEL_ENDPOINT 未设置"
        return True, None


settings = Settings()
