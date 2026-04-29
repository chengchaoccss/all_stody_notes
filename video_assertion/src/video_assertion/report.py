"""Render a Report as JSON or a small standalone HTML page."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from jinja2 import Template

from .models import Report


_HTML_TEMPLATE = Template(
    """<!doctype html>
<html><head><meta charset="utf-8"><title>Video Assertion Report</title>
<style>
body{font-family:system-ui,sans-serif;margin:24px;color:#222}
h1{font-size:20px}
.summary{padding:8px 12px;border-radius:6px;margin-bottom:16px}
.pass{background:#e6f8ec;color:#0a6c2a}
.fail{background:#fdecea;color:#9a1c14}
.row{border-top:1px solid #ddd;padding:12px 0}
.k{font-weight:600}
.refs{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.refs img{height:80px;border:1px solid #ccc;border-radius:4px}
code{background:#f3f3f3;padding:0 4px;border-radius:3px}
</style></head><body>
<h1>Video Assertion Report</h1>
<p>Source: <code>{{ report.video_path }}</code> &middot; duration {{ '%.2f' % report.duration_sec }}s &middot; {{ report.scenes|length }} scenes &middot; {{ report.keyframes|length }} keyframes</p>
<div class="summary {{ 'pass' if report.passed else 'fail' }}">
  Overall: {{ 'PASS' if report.passed else 'FAIL' }} ({{ pass_count }}/{{ report.results|length }} assertions passed)
</div>
{% for r in report.results %}
<div class="row">
  <div><span class="k">[{{ r.kind.value }}]</span> {{ r.text }}
    &mdash; <span class="{{ 'pass' if r.passed else 'fail' }}">{{ 'PASS' if r.passed else 'FAIL' }}</span>
    (conf {{ '%.2f' % r.confidence }})</div>
  <div>{{ r.evidence }}</div>
  {% if r.evidence_refs and embed_images %}
  <div class="refs">
    {% for img in r.evidence_refs %}
      {% if img in inline_images %}
      <img src="data:image/jpeg;base64,{{ inline_images[img] }}" alt="{{ img }}"/>
      {% endif %}
    {% endfor %}
  </div>
  {% endif %}
</div>
{% endfor %}
</body></html>
"""
)


def write_json(report: Report, path: str | Path) -> Path:
    p = Path(path)
    p.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return p


def write_html(report: Report, path: str | Path, embed_images: bool = True) -> Path:
    p = Path(path)
    inline: dict[str, str] = {}
    if embed_images:
        for r in report.results:
            for ref in r.evidence_refs:
                rp = Path(ref)
                if rp.is_file() and rp.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                    inline[ref] = base64.b64encode(rp.read_bytes()).decode("ascii")
    html = _HTML_TEMPLATE.render(
        report=report,
        pass_count=sum(1 for r in report.results if r.passed),
        embed_images=embed_images,
        inline_images=inline,
    )
    p.write_text(html, encoding="utf-8")
    return p


def to_dict(report: Report) -> dict:
    return json.loads(report.model_dump_json())
