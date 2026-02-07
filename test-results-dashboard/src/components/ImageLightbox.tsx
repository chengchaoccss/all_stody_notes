import { useEffect, useState, useCallback } from 'react';

interface ImageLightboxProps {
  src: string;
  alt?: string;
  onClose: () => void;
}

export function ImageLightbox({ src, alt = 'Image', onClose }: ImageLightboxProps) {
  const [closing, setClosing] = useState(false);

  const handleClose = useCallback(() => {
    setClosing(true);
    setTimeout(onClose, 200);
  }, [onClose]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [handleClose]);

  const handleDownload = async () => {
    try {
      const response = await fetch(src);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `test-screenshot-${Date.now()}.jpg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch {
      window.open(src, '_blank');
    }
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center p-8 ${
        closing ? 'animate-fade-out' : 'animate-fade-in'
      }`}
      style={{ backgroundColor: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(20px)' }}
      onClick={handleClose}
    >
      {/* Toolbar */}
      <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-6 py-4 z-10">
        <span className="text-white/70 text-sm font-medium">{alt}</span>
        <div className="flex items-center gap-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleDownload();
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 hover:bg-white/20 text-white/90 text-sm font-medium transition-all duration-200 cursor-pointer"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M8 2v9M4.5 7.5 8 11l3.5-3.5M3 13h10" />
            </svg>
            Download
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              window.open(src, '_blank');
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 hover:bg-white/20 text-white/90 text-sm font-medium transition-all duration-200 cursor-pointer"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 3H3v10h10v-3M9 2h5v5M14 2 7 9" />
            </svg>
            Original
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleClose();
            }}
            className="w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-all duration-200 cursor-pointer"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M4 4l10 10M14 4 4 14" />
            </svg>
          </button>
        </div>
      </div>

      {/* Image */}
      <img
        src={src}
        alt={alt}
        className={`max-w-[90vw] max-h-[85vh] object-contain rounded-lg shadow-2xl ${
          closing ? 'animate-lightbox-out' : 'animate-lightbox-in'
        }`}
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  );
}
