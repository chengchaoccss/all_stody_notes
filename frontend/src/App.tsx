import { Link, Route, Routes } from "react-router-dom";
import Upload from "./pages/Upload";
import TaskList from "./pages/TaskList";
import TaskDetail from "./pages/TaskDetail";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold">视频转笔记</Link>
          <nav className="flex gap-4 text-sm">
            <Link to="/" className="text-slate-600 hover:text-slate-900">上传</Link>
            <Link to="/tasks" className="text-slate-600 hover:text-slate-900">历史任务</Link>
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-8">
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/tasks" element={<TaskList />} />
          <Route path="/tasks/:id" element={<TaskDetail />} />
        </Routes>
      </main>
      <footer className="text-center text-xs text-slate-400 py-4">
        Powered by 火山引擎豆包语音 + 豆包大模型
      </footer>
    </div>
  );
}
