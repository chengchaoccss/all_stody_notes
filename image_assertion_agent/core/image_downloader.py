"""
图片下载模块
支持从URL下载图片，自动检测格式
"""
import io
import mimetypes
from typing import Optional, Tuple
from urllib.parse import urlparse

import httpx
from PIL import Image

from .logger import logger


class ImageDownloadError(Exception):
    """图片下载错误"""
    pass


class ImageDownloader:
    """图片下载器"""

    # 支持的图片格式
    SUPPORTED_FORMATS = {
        "image/jpeg": "jpeg",
        "image/jpg": "jpeg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
        "image/bmp": "bmp",
        "image/tiff": "tiff",
    }

    # 通过文件扩展名推断格式
    EXTENSION_MAP = {
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".png": "png",
        ".gif": "gif",
        ".webp": "webp",
        ".bmp": "bmp",
        ".tiff": "tiff",
        ".tif": "tiff",
    }

    def __init__(self, timeout: float = 30.0, max_size: int = 10 * 1024 * 1024):
        """
        初始化图片下载器

        Args:
            timeout: 下载超时时间（秒）
            max_size: 最大图片大小（字节），默认10MB
        """
        self.timeout = timeout
        self.max_size = max_size
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

    def _detect_format_from_url(self, url: str) -> Optional[str]:
        """从URL路径推断图片格式"""
        parsed = urlparse(url)
        path = parsed.path.lower()

        for ext, fmt in self.EXTENSION_MAP.items():
            if path.endswith(ext):
                return fmt

        return None

    def _detect_format_from_content_type(self, content_type: str) -> Optional[str]:
        """从Content-Type推断图片格式"""
        # 清理content-type（移除charset等参数）
        main_type = content_type.split(";")[0].strip().lower()
        return self.SUPPORTED_FORMATS.get(main_type)

    def _detect_format_from_bytes(self, image_bytes: bytes) -> Optional[str]:
        """从图片二进制数据检测格式"""
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                fmt = img.format
                if fmt:
                    return fmt.lower()
        except Exception:
            pass
        return None

    def download(self, url: str, task_id: Optional[str] = None) -> Tuple[bytes, str]:
        """
        下载图片

        Args:
            url: 图片URL
            task_id: 任务ID（用于日志追踪）

        Returns:
            Tuple[bytes, str]: (图片二进制数据, 图片格式)

        Raises:
            ImageDownloadError: 下载失败时抛出
        """
        logger.info(f"开始下载图片: {url[:100]}...", task_id=task_id)

        try:
            # 发起请求
            response = self.client.get(url)
            response.raise_for_status()

            # 检查内容大小
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > self.max_size:
                raise ImageDownloadError(
                    f"图片太大: {int(content_length) / 1024 / 1024:.1f}MB > {self.max_size / 1024 / 1024:.1f}MB"
                )

            image_bytes = response.content

            # 再次检查实际大小
            if len(image_bytes) > self.max_size:
                raise ImageDownloadError(
                    f"图片太大: {len(image_bytes) / 1024 / 1024:.1f}MB > {self.max_size / 1024 / 1024:.1f}MB"
                )

            # 检测图片格式
            image_format = None

            # 1. 优先从Content-Type检测
            content_type = response.headers.get("content-type", "")
            image_format = self._detect_format_from_content_type(content_type)

            # 2. 从URL扩展名检测
            if not image_format:
                image_format = self._detect_format_from_url(url)

            # 3. 从图片内容检测
            if not image_format:
                image_format = self._detect_format_from_bytes(image_bytes)

            # 默认使用jpeg
            if not image_format:
                image_format = "jpeg"

            logger.info(
                f"图片下载成功: {len(image_bytes)} bytes, 格式: {image_format}",
                task_id=task_id,
            )

            return image_bytes, image_format

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP错误 {e.response.status_code}: {url}"
            logger.error(error_msg, task_id=task_id)
            raise ImageDownloadError(error_msg)

        except httpx.TimeoutException:
            error_msg = f"下载超时: {url}"
            logger.error(error_msg, task_id=task_id)
            raise ImageDownloadError(error_msg)

        except httpx.RequestError as e:
            error_msg = f"请求错误: {str(e)}"
            logger.error(error_msg, task_id=task_id)
            raise ImageDownloadError(error_msg)

        except ImageDownloadError:
            raise

        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            logger.error(error_msg, task_id=task_id, error=str(e))
            raise ImageDownloadError(error_msg)

    def close(self):
        """关闭HTTP客户端"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 全局下载器实例
_downloader: Optional[ImageDownloader] = None


def get_downloader() -> ImageDownloader:
    """获取全局下载器实例"""
    global _downloader
    if _downloader is None:
        _downloader = ImageDownloader()
    return _downloader


def download_image(url: str, task_id: Optional[str] = None) -> Tuple[bytes, str]:
    """
    下载图片的便捷函数

    Args:
        url: 图片URL
        task_id: 任务ID

    Returns:
        Tuple[bytes, str]: (图片二进制数据, 图片格式)
    """
    return get_downloader().download(url, task_id)
