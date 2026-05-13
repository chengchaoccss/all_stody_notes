# 视频转笔记 · video-to-notes

一个把视频自动转成结构化学习笔记的 Web 应用。

```
视频上传 → ffmpeg 提取音频 → 火山引擎豆包语音大模型 ASR (录音文件识别)
        → 生成 SRT 字幕 → 豆包大模型 (方舟 Ark) 生成 Markdown 笔记
```

## 技术栈

| 模块      | 选型                                                    |
| --------- | ------------------------------------------------------- |
| 前端      | React 18 + Vite + TypeScript + TailwindCSS              |
| 后端 API  | FastAPI + SQLAlchemy 2 + Pydantic v2                    |
| 异步任务  | Celery + Redis                                          |
| 数据库    | PostgreSQL 16                                           |
| 媒体处理  | FFmpeg                                                  |
| 语音识别  | 火山引擎 豆包语音大模型 — 录音文件识别 (auc)            |
| 笔记生成  | 火山方舟 (Ark) Doubao Chat Completion                   |
| 部署      | Docker Compose                                          |

## 项目结构

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # pydantic-settings 配置
│   │   ├── db.py
│   │   ├── api/tasks.py         # 上传 / 列表 / 详情 / 删除
│   │   ├── models/task.py       # ORM 模型
│   │   ├── schemas/task.py      # Pydantic 响应
│   │   ├── services/
│   │   │   ├── ffmpeg.py        # 提取音频 / 探测时长
│   │   │   ├── doubao_asr.py    # 火山引擎录音文件识别
│   │   │   ├── doubao_llm.py    # 方舟 chat completion
│   │   │   └── subtitle.py      # 转 SRT / plain transcript
│   │   └── workers/
│   │       ├── celery_app.py
│   │       └── pipeline.py      # 提取→识别→出笔记 全流程
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/client.ts
│   │   └── pages/
│   │       ├── Upload.tsx
│   │       ├── TaskList.tsx
│   │       └── TaskDetail.tsx
│   ├── Dockerfile + nginx.conf
│   ├── tailwind.config.js
│   └── vite.config.ts
├── docker-compose.yml
└── .env.example
```

## 快速开始

### 1. 准备火山引擎账号

需要两套凭证：

1. **豆包语音大模型 / 录音文件识别**
   - 控制台: <https://console.volcengine.com/speech/app>
   - 创建应用，取 `App ID`、`Access Token` 和 `Cluster`
2. **方舟 (Ark) — Doubao Chat**
   - 控制台: <https://console.volcengine.com/ark>
   - 创建 API Key；可选创建推理接入点 `ep-xxxxx` 或直接用公共模型名 `doubao-pro-32k`

### 2. 写入 `.env`

```bash
cp .env.example .env
# 编辑 .env 填入 VOLC_ASR_*、ARK_API_KEY、ARK_MODEL
```

> ⚠️ 注意：火山引擎 ASR 会通过 `PUBLIC_FILE_BASE_URL` 拉取你上传的音频。
> 本地开发可以用 `ngrok http 8000` 之类的隧道，把 `PUBLIC_FILE_BASE_URL`
> 设成隧道地址，例如 `https://xxx.ngrok-free.app/files`。生产推荐把音频
> 推到 TOS / OSS 之类的对象存储后拿到一个公网 URL。

### 3. 一键启动

```bash
docker compose up --build
```

启动后：
- 前端: <http://localhost:5173>
- API: <http://localhost:8000/api>
- API Docs: <http://localhost:8000/docs>

### 4. 本地开发（不走 Docker）

```bash
# 后端
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 起 Postgres / Redis（可单独 docker compose up db redis）
uvicorn app.main:app --reload &
celery -A app.workers.celery_app worker -l info

# 前端
cd frontend
npm install
npm run dev
```

## API

| 方法 | 路径                  | 说明                  |
| ---- | --------------------- | --------------------- |
| POST | `/api/tasks`          | 上传视频，创建任务    |
| GET  | `/api/tasks`          | 任务列表              |
| GET  | `/api/tasks/{id}`     | 任务详情 + 字幕/笔记  |
| DELETE | `/api/tasks/{id}`   | 删除任务及关联文件    |

任务状态机：
```
pending → extracting_audio → transcribing → generating_notes → completed
                                              └→ failed (任何环节)
```

## 后续可拓展

- 用对象存储 (TOS / OSS) 替代本地文件 + nginx 直传
- 用户系统 + 任务配额
- 分片上传 / 断点续传
- 实时字幕预览（流式 ASR）
- 笔记导出 PDF / 同步到 Notion / 飞书
