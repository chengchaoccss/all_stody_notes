export type TaskStatus =
  | "pending"
  | "extracting_audio"
  | "transcribing"
  | "generating_notes"
  | "completed"
  | "failed";

export interface Task {
  id: string;
  filename: string;
  status: TaskStatus;
  progress: number;
  error: string | null;
  duration_seconds: number | null;
  created_at: string;
  updated_at: string;
}

export interface TaskDetail extends Task {
  subtitle_url: string | null;
  notes_url: string | null;
  notes_markdown: string | null;
  subtitle_srt: string | null;
}

const BASE = "/api";

export async function listTasks(): Promise<Task[]> {
  const r = await fetch(`${BASE}/tasks`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getTask(id: string): Promise<TaskDetail> {
  const r = await fetch(`${BASE}/tasks/${id}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function uploadVideo(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<Task> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const fd = new FormData();
    fd.append("file", file);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(xhr.responseText || `HTTP ${xhr.status}`));
      }
    };
    xhr.onerror = () => reject(new Error("network error"));

    xhr.open("POST", `${BASE}/tasks`);
    xhr.send(fd);
  });
}

export async function deleteTask(id: string): Promise<void> {
  const r = await fetch(`${BASE}/tasks/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error(await r.text());
}

export const statusLabels: Record<TaskStatus, string> = {
  pending: "等待中",
  extracting_audio: "提取音频",
  transcribing: "语音识别中",
  generating_notes: "生成笔记中",
  completed: "已完成",
  failed: "失败",
};
