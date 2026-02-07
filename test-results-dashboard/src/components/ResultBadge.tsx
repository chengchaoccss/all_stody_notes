import type { TestStatus } from '../types';

interface ResultBadgeProps {
  status: TestStatus;
}

export function ResultBadge({ status }: ResultBadgeProps) {
  const isPass = status === 'pass';

  return (
    <div className="flex flex-col items-center gap-2">
      {/* Icon */}
      <div
        className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 ${
          isPass
            ? 'bg-pass-bg border-2 border-pass-border'
            : 'bg-fail-bg border-2 border-fail-border'
        }`}
      >
        {isPass ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-pass">
            <path
              d="M5 13l4 4L19 7"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-fail">
            <path
              d="M7 7l10 10M17 7 7 17"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </div>

      {/* Text */}
      <span
        className={`text-sm font-semibold tracking-wide uppercase ${
          isPass ? 'text-pass' : 'text-fail'
        }`}
      >
        {isPass ? 'Pass' : 'Fail'}
      </span>
    </div>
  );
}
