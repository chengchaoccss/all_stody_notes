import type { TestRecord } from '../types';
import { ImagePreview } from './ImagePreview';
import { ExpectedResult } from './ExpectedResult';
import { AIAnalysis } from './AIAnalysis';
import { ResultBadge } from './ResultBadge';

interface TestRowProps {
  record: TestRecord;
  index: number;
}

export function TestRow({ record, index }: TestRowProps) {
  return (
    <div
      className="test-row-enter group/row w-full bg-surface-1 border border-border-light rounded-2xl hover:border-border hover:shadow-lg transition-all duration-300 ease-[var(--ease-apple)]"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div className="grid grid-cols-[200px_1fr_1fr_100px_140px] gap-5 p-5 items-start">
        {/* Column 1: Original Screenshot */}
        <div className="flex flex-col gap-2">
          <ImagePreview
            src={record.screenshotUrl}
            alt={`Test ${record.id} screenshot`}
            label="Screenshot"
            labelColor="blue"
          />
          <span className="text-xs text-text-tertiary font-mono text-center">
            {record.id}
          </span>
        </div>

        {/* Column 2: Expected Result */}
        <div className="min-w-0">
          <ExpectedResult result={record.expectedResult} />
        </div>

        {/* Column 3: AI Analysis */}
        <div className="min-w-0">
          <AIAnalysis text={record.aiAnalysis} />
        </div>

        {/* Column 4: Test Result Badge */}
        <div className="flex items-center justify-center pt-4">
          <ResultBadge status={record.status} />
        </div>

        {/* Column 5: Timestamp */}
        <div className="flex flex-col items-end justify-start pt-4 gap-1">
          <span className="text-xs text-text-tertiary font-medium">Test Time</span>
          <span className="text-sm text-text-secondary font-mono tabular-nums">
            {record.timestamp.split(' ')[0]}
          </span>
          <span className="text-sm text-text-primary font-mono tabular-nums font-medium">
            {record.timestamp.split(' ')[1]}
          </span>
        </div>
      </div>
    </div>
  );
}
