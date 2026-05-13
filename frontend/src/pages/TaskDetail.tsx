import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getTask, statusLabels, type TaskDetail as TD } from "../api/client";

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>();
  const [task, setTask] = useState<TD | null>(null);
  const [tab, setTab] = useState<"notes" | "subtitle">("notes");

  useEffect(() => {
    if (!id) return;
    let alive = true;
    const tick = async () => {
      try {
        const data = await getTask(id);
        if (alive) setTask(data);
      } catch {
        /* ignore */
      }
    };
    tick();
    const t = setInterval(tick, 3000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [id]);

  if (!task) return <div>加载中…</div>;

  const done = task.status === "completed";
  const failed = task.status === "failed";

  return (
    <div>
      <div className="mb-6">
        <Link to="/tasks" className="text-sm text-slate-500 hover:text-slate-900">← 返回任务列表</Link>
        <h1 className="text-2xl font-bold mt-2 break-all">{task.filename}</h1>
        <div className="text-sm text-slate-500 mt-1">
          {new Date(task.created_at).toLocaleString()}
          {task.duration_seconds != null && ` · ${Math.round(task.duration_seconds)} 秒`}
        </div>
      </div>

      {!done && !failed && (
        <div className="bg-white border rounded-xl p-6 mb-6">
          <div className="text-sm text-slate-700 mb-2">{statusLabels[task.status]}</div>
          <div className="h-2 bg-slate-100 rounded overflow-hidden">
            <div className="h-full bg-slate-900 transition-all" style={{ width: `${task.progress}%` }} />
          </div>
          <div className="text-xs text-slate-500 mt-2">{task.progress}%</div>
        </div>
      )}

      {failed && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-6 mb-6">
          <div className="font-semibold mb-2">处理失败</div>
          <pre className="whitespace-pre-wrap text-xs">{task.error}</pre>
        </div>
      )}

      {done && (
        <div>
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setTab("notes")}
              className={`px-4 py-2 rounded-md text-sm ${tab === "notes" ? "bg-slate-900 text-white" : "bg-white border"}`}
            >
              笔记
            </button>
            <button
              onClick={() => setTab("subtitle")}
              className={`px-4 py-2 rounded-md text-sm ${tab === "subtitle" ? "bg-slate-900 text-white" : "bg-white border"}`}
            >
              字幕 (SRT)
            </button>
            {task.notes_url && (
              <a
                href={task.notes_url}
                download
                className="ml-auto px-4 py-2 rounded-md text-sm bg-white border hover:bg-slate-50"
              >
                下载 .md
              </a>
            )}
            {task.subtitle_url && (
              <a
                href={task.subtitle_url}
                download
                className="px-4 py-2 rounded-md text-sm bg-white border hover:bg-slate-50"
              >
                下载 .srt
              </a>
            )}
          </div>

          <div className="bg-white border rounded-xl p-6">
            {tab === "notes" ? (
              <div className="prose-notes">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {task.notes_markdown ?? ""}
                </ReactMarkdown>
              </div>
            ) : (
              <pre className="text-sm whitespace-pre-wrap font-mono leading-6">
                {task.subtitle_srt}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
