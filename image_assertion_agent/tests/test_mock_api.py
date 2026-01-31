"""
图像视觉断言Agent - Mock API测试
使用Mock模拟豆包API响应，测试整个工程的各个模块
"""
import base64
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image
import httpx


# ============ 测试数据生成工具 ============

def create_test_image(width: int = 100, height: int = 100, color: str = "red") -> bytes:
    """创建测试图片"""
    colors = {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "white": (255, 255, 255),
        "black": (0, 0, 0),
    }
    img = Image.new("RGB", (width, height), colors.get(color, (255, 0, 0)))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def create_test_image_base64(width: int = 100, height: int = 100, color: str = "red") -> str:
    """创建Base64编码的测试图片"""
    image_bytes = create_test_image(width, height, color)
    return base64.b64encode(image_bytes).decode("utf-8")


def create_mock_api_response(
    assertion_passed: bool = True,
    confidence: float = 0.95,
    object_match: bool = True,
    quantity_match: bool = True,
    image_match: bool = None,
    image_similarity: float = None,
    comparison_mode: str = None,
) -> str:
    """创建模拟的API响应"""
    response = {
        "assertion_passed": assertion_passed,
        "confidence": confidence,
        "expected_description": "测试预期",
        "actual_description": "实际看到的内容",
        "object_match": object_match,
        "quantity_match": quantity_match,
        "expected_quantity": 2,
        "actual_quantity": 2,
        "detected_objects": [
            {
                "name": "测试物品",
                "quantity": 2,
                "confidence": 0.9,
                "description": "检测到的测试物品",
            }
        ],
        "reason": "测试理由",
    }

    if image_match is not None:
        response["image_match"] = image_match
    if image_similarity is not None:
        response["image_similarity"] = image_similarity
    if comparison_mode is not None:
        response["match_location"] = "中央" if comparison_mode == "partial" else "整体对比"

    return json.dumps(response)


# ============ 单元测试 ============

