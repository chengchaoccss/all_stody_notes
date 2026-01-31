"""
豆包视觉API客户端
使用OpenAI兼容接口调用豆包视觉大模型
"""
import base64
import json
from typing import Optional

from openai import OpenAI

from ..config import settings
from ..models.schemas import AssertionResult, ObjectDetail


class DoubaoVisionClient:
    """豆包视觉API客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model_endpoint: Optional[str] = None,
    ):
        self.api_key = api_key or settings.DOUBAO_API_KEY
        self.api_base = api_base or settings.DOUBAO_API_BASE
        self.model_endpoint = model_endpoint or settings.DOUBAO_MODEL_ENDPOINT

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
        )

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一个专业的图像视觉分析助手，专门用于验证图片内容是否符合用户的预期。

你的任务是：
1. 仔细分析用户提供的图片
2. 根据用户的预期描述，判断图片内容是否满足预期
3. 必须以严格的JSON格式返回分析结果

返回的JSON格式必须严格遵循以下schema：
{
    "assertion_passed": boolean,  // 断言是否通过（预期是否完全满足）
    "confidence": float,  // 置信度，0.0-1.0之间
    "expected_description": string,  // 用户的预期描述
    "actual_description": string,  // 图片中实际看到的内容描述
    "object_match": boolean,  // 物品类型是否匹配
    "quantity_match": boolean,  // 数量是否匹配
    "expected_quantity": int or null,  // 预期数量（如果用户指定了的话）
    "actual_quantity": int or null,  // 实际检测到的数量
    "detected_objects": [  // 检测到的物品列表
        {
            "name": string,  // 物品名称
            "quantity": int,  // 数量
            "confidence": float,  // 检测置信度
            "description": string  // 详细描述
        }
    ],
    "reason": string  // 判断理由的详细说明
}

注意事项：
- 如果用户说"一双鞋"，预期数量应该是2（一双=两只）
- 如果用户说"一对xx"，预期数量应该是2
- 仔细计数图片中的物品数量
- 只返回JSON，不要有任何其他文字说明"""

    def _build_user_prompt(self, expectation: str) -> str:
        """构建用户提示词"""
        return f"""请分析这张图片，并验证是否满足以下预期：

预期描述：{expectation}

请严格按照JSON格式返回分析结果。"""

    def _encode_image_to_base64(self, image_bytes: bytes) -> str:
        """将图片编码为base64"""
        return base64.b64encode(image_bytes).decode("utf-8")

    def _parse_response(self, response_text: str, expectation: str) -> AssertionResult:
        """解析API响应"""
        # 尝试提取JSON部分
        text = response_text.strip()

        # 如果响应被包裹在markdown代码块中，提取出来
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            data = json.loads(text)

            # 解析检测到的物品
            detected_objects = []
            for obj in data.get("detected_objects", []):
                detected_objects.append(
                    ObjectDetail(
                        name=obj.get("name", "未知"),
                        quantity=obj.get("quantity", 0),
                        confidence=obj.get("confidence", 0.0),
                        description=obj.get("description", ""),
                    )
                )

            return AssertionResult(
                assertion_passed=data.get("assertion_passed", False),
                confidence=data.get("confidence", 0.0),
                expected_description=data.get("expected_description", expectation),
                actual_description=data.get("actual_description", ""),
                object_match=data.get("object_match", False),
                quantity_match=data.get("quantity_match", False),
                expected_quantity=data.get("expected_quantity"),
                actual_quantity=data.get("actual_quantity"),
                detected_objects=detected_objects,
                reason=data.get("reason", ""),
            )
        except json.JSONDecodeError as e:
            # 解析失败时返回错误结果
            return AssertionResult(
                assertion_passed=False,
                confidence=0.0,
                expected_description=expectation,
                actual_description="",
                object_match=False,
                quantity_match=False,
                expected_quantity=None,
                actual_quantity=None,
                detected_objects=[],
                reason=f"API响应解析失败: {str(e)}, 原始响应: {response_text[:500]}",
            )

    def assert_image(
        self,
        image_bytes: bytes,
        expectation: str,
        image_format: str = "jpeg",
    ) -> AssertionResult:
        """
        对图片进行视觉断言

        Args:
            image_bytes: 图片的二进制数据
            expectation: 用户的预期描述，如"这张图里面有一双运动鞋"
            image_format: 图片格式，如 jpeg, png, webp 等

        Returns:
            AssertionResult: 断言结果
        """
        # 将图片编码为base64
        image_base64 = self._encode_image_to_base64(image_bytes)

        # 构建消息
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{image_format};base64,{image_base64}"
                        },
                    },
                    {"type": "text", "text": self._build_user_prompt(expectation)},
                ],
            },
        ]

        # 调用API
        response = self.client.chat.completions.create(
            model=self.model_endpoint,
            messages=messages,
            temperature=0.1,  # 低温度以获得更稳定的输出
            max_tokens=2000,
        )

        # 解析响应
        response_text = response.choices[0].message.content
        return self._parse_response(response_text, expectation)

    def assert_image_url(self, image_url: str, expectation: str) -> AssertionResult:
        """
        对URL图片进行视觉断言

        Args:
            image_url: 图片URL
            expectation: 用户的预期描述

        Returns:
            AssertionResult: 断言结果
        """
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": self._build_user_prompt(expectation)},
                ],
            },
        ]

        response = self.client.chat.completions.create(
            model=self.model_endpoint,
            messages=messages,
            temperature=0.1,
            max_tokens=2000,
        )

        response_text = response.choices[0].message.content
        return self._parse_response(response_text, expectation)
