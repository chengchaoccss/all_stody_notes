interface HeaderProps {
  totalCount: number;
  passCount: number;
  failCount: number;
  lastRefreshed: Date;
  isRefreshing: boolean;
  onRefresh: () => void;
  autoRefresh: boolean;
  onToggleAutoRefresh: () => void;
}

export function Header({
  totalCount,
  passCount,
  failCount,
  lastRefreshed,
  isRefreshing,
  onRefresh,
  autoRefresh,
  onToggleAutoRefresh,
}: HeaderProps) {
  const passRate = totalCount > 0 ? Math.round((passCount / totalCount) * 100) : 0;

  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-surface-1/80 border-b border-border-light">
      <div className="max-w-[1800px] mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Left: Title */}
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-blue-400 flex items-center justify-center shadow-md">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="text-white">
                <path
                  d="M4 10l4 4 8-8"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-text-primary tracking-tight">
                Test Results Dashboard
              </h1>
              <p className="text-xs text-text-tertiary mt-0.5">
                Automated visual testing records
              </p>
            </div>
          </div>

          {/* Center: Stats */}
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-text-primary tabular-nums">{totalCount}</span>
              <span className="text-xs text-text-tertiary">Total</span>
            </div>
            <div className="w-px h-8 bg-border-light" />
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-pass" />
              <span className="text-lg font-semibold text-pass tabular-nums">{passCount}</span>
              <span className="text-xs text-text-tertiary">Pass</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-fail" />
              <span className="text-lg font-semibold text-fail tabular-nums">{failCount}</span>
              <span className="text-xs text-text-tertiary">Fail</span>
            </div>
            <div className="w-px h-8 bg-border-light" />
            <div className="flex items-center gap-2">
              <div className="w-16 h-2 rounded-full bg-surface-3 overflow-hidden">
                <div
                  className="h-full rounded-full bg-pass transition-all duration-700 ease-[var(--ease-apple)]"
                  style={{ width: `${passRate}%` }}
                />
              </div>
              <span className="text-sm font-semibold text-text-secondary tabular-nums">{passRate}%</span>
            </div>
          </div>

          {/* Right: Controls */}
          <div className="flex items-center gap-3">
            {/* Auto-refresh toggle */}
            <button
              onClick={onToggleAutoRefresh}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 cursor-pointer ${
                autoRefresh
                  ? 'bg-pass/10 text-pass border border-pass/20'
                  : 'bg-surface-2 text-text-tertiary border border-border-light'
              }`}
            >
              <div className={`w-1.5 h-1.5 rounded-full ${autoRefresh ? 'bg-pass animate-pulse' : 'bg-text-tertiary'}`} />
              Auto {autoRefresh ? 'ON' : 'OFF'}
            </button>

            {/* Manual refresh */}
            <button
              onClick={onRefresh}
              className="w-9 h-9 rounded-full bg-surface-2 hover:bg-surface-3 flex items-center justify-center transition-all duration-200 border border-border-light cursor-pointer"
              title="Refresh now"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className={`text-text-secondary transition-transform duration-500 ${isRefreshing ? 'animate-spin' : ''}`}
              >
                <path d="M2 8a6 6 0 0110.47-4M14 2v4h-4" />
                <path d="M14 8a6 6 0 01-10.47 4M2 14v-4h4" />
              </svg>
            </button>

            {/* Last refreshed */}
            <span className="text-xs text-text-tertiary tabular-nums min-w-[80px] text-right">
              {lastRefreshed.toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
