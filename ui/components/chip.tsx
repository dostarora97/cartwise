"use client";

interface ChipProps {
  label: string;
  onRemove?: () => void;
}

export function Chip({ label, onRemove }: ChipProps) {
  return (
    <span className="inline-flex h-6 items-center px-2 bg-black text-white text-xs font-bold tracking-label uppercase">
      {label}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="ml-1 text-white"
          aria-label={`Remove ${label}`}
        >
          ×
        </button>
      )}
    </span>
  );
}
