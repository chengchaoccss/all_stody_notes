import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listTasks, statusLabels, type Task } from "../api/client";

export default function TaskList() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const data = await listTasks();
        if (alive) setTasks(data);
      } finally {
        if (alive) setLoading(false);
      }
    };
    tick();
    const id = setInterval(tick, 3000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  if (loading) return <div>加载中…</div>;
  if (tasks.length === 0)
    return (
      <div className="text-slate-500">
        还没有任务，去 <Link to="/" className="underline">上传一个视频</Link>。
      </div>
    );

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">历史任务</h1>
      <div className="bg-white rounded-xl shadow-sm border divide-y">
        {tasks.map((t) => (
          <Link
            key={t.id}
            to={`/tasks/${t.id}`}
            className="block px-5 py-4 hover:bg-slate-50"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <div className="font-medium truncate">{t.filename}</div>
                <div className="text-xs text-slate-500 mt-1">
                  {new Date(t.created_at).toLocaleString()} ·{" "}
                  {t.duration_seconds
                    ? `${Math.round(t.duration_seconds)} 秒`
                    : "-"}
                </div>
              </div>
              <StatusBadge status={t.status} progress={t.progress} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

function StatusBadge({ status, progress }: { status: Task["status"]; progress: number }) {
  const color =
    status === "completed"
      ? "bg-emerald-100 text-emerald-700"
      : status === "failed"
        ? "bg-red-100 text-red-700"
        : "bg-amber-100 text-amber-700";
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs whitespace-nowrap ${color}`}>
      {statusLabels[status]}
      {status !== "completed" && status !== "failed" ? ` ${progress}%` : ""}
    </span>
  );
}