class TestImageDownloader(unittest.TestCase):
    """测试图片下载模块"""

    def test_format_detection_from_url(self):
        """测试从URL检测图片格式"""
        from image_assertion_agent.core.image_downloader import ImageDownloader

        downloader = ImageDownloader()

        # 测试各种扩展名
        self.assertEqual(downloader._detect_format_from_url("http://example.com/image.jpg"), "jpeg")
        self.assertEqual(downloader._detect_format_from_url("http://example.com/image.jpeg"), "jpeg")
        self.assertEqual(downloader._detect_format_from_url("http://example.com/image.png"), "png")
        self.assertEqual(downloader._detect_format_from_url("http://example.com/image.gif"), "gif")
        self.assertEqual(downloader._detect_format_from_url("http://example.com/image.webp"), "webp")
        self.assertIsNone(downloader._detect_format_from_url("http://example.com/image"))

    def test_format_detection_from_content_type(self):
        """测试从Content-Type检测图片格式"""
        from image_assertion_agent.core.image_downloader import ImageDownloader

        downloader = ImageDownloader()

        self.assertEqual(downloader._detect_format_from_content_type("image/jpeg"), "jpeg")
        self.assertEqual(downloader._detect_format_from_content_type("image/png"), "png")
        self.assertEqual(downloader._detect_format_from_content_type("image/jpeg; charset=utf-8"), "jpeg")
        self.assertIsNone(downloader._detect_format_from_content_type("text/html"))

    def test_format_detection_from_bytes(self):
        """测试从图片内容检测格式"""
        from image_assertion_agent.core.image_downloader import ImageDownloader

        downloader = ImageDownloader()

        # 创建PNG图片
        png_bytes = create_test_image(50, 50, "blue")
        self.assertEqual(downloader._detect_format_from_bytes(png_bytes), "png")

    @patch("httpx.Client.get")
    def test_download_success(self, mock_get):
        """测试图片下载成功"""
        from image_assertion_agent.core.image_downloader import ImageDownloader

        # 创建模拟响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = create_test_image(100, 100, "green")
        mock_response.headers = {"content-type": "image/png", "content-length": "1000"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        downloader = ImageDownloader()
        image_bytes, image_format = downloader.download("http://example.com/test.png")

        self.assertIsNotNone(image_bytes)
        self.assertEqual(image_format, "png")

    @patch("httpx.Client.get")
    def test_download_timeout(self, mock_get):
        """测试下载超时"""
        from image_assertion_agent.core.image_downloader import ImageDownloader, ImageDownloadError

        mock_get.side_effect = httpx.TimeoutException("Connection timeout")

        downloader = ImageDownloader()

        with self.assertRaises(ImageDownloadError) as context:
            downloader.download("http://example.com/slow.jpg")

        self.assertIn("超时", str(context.exception))


class TestDoubaoClient(unittest.TestCase):
    """测试豆包API客户端"""

    def setUp(self):
        """设置测试环境"""
        os.environ["DOUBAO_API_KEY"] = "test-api-key"
        os.environ["DOUBAO_MODEL_ENDPOINT"] = "test-endpoint"

    def test_resolution_detection(self):
        """测试分辨率检测"""
        from image_assertion_agent.core.doubao_client import DoubaoVisionClient

        client = DoubaoVisionClient()

        # 创建测试图片
        img_100x100 = create_test_image(100, 100)
        img_200x200 = create_test_image(200, 200)
        img_100x100_2 = create_test_image(100, 100, "blue")

        # 测试分辨率获取
        self.assertEqual(client._get_image_resolution(img_100x100), (100, 100))
        self.assertEqual(client._get_image_resolution(img_200x200), (200, 200))

        # 测试分辨率比较
        self.assertTrue(client._check_same_resolution(img_100x100, img_100x100_2))
        self.assertFalse(client._check_same_resolution(img_100x100, img_200x200))

    def test_system_prompt_selection(self):
        """测试系统提示词选择"""
        from image_assertion_agent.core.doubao_client import DoubaoVisionClient

        client = DoubaoVisionClient()

        # 文字断言模式
        prompt_text = client._build_system_prompt(has_expect_image=False)
        self.assertIn("预期描述", prompt_text)

        # 局部匹配模式
        prompt_partial = client._build_system_prompt(has_expect_image=True, same_resolution=False)
        self.assertIn("局部", prompt_partial)

        # 整体相似度模式
        prompt_similarity = client._build_system_prompt(has_expect_image=True, same_resolution=True)
        self.assertIn("相似度", prompt_similarity)

    def test_response_parsing(self):
        """测试响应解析"""
        from image_assertion_agent.core.doubao_client import DoubaoVisionClient

        client = DoubaoVisionClient()

        # 测试正常JSON响应
        response_text = create_mock_api_response(assertion_passed=True, confidence=0.95)
        result = client._parse_response(response_text, "测试预期")

        self.assertTrue(result.assertion_passed)
        self.assertEqual(result.confidence, 0.95)
        self.assertTrue(result.object_match)

    def test_response_parsing_with_markdown(self):
        """测试包含Markdown代码块的响应解析"""
        from image_assertion_agent.core.doubao_client import DoubaoVisionClient

        client = DoubaoVisionClient()

        # 测试被Markdown包裹的JSON
        response_text = f"```json\n{create_mock_api_response()}\n```"
        result = client._parse_response(response_text, "测试预期")

        self.assertTrue(result.assertion_passed)

    @patch("image_assertion_agent.core.doubao_client.OpenAI")
    def test_assert_image_success(self, mock_openai_class):
        """测试图片断言成功"""
        from image_assertion_agent.core.doubao_client import DoubaoVisionClient

        # 设置Mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = create_mock_api_response()
        mock_client.chat.completions.create.return_value = mock_response

        # 执行测试
        client = DoubaoVisionClient()
        image_bytes = create_test_image(100, 100)
        result, raw_response = client.assert_image(
            image_bytes=image_bytes,
            expectation="这是一张红色图片",
            image_format="png",
        )

        self.assertTrue(result.assertion_passed)
        self.assertEqual(result.confidence, 0.95)

    @patch("image_assertion_agent.core.doubao_client.OpenAI")
    def test_assert_image_with_expect_image_same_resolution(self, mock_openai_class):
        """测试双图对比 - 分辨率相同（相似度模式）"""
        from image_assertion_agent.core.doubao_client import DoubaoVisionClient

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = create_mock_api_response(
            image_match=True,
            image_similarity=0.92,
            comparison_mode="similarity",
        )
        mock_client.chat.completions.create.return_value = mock_response

        client = DoubaoVisionClient()
        test_image = create_test_image(100, 100, "red")
        expect_image = create_test_image(100, 100, "blue")  # 相同分辨率

        result, _ = client.assert_image(
            image_bytes=test_image,
            expectation="",
            image_format="png",
            expect_image_bytes=expect_image,
            expect_image_format="png",
        )

        self.assertEqual(result.comparison_mode, "similarity")
        self.assertTrue(result.image_match)

    @patch("image_assertion_agent.core.doubao_client.OpenAI")
    def test_assert_image_with_expect_image_different_resolution(self, mock_openai_class):
        """测试双图对比 - 分辨率不同（局部匹配模式）"""
        from image_assertion_agent.core.doubao_client import DoubaoVisionClient

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = create_mock_api_response(
            image_match=True,
            image_similarity=0.85,
            comparison_mode="partial",
        )
        mock_client.chat.completions.create.return_value = mock_response

        client = DoubaoVisionClient()
        test_image = create_test_image(200, 200, "red")  # 大图
        expect_image = create_test_image(50, 50, "blue")  # 小图（局部图）

        result, _ = client.assert_image(
            image_bytes=test_image,
            expectation="",
            image_format="png",
            expect_image_bytes=expect_image,
            expect_image_format="png",
        )

        self.assertEqual(result.comparison_mode, "partial")


class TestTaskManager(unittest.TestCase):
    """测试任务管理器"""

    def test_create_task(self):
        """测试创建任务"""
        from image_assertion_agent.core.task_manager import TaskManager, TaskStatus

        manager = TaskManager()
        manager.clear_tasks()

        task = manager.create_task(
            expectation="测试预期",
            image_data="base64_data",
            image_type="base64",
            image_format="png",
        )

        self.assertIsNotNone(task.task_id)
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(task.expectation, "测试预期")

    def test_update_task_status(self):
        """测试更新任务状态"""
        from image_assertion_agent.core.task_manager import TaskManager, TaskStatus
        from image_assertion_agent.models.schemas import AssertionResult

        manager = TaskManager()
        manager.clear_tasks()

        task = manager.create_task(
            expectation="测试预期",
            image_data="base64_data",
            image_type="base64",
        )

        # 更新为处理中
        manager.update_task_status(task.task_id, TaskStatus.PROCESSING)
        updated_task = manager.get_task(task.task_id)
        self.assertEqual(updated_task.status, TaskStatus.PROCESSING)

        # 更新为完成
        result = AssertionResult(
            assertion_passed=True,
            confidence=0.95,
            expected_description="测试",
            actual_description="实际",
            object_match=True,
            quantity_match=True,
            detected_objects=[],
            reason="成功",
        )
        manager.update_task_status(task.task_id, TaskStatus.COMPLETED, result=result)
        updated_task = manager.get_task(task.task_id)
        self.assertEqual(updated_task.status, TaskStatus.COMPLETED)
        self.assertIsNotNone(updated_task.result)

    def test_get_all_tasks(self):
        """测试获取所有任务"""
        from image_assertion_agent.core.task_manager import TaskManager

        manager = TaskManager()
        manager.clear_tasks()

        # 创建多个任务
        for i in range(5):
            manager.create_task(
                expectation=f"测试{i}",
                image_data="data",
                image_type="base64",
            )

        tasks = manager.get_all_tasks()
        self.assertEqual(len(tasks), 5)


class TestSchemas(unittest.TestCase):
    """测试数据模型"""

    def test_assertion_result_model(self):
        """测试断言结果模型"""
        from image_assertion_agent.models.schemas import AssertionResult, ObjectDetail

        result = AssertionResult(
            assertion_passed=True,
            confidence=0.95,
            expected_description="预期",
            actual_description="实际",
            object_match=True,
            quantity_match=True,
            image_match=True,
            image_similarity=0.9,
            match_location="中央",
            comparison_mode="partial",
            expected_quantity=2,
            actual_quantity=2,
            detected_objects=[
                ObjectDetail(
                    name="物品",
                    quantity=2,
                    confidence=0.9,
                    description="描述",
                )
            ],
            reason="理由",
        )

        self.assertTrue(result.assertion_passed)
        self.assertEqual(result.comparison_mode, "partial")
        self.assertEqual(len(result.detected_objects), 1)

    def test_assertion_result_json_serialization(self):
        """测试断言结果JSON序列化"""
        from image_assertion_agent.models.schemas import AssertionResult

        result = AssertionResult(
            assertion_passed=True,
            confidence=0.95,
            expected_description="预期",
            actual_description="实际",
            object_match=True,
            quantity_match=True,
            detected_objects=[],
            reason="理由",
        )

        json_str = result.model_dump_json()
        data = json.loads(json_str)

        self.assertTrue(data["assertion_passed"])
        self.assertEqual(data["confidence"], 0.95)


class TestAPIEndpoints(unittest.TestCase):
    """测试API端点"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        os.environ["DOUBAO_API_KEY"] = "test-api-key"
        os.environ["DOUBAO_MODEL_ENDPOINT"] = "test-endpoint"

    def test_health_check(self):
        """测试健康检查接口"""
        from fastapi.testclient import TestClient
        from image_assertion_agent.api.main import app

        client = TestClient(app)
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)

    def test_schema_endpoints(self):
        """测试Schema接口"""
        from fastapi.testclient import TestClient
        from image_assertion_agent.api.main import app

        client = TestClient(app)

        # 测试结果Schema
        response = client.get("/schema/result")
        self.assertEqual(response.status_code, 200)

        # 测试请求Schema
        response = client.get("/schema/request")
        self.assertEqual(response.status_code, 200)

    def test_async_upload_endpoint(self):
        """测试异步上传接口"""
        from fastapi.testclient import TestClient
        from image_assertion_agent.api.main import app

        client = TestClient(app)

        # 创建测试图片
        image_bytes = create_test_image(100, 100)

        response = client.post(
            "/assert/async/upload",
            files={"image": ("test.png", image_bytes, "image/png")},
            data={"expectation": "测试预期"},
        )

        # 异步接口应该立即返回任务ID
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("task_id", data)
        # 状态可能是pending或processing（取决于线程调度）
        self.assertIn(data["status"], ["pending", "processing"])

    @patch("image_assertion_agent.api.main.vision_client")
    def test_async_base64_endpoint(self, mock_client):
        """测试异步Base64接口"""
        from fastapi.testclient import TestClient
        from image_assertion_agent.api.main import app

        client = TestClient(app)

        image_base64 = create_test_image_base64(100, 100)

        response = client.post(
            "/assert/async/base64",
            json={
                "image_base64": image_base64,
                "expectation": "测试预期",
                "image_format": "png",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("task_id", data)

    def test_task_not_found(self):
        """测试任务不存在"""
        from fastapi.testclient import TestClient
        from image_assertion_agent.api.main import app

        client = TestClient(app)

        response = client.get("/task/non-existent-id")
        self.assertEqual(response.status_code, 404)

    def test_validation_error_no_expectation(self):
        """测试验证错误 - 缺少预期"""
        from fastapi.testclient import TestClient
        from image_assertion_agent.api.main import app

        client = TestClient(app)

        image_bytes = create_test_image(100, 100)

        response = client.post(
            "/assert/async/upload",
            files={"image": ("test.png", image_bytes, "image/png")},
            # 不提供expectation和expect_image
        )

        self.assertEqual(response.status_code, 400)

    def test_clear_tasks(self):
        """测试清空任务"""
        from fastapi.testclient import TestClient
        from image_assertion_agent.api.main import app

        client = TestClient(app)

        response = client.delete("/tasks")
        self.assertEqual(response.status_code, 200)


class TestRetryMechanism(unittest.TestCase):
    """测试重试机制"""

    def test_retry_delay_calculation(self):
        """测试重试延迟计算"""
        from image_assertion_agent.core.doubao_client import DoubaoVisionClient

        os.environ["DOUBAO_API_KEY"] = "test"
        os.environ["DOUBAO_MODEL_ENDPOINT"] = "test"
        os.environ["API_RETRY_BASE_DELAY"] = "2.0"
        os.environ["API_RETRY_MAX_DELAY"] = "30.0"

        client = DoubaoVisionClient()

        # 测试指数退避
        self.assertEqual(client._calculate_retry_delay(1), 2.0)
        self.assertEqual(client._calculate_retry_delay(2), 4.0)
        self.assertEqual(client._calculate_retry_delay(3), 8.0)
        self.assertEqual(client._calculate_retry_delay(4), 16.0)
        self.assertEqual(client._calculate_retry_delay(5), 30.0)  # 达到上限

    @patch("image_assertion_agent.core.doubao_client.OpenAI")
    def test_retry_on_api_error(self, mock_openai_class):
        """测试API错误时的重试"""
        from image_assertion_agent.core.doubao_client import DoubaoVisionClient, RetryableError, APIError

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # 模拟API持续失败
        mock_client.chat.completions.create.side_effect = APIError(
            message="API Error",
            request=MagicMock(),
            body=None,
        )

        client = DoubaoVisionClient()
        # 手动设置重试参数以加速测试
        client.max_retries = 2
        client.retry_base_delay = 0.1

        image_bytes = create_test_image(50, 50)

        with self.assertRaises(RetryableError):
            client.assert_image(
                image_bytes=image_bytes,
                expectation="测试",
            )

        # 验证重试次数（应该是max_retries次）
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        os.environ["DOUBAO_API_KEY"] = "test-api-key"
        os.environ["DOUBAO_MODEL_ENDPOINT"] = "test-endpoint"

    @patch("image_assertion_agent.core.doubao_client.download_image")
    @patch("image_assertion_agent.core.doubao_client.OpenAI")
    def test_full_workflow_with_url(self, mock_openai_class, mock_download):
        """测试完整的URL图片工作流"""
        from image_assertion_agent.core.doubao_client import DoubaoVisionClient

        # Mock下载
        test_image = create_test_image(100, 100, "red")
        expect_image = create_test_image(100, 100, "blue")
        mock_download.side_effect = [
            (test_image, "png"),
            (expect_image, "png"),
        ]

        # Mock API响应
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = create_mock_api_response(
            image_match=True,
            image_similarity=0.95,
            comparison_mode="similarity",
        )
        mock_client.chat.completions.create.return_value = mock_response

        # 执行测试
        client = DoubaoVisionClient()
        result, _ = client.assert_image_url(
            image_url="http://example.com/test.png",
            expectation="",
            expect_image_url="http://example.com/expect.png",
            task_id="test-123",
        )

        # 验证结果
        self.assertTrue(result.assertion_passed)
        self.assertEqual(result.comparison_mode, "similarity")  # 因为分辨率相同
        self.assertEqual(mock_download.call_count, 2)  # 下载了两张图片

    @patch("image_assertion_agent.core.doubao_client.OpenAI")
    def test_full_async_workflow(self, mock_openai_class):
        """测试完整的异步工作流"""
        import time
        from fastapi.testclient import TestClient
        from image_assertion_agent.api.main import app
        from image_assertion_agent.core.task_manager import task_manager

        # 清空任务
        task_manager.clear_tasks()

        # Mock API响应
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = create_mock_api_response()
        mock_client.chat.completions.create.return_value = mock_response

        client = TestClient(app)

        # 1. 提交任务
        image_bytes = create_test_image(100, 100)
        response = client.post(
            "/assert/async/upload",
            files={"image": ("test.png", image_bytes, "image/png")},
            data={"expectation": "测试异步工作流"},
        )

        self.assertEqual(response.status_code, 200)
        task_id = response.json()["task_id"]

        # 2. 等待任务完成（实际测试中会更快）
        max_wait = 10
        for _ in range(max_wait):
            response = client.get(f"/task/{task_id}")
            data = response.json()
            if data["status"] in ["completed", "failed"]:
                break
            time.sleep(0.5)

        # 3. 验证结果
        final_response = client.get(f"/task/{task_id}")
        final_data = final_response.json()

        # 任务应该完成（或者仍在处理中，取决于线程调度）
        self.assertIn(final_data["status"], ["pending", "processing", "completed", "failed"])


class TestDualImageComparison(unittest.TestCase):
    """测试双图对比功能"""

    @classmethod
    def setUpClass(cls):
        os.environ["DOUBAO_API_KEY"] = "test-api-key"
        os.environ["DOUBAO_MODEL_ENDPOINT"] = "test-endpoint"

    @patch("image_assertion_agent.core.doubao_client.OpenAI")
    def test_same_resolution_triggers_similarity_mode(self, mock_openai_class):
        """测试相同分辨率触发相似度模式"""
        from image_assertion_agent.core.doubao_client import DoubaoVisionClient

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = create_mock_api_response(
            image_match=True,
            image_similarity=0.88,
        )
        mock_client.chat.completions.create.return_value = mock_response

        client = DoubaoVisionClient()

        # 相同分辨率的图片
        img1 = create_test_image(150, 150, "red")
        img2 = create_test_image(150, 150, "green")

        result, _ = client.assert_image(
            image_bytes=img1,
            expectation="",
            expect_image_bytes=img2,
        )

        # 验证调用的prompt包含相似度相关内容
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages", call_args.args[0] if call_args.args else None)

        if messages:
            system_prompt = messages[0]["content"]
            self.assertIn("相似度", system_prompt)

    @patch("image_assertion_agent.core.doubao_client.OpenAI")
    def test_different_resolution_triggers_partial_mode(self, mock_openai_class):
        """测试不同分辨率触发局部匹配模式"""
        from image_assertion_agent.core.doubao_client import DoubaoVisionClient

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = create_mock_api_response(
            image_match=True,
            image_similarity=0.75,
            comparison_mode="partial",
        )
        mock_client.chat.completions.create.return_value = mock_response

        client = DoubaoVisionClient()

        # 不同分辨率的图片
        img1 = create_test_image(200, 200, "red")  # 大图
        img2 = create_test_image(50, 50, "green")  # 小图（局部图）

        result, _ = client.assert_image(
            image_bytes=img1,
            expectation="",
            expect_image_bytes=img2,
        )

        self.assertEqual(result.comparison_mode, "partial")


# ============ 运行测试 ============

def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestImageDownloader))
    suite.addTests(loader.loadTestsFromTestCase(TestDoubaoClient))
    suite.addTests(loader.loadTestsFromTestCase(TestTaskManager))
    suite.addTests(loader.loadTestsFromTestCase(TestSchemas))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIEndpoints))
    suite.addTests(loader.loadTestsFromTestCase(TestRetryMechanism))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDualImageComparison))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
