import { useState, useMemo } from 'react';
import { Header } from './components/Header';
import { TestRow } from './components/TestRow';
import { useAutoRefresh } from './hooks/useAutoRefresh';
import { mockTestRecords } from './data/mockData';
import type { TestRecord } from './types';

function fetchTestRecords(): TestRecord[] {
  // In production, replace with actual API call:
  // const res = await fetch('/api/test-records');
  // return res.json();
  return mockTestRecords;
}

function App() {
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { data, lastRefreshed, isRefreshing, refresh } = useAutoRefresh(
    fetchTestRecords,
    { interval: 5000, enabled: autoRefresh }
  );

  const records = data ?? [];

  const stats = useMemo(() => {
    const passCount = records.filter((r) => r.status === 'pass').length;
    return {
      total: records.length,
      pass: passCount,
      fail: records.length - passCount,
    };
  }, [records]);

  return (
    <div className="min-h-screen bg-surface-0">
      <Header
        totalCount={stats.total}
        passCount={stats.pass}
        failCount={stats.fail}
        lastRefreshed={lastRefreshed}
        isRefreshing={isRefreshing}
        onRefresh={refresh}
        autoRefresh={autoRefresh}
        onToggleAutoRefresh={() => setAutoRefresh((v) => !v)}
      />

      {/* Main content */}
      <main className="max-w-[1800px] mx-auto px-6 py-6">
        {/* Column Headers */}
        <div className="grid grid-cols-[200px_1fr_1fr_100px_140px] gap-5 px-5 pb-3">
          <span className="text-xs font-semibold text-text-tertiary uppercase tracking-wider">
            Screenshot
          </span>
          <span className="text-xs font-semibold text-text-tertiary uppercase tracking-wider">
            Expected Result
          </span>
          <span className="text-xs font-semibold text-text-tertiary uppercase tracking-wider">
            AI Analysis
          </span>
          <span className="text-xs font-semibold text-text-tertiary uppercase tracking-wider text-center">
            Result
          </span>
          <span className="text-xs font-semibold text-text-tertiary uppercase tracking-wider text-right">
            Time
          </span>
        </div>

        {/* Records List */}
        <div className="flex flex-col gap-3">
          {records.map((record, index) => (
            <TestRow key={record.id} record={record} index={index} />
          ))}
        </div>

        {/* Empty state */}
        {records.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24">
            <div className="w-16 h-16 rounded-full bg-surface-2 flex items-center justify-center mb-4">
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none" className="text-text-tertiary">
                <path
                  d="M8 16h16M16 8v16"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </div>
            <p className="text-text-secondary font-medium">No test records yet</p>
            <p className="text-text-tertiary text-sm mt-1">Records will appear here once tests are executed</p>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-center py-8 mt-4">
          <p className="text-xs text-text-tertiary">
            {records.length} records loaded &middot; Auto-refresh {autoRefresh ? 'enabled' : 'disabled'}
          </p>
        </div>
      </main>
    </div>
  );
}

export default App;
