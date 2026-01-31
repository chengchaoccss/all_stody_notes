#!/usr/bin/env python3
"""
图像视觉断言Agent - Python客户端使用示例
"""
import base64
from pathlib import Path

import httpx


class ImageAssertionClient:
    """图像视觉断言客户端"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=60.0)

    def assert_image_file(self, image_path: str, expectation: str) -> dict:
        """
        通过文件上传进行图像断言

        Args:
            image_path: 本地图片路径
            expectation: 预期描述

        Returns:
            断言结果字典
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        with open(path, "rb") as f:
            files = {"image": (path.name, f, f"image/{path.suffix[1:]}")}
            data = {"expectation": expectation}

            response = self.client.post(
                f"{self.base_url}/assert/upload",
                files=files,
                data=data,
            )
            response.raise_for_status()
            return response.json()

    def assert_image_base64(
        self, image_bytes: bytes, expectation: str, image_format: str = "jpeg"
    ) -> dict:
        """
        通过Base64编码进行图像断言

        Args:
            image_bytes: 图片二进制数据
            expectation: 预期描述
            image_format: 图片格式

        Returns:
            断言结果字典
        """
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        response = self.client.post(
            f"{self.base_url}/assert/base64",
            json={
                "image_base64": image_base64,
                "expectation": expectation,
                "image_format": image_format,
            },
        )
        response.raise_for_status()
        return response.json()

    def assert_image_url(self, image_url: str, expectation: str) -> dict:
        """
        通过图片URL进行图像断言

        Args:
            image_url: 图片URL
            expectation: 预期描述

        Returns:
            断言结果字典
        """
        response = self.client.post(
            f"{self.base_url}/assert/url",
            json={
                "image_url": image_url,
                "expectation": expectation,
            },
        )
        response.raise_for_status()
        return response.json()

    def health_check(self) -> dict:
        """健康检查"""
        response = self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def close(self):
        """关闭客户端"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """使用示例"""
    # 创建客户端
    with ImageAssertionClient("http://localhost:8000") as client:
        # 健康检查
        print("健康检查:")
        health = client.health_check()
        print(f"  状态: {health['status']}")
        print(f"  配置有效: {health['config_valid']}")

        # 示例1: 通过文件上传断言
        print("\n示例1 - 文件上传断言:")
        print("  client.assert_image_file('shoes.jpg', '这张图里面有一双运动鞋')")

        # 示例2: 通过URL断言
        print("\n示例2 - URL断言:")
        print("  client.assert_image_url('https://example.com/shoes.jpg', '图片中有两只红色的苹果')")

        # 示例3: 通过Base64断言
        print("\n示例3 - Base64断言:")
        print("  with open('image.jpg', 'rb') as f:")
        print("      result = client.assert_image_base64(f.read(), '图中有一只猫')")

        print("\n断言结果JSON Schema示例:")
        result_example = {
            "assertion_passed": True,
            "confidence": 0.92,
            "expected_description": "这张图里面有一双运动鞋",
            "actual_description": "图片中可以看到一双白色的Nike运动鞋",
            "object_match": True,
            "quantity_match": True,
            "expected_quantity": 2,
            "actual_quantity": 2,
            "detected_objects": [
                {
                    "name": "运动鞋",
                    "quantity": 2,
                    "confidence": 0.95,
                    "description": "白色Nike运动鞋",
                }
            ],
            "reason": "图片中确实存在一双运动鞋，物品类型和数量均符合预期",
        }

        import json

        print(json.dumps(result_example, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
