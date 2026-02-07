import { useState } from 'react';
import { ImageLightbox } from './ImageLightbox';

interface ImagePreviewProps {
  src: string;
  alt?: string;
  label?: string;
  labelColor?: 'blue' | 'purple';
}

export function ImagePreview({
  src,
  alt = 'Preview',
  label,
  labelColor = 'blue',
}: ImagePreviewProps) {
  const [showLightbox, setShowLightbox] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const labelStyles =
    labelColor === 'purple'
      ? 'bg-purple-500/90 text-white'
      : 'bg-accent/90 text-white';

  return (
    <>
      <div
        className="relative group cursor-pointer overflow-hidden rounded-xl bg-surface-2"
        onClick={() => setShowLightbox(true)}
      >
        {/* Skeleton loader */}
        {!loaded && (
          <div className="absolute inset-0 bg-surface-3 animate-pulse rounded-xl" />
        )}

        <img
          src={src}
          alt={alt}
          className={`w-full h-full object-cover transition-all duration-500 ease-[var(--ease-apple)] group-hover:scale-105 ${
            loaded ? 'opacity-100' : 'opacity-0'
          }`}
          style={{ aspectRatio: '4/3' }}
          onLoad={() => setLoaded(true)}
        />

        {/* Hover overlay */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-all duration-300 rounded-xl flex items-center justify-center">
          <div className="opacity-0 group-hover:opacity-100 transition-all duration-300 transform translate-y-2 group-hover:translate-y-0">
            <div className="w-10 h-10 rounded-full bg-white/90 flex items-center justify-center shadow-lg">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" className="text-text-primary">
                <path
                  d="M3 10.5V14a1 1 0 001 1h10a1 1 0 001-1v-3.5M9 3v8M5.5 7.5 9 11l3.5-3.5"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
          </div>
        </div>

        {/* Label */}
        {label && (
          <span
            className={`absolute top-2 left-2 px-2.5 py-1 rounded-md text-xs font-semibold ${labelStyles} shadow-sm`}
          >
            {label}
          </span>
        )}
      </div>

      {showLightbox && (
        <ImageLightbox
          src={src}
          alt={alt}
          onClose={() => setShowLightbox(false)}
        />
      )}
    </>
  );
}
