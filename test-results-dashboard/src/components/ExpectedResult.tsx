import type { ExpectedResult as ExpectedResultType } from '../types';
import { ImagePreview } from './ImagePreview';

interface ExpectedResultProps {
  result: ExpectedResultType;
}

export function ExpectedResult({ result }: ExpectedResultProps) {
  if (result.type === 'image' && result.imageUrl) {
    return (
      <div className="flex flex-col gap-2">
        <ImagePreview
          src={result.imageUrl}
          alt="Expected result"
          label="Expected"
          labelColor="purple"
        />
      </div>
    );
  }

  // Text description type
  return (
    <div className="flex flex-col gap-2">
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-purple-50 text-purple-600 text-xs font-semibold w-fit">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
          <path d="M2 3h8M2 6h6M2 9h4" />
        </svg>
        Text Expected
      </span>
      <div className="p-3 rounded-xl bg-surface-2 border border-border-light max-h-40 overflow-y-auto">
        <p className="text-sm text-text-primary leading-relaxed whitespace-pre-line">
          {result.description}
        </p>
      </div>
    </div>
  );
}
