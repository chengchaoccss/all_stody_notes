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

    def _build_system_prompt(self, has_expect_image: bool = False) -> str:
        """构建系统提示词"""
        if has_expect_image:
            return """你是一个专业的图像视觉分析助手，专门用于验证图片内容是否符合用户的预期。

你的任务是：
1. 用户会提供两张图片：第一张是【测试图片】，第二张是【预期图片】（参考/局部图）
2. 分析【测试图片】中是否包含与【预期图片】相似或相同的内容
3. 如果用户还提供了文字描述，也要一并验证
4. 必须以严格的JSON格式返回分析结果

返回的JSON格式必须严格遵循以下schema：
{
    "assertion_passed": boolean,  // 断言是否通过（预期是否完全满足）
    "confidence": float,  // 置信度，0.0-1.0之间
    "expected_description": string,  // 用户的预期描述（如果有的话）
    "actual_description": string,  // 测试图片中实际看到的内容描述
    "object_match": boolean,  // 物品类型是否匹配
    "quantity_match": boolean,  // 数量是否匹配
    "image_match": boolean,  // 预期图片中的内容是否在测试图中找到
    "image_similarity": float,  // 预期图片与测试图中匹配部分的相似度，0.0-1.0
    "match_location": string,  // 预期图片内容在测试图中的位置描述（如"左上角"、"中央"、"右下方"等）
    "expected_quantity": int or null,  // 预期数量（如果用户文字中指定了）
    "actual_quantity": int or null,  // 实际检测到的数量
    "detected_objects": [  // 检测到的与预期相关的物品列表
        {
            "name": string,  // 物品名称
            "quantity": int,  // 数量
            "confidence": float,  // 检测置信度
            "description": string  // 详细描述
        }
    ],
    "reason": string  // 判断理由的详细说明，包括为什么认为匹配或不匹配
}

注意事项：
- 重点关注预期图片中的主要物体/特征是否出现在测试图片中
- 考虑颜色、形状、纹理、品牌标识等细节特征
- 如果预期图片是某物品的局部，判断测试图中是否有完整或部分的该物品
- 相似度评分要客观，完全相同为1.0，完全不相关为0.0
- 只返回JSON，不要有任何其他文字说明"""
        else:
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

    def _build_user_prompt(self, expectation: str, has_expect_image: bool = False) -> str:
        """构建用户提示词"""
        if has_expect_image:
            if expectation:
                return f"""请分析这两张图片：
- 第一张是【测试图片】（需要验证的图片）
- 第二张是【预期图片】（参考图/局部图，表示我希望在测试图中找到的内容）

除了图片对比，还需要验证以下文字预期：
{expectation}

请判断测试图片中是否包含预期图片中的内容，并严格按照JSON格式返回分析结果。"""
            else:
                return """请分析这两张图片：
- 第一张是【测试图片】（需要验证的图片）
- 第二张是【预期图片】（参考图/局部图，表示我希望在测试图中找到的内容）

请判断测试图片中是否包含预期图片中的内容，并严格按照JSON格式返回分析结果。"""
        else:
            return f"""请分析这张图片，并验证是否满足以下预期：

预期描述：{expectation}

请严格按照JSON格式返回分析结果。"""

    def _encode_image_to_base64(self, image_bytes: bytes) -> str:
        """将图片编码为base64"""
        return base64.b64encode(image_bytes).decode("utf-8")

    def _parse_response(
        self, response_text: str, expectation: str, has_expect_image: bool = False
    ) -> AssertionResult:
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
                image_match=data.get("image_match") if has_expect_image else None,
                image_similarity=data.get("image_similarity") if has_expect_image else None,
                match_location=data.get("match_location") if has_expect_image else None,
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
                image_match=False if has_expect_image else None,
                image_similarity=0.0 if has_expect_image else None,
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
        expect_image_bytes: Optional[bytes] = None,
        expect_image_format: str = "jpeg",
    ) -> AssertionResult:
        """
        对图片进行视觉断言

        Args:
            image_bytes: 测试图片的二进制数据
            expectation: 用户的预期描述，如"这张图里面有一双运动鞋"
            image_format: 测试图片格式，如 jpeg, png, webp 等
            expect_image_bytes: 预期图片的二进制数据（可选，局部参考图）
            expect_image_format: 预期图片格式

        Returns:
            AssertionResult: 断言结果
        """
        has_expect_image = expect_image_bytes is not None

        # 将测试图片编码为base64
        image_base64 = self._encode_image_to_base64(image_bytes)

        # 构建消息内容
        content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{image_format};base64,{image_base64}"
                },
            },
        ]

        # 如果有预期图片，添加到消息中
        if has_expect_image:
            expect_image_base64 = self._encode_image_to_base64(expect_image_bytes)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{expect_image_format};base64,{expect_image_base64}"
                    },
                }
            )

        # 添加文本提示
        content.append(
            {"type": "text", "text": self._build_user_prompt(expectation, has_expect_image)}
        )

        # 构建消息
        messages = [
            {"role": "system", "content": self._build_system_prompt(has_expect_image)},
            {"role": "user", "content": content},
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
        return self._parse_response(response_text, expectation, has_expect_image)

    def assert_image_url(
        self,
        image_url: str,
        expectation: str,
        expect_image_url: Optional[str] = None,
    ) -> AssertionResult:
        """
        对URL图片进行视觉断言

        Args:
            image_url: 测试图片URL
            expectation: 用户的预期描述
            expect_image_url: 预期图片URL（可选，局部参考图）

        Returns:
            AssertionResult: 断言结果
        """
        has_expect_image = expect_image_url is not None

        # 构建消息内容
        content = [
            {"type": "image_url", "image_url": {"url": image_url}},
        ]

        # 如果有预期图片URL
        if has_expect_image:
            content.append(
                {"type": "image_url", "image_url": {"url": expect_image_url}}
            )

        content.append(
            {"type": "text", "text": self._build_user_prompt(expectation, has_expect_image)}
        )

        messages = [
            {"role": "system", "content": self._build_system_prompt(has_expect_image)},
            {"role": "user", "content": content},
        ]

        response = self.client.chat.completions.create(
            model=self.model_endpoint,
            messages=messages,
            temperature=0.1,
            max_tokens=2000,
        )

        response_text = response.choices[0].message.content
        return self._parse_response(response_text, expectation, has_expect_image)
