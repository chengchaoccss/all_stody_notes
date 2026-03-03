"""
视频关键帧提取引擎 — FastAPI 应用入口。

启动方式：
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging

from fastapi import FastAPI

from app.api import router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="视频关键帧提取引擎",
    description="支持时间采样和算法关键帧两种模式的视频关键帧提取 REST API 服务。",
    version="1.0.0",
)

# 注册路由
app.include_router(router)


@app.get("/health")
async def health_check() -> dict:
    """健康检查接口。"""
    return {"status": "ok"}
