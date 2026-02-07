interface AIAnalysisProps {
  text: string;
}

/**
 * Renders AI analysis text with simple markdown-like formatting:
 * - **bold** for emphasis
 * - Lines starting with a number+dot become list items
 */
function formatAnalysisText(text: string) {
  const lines = text.split('\n');

  return lines.map((line, i) => {
    // Process bold markers **text**
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    const formattedParts = parts.map((part, j) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <span key={j} className="font-semibold text-text-primary bg-highlight-bg text-highlight-text px-1 py-0.5 rounded">
            {part.slice(2, -2)}
          </span>
        );
      }
      return <span key={j}>{part}</span>;
    });

    // Detect numbered list items
    const isListItem = /^\d+\.\s/.test(line.trim());

    if (isListItem) {
      return (
        <div key={i} className="flex gap-2 py-1">
          <span className="text-text-tertiary select-none shrink-0">
            {line.trim().match(/^\d+\./)?.[0]}
          </span>
          <span className="text-sm text-text-secondary leading-relaxed">
            {formattedParts}
          </span>
        </div>
      );
    }

    if (line.trim() === '') {
      return <div key={i} className="h-2" />;
    }

    return (
      <p key={i} className="text-sm text-text-secondary leading-relaxed py-0.5">
        {formattedParts}
      </p>
    );
  });
}

export function AIAnalysis({ text }: AIAnalysisProps) {
  return (
    <div className="flex flex-col gap-2">
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-blue-50 text-accent text-xs font-semibold w-fit">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="6" cy="6" r="4.5" />
          <path d="M6 4v2.5l1.5 1" />
        </svg>
        AI Analysis
      </span>
      <div className="p-3 rounded-xl bg-surface-2 border border-border-light max-h-44 overflow-y-auto">
        {formatAnalysisText(text)}
      </div>
    </div>
  );
}
