#!/usr/bin/env python3
"""
启动图像视觉断言Agent服务
"""
import uvicorn

from config import settings

if __name__ == "__main__":
    print("=" * 50)
    print("图像视觉断言Agent")
    print("=" * 50)

    valid, error = settings.validate()
    if not valid:
        print(f"\n警告: {error}")
        print("\n请设置以下环境变量:")
        print("  export DOUBAO_API_KEY='your-api-key'")
        print("  export DOUBAO_MODEL_ENDPOINT='your-model-endpoint'")
        print("\n服务将以降级模式启动...\n")

    print(f"\n启动服务: http://{settings.HOST}:{settings.PORT}")
    print(f"API文档: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"调试模式: {settings.DEBUG}\n")

    uvicorn.run(
        "api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
