"""
Volcengine Ark (方舟) — Doubao chat completions.

The Ark API is OpenAI-compatible: POST {base_url}/chat/completions with
{model, messages}. We send the transcript with timestamps as user content
and ask for structured Markdown notes back.
"""
from __future__ import annotations

import httpx

from app.config import settings


SYSTEM_PROMPT = """你是一个专业的课程/会议/视频笔记整理助手。用户会提供带时间戳的语音转写文本，请按以下要求输出一份高质量的中文 Markdown 笔记：

1. 顶部一句话总结视频主题（加粗）。
2. 用 ## 一级标题划分章节，按讲述的主题逻辑重组，不要按时间顺序简单复述。
3. 每个章节下面用项符列出要点，保留关键名词 / 定义 / 数字。
4. 在重要的要点后面用 《(mm:ss)》 标出原始时间戳，方便回看。
5. 最后加一个 "## 重点回顾" 小节，3-5 条最重要的结论。
6. 保持中立、专业的叙述口吻，不要虚构讲者未提及的内容。
7. 输出只包含 Markdown 本体，不要额外的说明。"""


class DoubaoLLMError(RuntimeError):
    pass


def generate_notes(transcript: str, *, title_hint: str | None = None) -> str:
    if not settings.ark_api_key:
        raise DoubaoLLMError("ARK_API_KEY not configured")

    user_content = (
        f"视频文件名：{title_hint}\n\n" if title_hint else ""
    ) + f"以下是语音转写的带时间戳文本：\n\n{transcript}"

    payload = {
        "model": settings.ark_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {settings.ark_api_key}",
        "Content-Type": "application/json",
    }

    url = f"{settings.ark_base_url.rstrip('/')}/chat/completions"
    resp = httpx.post(url, headers=headers, json=payload, timeout=120.0)
    if resp.status_code >= 400:
        raise DoubaoLLMError(f"Ark API error {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as e:
        raise DoubaoLLMError(f"unexpected Ark response: {data}") from e
