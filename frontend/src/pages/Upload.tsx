import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadVideo } from "../api/client";

export default function Upload() {
  const nav = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [pct, setPct] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const task = await uploadVideo(file, setPct);
      nav(`/tasks/${task.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">上传视频生成学习笔记</h1>
      <p className="text-slate-500 mb-6">
        支持 mp4 / mov / mkv / webm 等常见格式。上传后会自动提取音频、识别语音、生成结构化 Markdown 笔记。
      </p>
      <form onSubmit={onSubmit} className="bg-white rounded-xl shadow-sm border p-6 space-y-4">
        <label className="block">
          <span className="text-sm text-slate-700">选择视频</span>
          <input
            type="file"
            accept="video/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            disabled={busy}
            className="mt-2 block w-full text-sm file:mr-3 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-slate-900 file:text-white hover:file:bg-slate-700"
          />
        </label>

        {file && (
          <div className="text-sm text-slate-600">
            {file.name} · {(file.size / 1024 / 1024).toFixed(1)} MB
          </div>
        )}

        {busy && (
          <div>
            <div className="h-2 bg-slate-100 rounded overflow-hidden">
              <div
                className="h-full bg-slate-900 transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            <div className="text-xs text-slate-500 mt-1">上传中 {pct}%</div>
          </div>
        )}

        {error && <div className="text-sm text-red-600">{error}</div>}

        <button
          type="submit"
          disabled={!file || busy}
          className="px-5 py-2 rounded-md bg-slate-900 text-white disabled:opacity-40"
        >
          {busy ? "正在上传…" : "开始处理"}
        </button>
      </form>
    </div>
  );
}
