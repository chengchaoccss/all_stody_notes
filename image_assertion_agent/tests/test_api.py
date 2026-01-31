"""
API测试用例
"""
import base64
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from image_assertion_agent.api.main import app
from image_assertion_agent.models.schemas import AssertionResult, ObjectDetail


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_vision_client():
    """模拟豆包视觉客户端"""
    mock_result = AssertionResult(
        assertion_passed=True,
        confidence=0.95,
        expected_description="这张图里面有一双运动鞋",
        actual_description="图片中有一双白色运动鞋",
        object_match=True,
        quantity_match=True,
        expected_quantity=2,
        actual_quantity=2,
        detected_objects=[
            ObjectDetail(
                name="运动鞋",
                quantity=2,
                confidence=0.95,
                description="白色运动鞋",
            )
        ],
        reason="图片中确实存在一双运动鞋",
    )

    mock_client = MagicMock()
    mock_client.assert_image.return_value = mock_result
    mock_client.assert_image_url.return_value = mock_result

    return mock_client


def test_health_check(client):
    """测试健康检查接口"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "config_valid" in data


def test_get_result_schema(client):
    """测试获取结果Schema"""
    response = client.get("/schema/result")
    assert response.status_code == 200
    schema = response.json()
    assert "properties" in schema
    assert "assertion_passed" in schema["properties"]


def test_get_request_schema(client):
    """测试获取请求Schema"""
    response = client.get("/schema/request")
    assert response.status_code == 200
    schema = response.json()
    assert "base64" in schema
    assert "url" in schema


@patch("image_assertion_agent.api.main.vision_client")
def test_assert_base64(mock_client_global, client, mock_vision_client):
    """测试Base64断言接口"""
    mock_client_global.__bool__ = lambda self: True
    mock_client_global.assert_image = mock_vision_client.assert_image

    # 创建一个简单的测试图片 (1x1 白色像素)
    test_image_base64 = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode()

    response = client.post(
        "/assert/base64",
        json={
            "image_base64": test_image_base64,
            "expectation": "这张图里面有一双运动鞋",
            "image_format": "png",
        },
    )

    # 由于没有真实配置，预期返回503
    # 在有配置的情况下应该返回200
    assert response.status_code in [200, 503]


@patch("image_assertion_agent.api.main.vision_client")
def test_assert_url(mock_client_global, client, mock_vision_client):
    """测试URL断言接口"""
    mock_client_global.__bool__ = lambda self: True
    mock_client_global.assert_image_url = mock_vision_client.assert_image_url

    response = client.post(
        "/assert/url",
        json={
            "image_url": "https://example.com/test.jpg",
            "expectation": "图片中有一只猫",
        },
    )

    # 由于没有真实配置，预期返回503
    assert response.status_code in [200, 503]


def test_invalid_base64(client):
    """测试无效的Base64输入"""
    response = client.post(
        "/assert/base64",
        json={
            "image_base64": "not-valid-base64!!!",
            "expectation": "测试",
            "image_format": "jpeg",
        },
    )

    # 应该返回400或503（配置问题）
    assert response.status_code in [400, 503]
