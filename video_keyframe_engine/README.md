# 视频关键帧提取引擎 (Video Keyframe Engine)

基于 FastAPI + OpenCV 的视频关键帧提取服务，支持时间采样和多种算法关键帧提取模式。

## 功能特性

- **时间采样模式** — 按固定时间间隔精准跳帧采样
- **帧差法** — 基于相邻帧灰度差值检测关键帧
- **光流法** — 基于 Farneback 密集光流检测运动突变
- **场景检测** — 基于 HSV H+S 通道直方图 Bhattacharyya 距离检测场景切换（去掉 V 通道抗光照干扰）
- **流式处理** — 逐帧处理，不一次性加载全部帧到内存
- **异步任务** — 支持同步/异步两种调用模式，长视频不阻塞 API
- **路径安全** — 白名单目录校验，防止路径遍历攻击
- **模块化设计** — 纯 dict 注册表工厂模式，扩展新算法无需修改工厂代码

## 环境要求

- Python 3.9+

## 安装

```bash
cd video_keyframe_engine
pip install -r requirements.txt
```

## 启动服务

```bash
cd video_keyframe_engine
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 路径安全配置（生产环境推荐）

通过环境变量限制可访问的目录（多目录用 `:` 分隔）：

```bash
export VKE_ALLOWED_VIDEO_DIRS="/data/videos:/mnt/media"
export VKE_ALLOWED_OUTPUT_DIRS="/data/output"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

不设置时默认不限制路径（开发模式）。

服务启动后访问 API 文档：http://localhost:8000/docs

## API 调用示例

### 健康检查

```bash
curl http://localhost:8000/health
```

### 时间采样模式（每 2 秒取一帧）

```bash
curl -X POST http://localhost:8000/extract-frames \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/path/to/video.mp4",
    "mode": "time",
    "output_dir": "/path/to/output",
    "time_interval_sec": 2
  }'
```

### 帧差法

```bash
curl -X POST http://localhost:8000/extract-frames \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/path/to/video.mp4",
    "mode": "algorithm",
    "output_dir": "/path/to/output",
    "algorithm_type": "frame_diff",
    "algorithm_config": {
      "threshold": 0.3,
      "min_interval_sec": 1
    }
  }'
```

### 光流法

```bash
curl -X POST http://localhost:8000/extract-frames \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/path/to/video.mp4",
    "mode": "algorithm",
    "output_dir": "/path/to/output",
    "algorithm_type": "optical_flow",
    "algorithm_config": {
      "threshold": 0.3,
      "min_interval_sec": 1
    }
  }'
```

### 场景检测

```bash
curl -X POST http://localhost:8000/extract-frames \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/path/to/video.mp4",
    "mode": "algorithm",
    "output_dir": "/path/to/output",
    "algorithm_type": "scene_detect",
    "algorithm_config": {
      "threshold": 0.3,
      "min_interval_sec": 1
    }
  }'
```

### 返回示例

```json
{
  "status": "success",
  "total_frames_extracted": 18,
  "output_dir": "/path/to/output",
  "timestamps": [0.0, 1.033, 2.067, 3.1]
}
```

### 异步提取（推荐用于长视频）

```bash
# 提交异步任务
curl -X POST http://localhost:8000/extract-frames/async \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/path/to/video.mp4",
    "mode": "time",
    "output_dir": "/path/to/output",
    "time_interval_sec": 2
  }'
# 返回: {"task_id": "abc123...", "status": "pending", "message": "..."}

# 查询任务状态
curl http://localhost:8000/tasks/{task_id}
# 返回: {"task_id": "abc123...", "status": "completed", "result": {...}, "error": null}
```

## 输出目录结构

```
output_dir/
├── metadata.json
└── frames/
    ├── frame_0001_t000000ms.jpg
    ├── frame_0002_t001033ms.jpg
    └── frame_0003_t002067ms.jpg
```

## 项目结构

```
video_keyframe_engine/
├── app/
│   ├── main.py                          # FastAPI 应用入口
│   ├── api.py                           # REST API 路由
│   ├── config.py                        # 全局配置与数据模型
│   ├── extractor/
│   │   ├── base.py                      # 提取器抽象基类 + 工厂
│   │   ├── time_extractor.py            # 时间采样提取器
│   │   ├── frame_diff_extractor.py      # 帧差法提取器
│   │   ├── optical_flow_extractor.py    # 光流法提取器
│   │   └── scene_detect_extractor.py    # 场景检测提取器
│   └── utils/
│       ├── video_reader.py              # 视频读取与校验
│       ├── frame_writer.py              # 帧图片写入
│       └── metadata_writer.py           # 元数据 JSON 写入
├── requirements.txt
└── README.md
```

## 扩展指南

### 添加新算法

1. 在 `app/extractor/` 下创建新文件，继承 `BaseExtractor`
2. 实现 `extract` 生成器方法
3. 调用 `ExtractorFactory.register("your_key", YourExtractor)` 注册（无需修改工厂代码）

```python
from app.extractor.base import ExtractorFactory
from app.extractor.your_extractor import YourExtractor

ExtractorFactory.register("semantic", YourExtractor)
```

### 预留扩展点

- **AI 语义关键帧** — 实现新的 `BaseExtractor` 子类即可接入
- **图像断言 API** — 在 `extract_frames` 接口后处理阶段集成
- **批量视频处理** — 新增批量接口，内部循环调用提取逻辑
- **GPU 加速** — `BaseExtractor` 已预留 `use_gpu` 参数
