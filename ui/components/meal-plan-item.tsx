import { Icon } from "@/components/icon";

type Mode = "view" | "select" | "reorder";

interface MealPlanItemProps {
  name: string;
  mode: Mode;
  checked?: boolean;
  onToggle?: () => void;
  onTap?: () => void;
  /** Row index for reorder mode; sets `data-meal-reorder-index` on the row. */
  reorderIndex?: number;
  onReorderPointerDown?: (e: React.PointerEvent<HTMLButtonElement>) => void;
  onReorderPointerMove?: (e: React.PointerEvent<HTMLButtonElement>) => void;
  onReorderPointerUp?: (e: React.PointerEvent<HTMLButtonElement>) => void;
  onReorderPointerCancel?: (e: React.PointerEvent<HTMLButtonElement>) => void;
  dragging?: boolean;
}

export function MealPlanItem({
  name,
  mode,
  checked,
  onToggle,
  onTap,
  reorderIndex,
  onReorderPointerDown,
  onReorderPointerMove,
  onReorderPointerUp,
  onReorderPointerCancel,
  dragging,
}: MealPlanItemProps) {
  return (
    <li
      data-meal-reorder-index={
        mode === "reorder" && reorderIndex !== undefined
          ? reorderIndex
          : undefined
      }
      className={`flex items-center gap-4 border-b border-gray-200 py-5 ${
        dragging ? "opacity-50" : ""
      }`}
    >
      <div className="w-6 shrink-0 flex justify-center">
        {mode === "view" && <span className="text-sm">-</span>}
        {mode === "select" && (
          <input
            type="checkbox"
            checked={checked}
            onChange={onToggle}
            className="h-5 w-5 appearance-none border-2 border-neutral-400 checked:border-neutral-800 checked:bg-neutral-800"
          />
        )}
        {mode === "reorder" && (
          <button
            type="button"
            aria-label="Drag to reorder"
            className="flex cursor-grab touch-none appearance-none items-center justify-center border-0 bg-transparent p-0 active:cursor-grabbing"
            onPointerDown={(e) => {
              e.preventDefault();
              e.currentTarget.setPointerCapture(e.pointerId);
              onReorderPointerDown?.(e);
            }}
            onPointerMove={(e) => {
              if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
              onReorderPointerMove?.(e);
            }}
            onPointerUp={(e) => {
              if (e.currentTarget.hasPointerCapture(e.pointerId)) {
                e.currentTarget.releasePointerCapture(e.pointerId);
              }
              onReorderPointerUp?.(e);
            }}
            onPointerCancel={(e) => {
              if (e.currentTarget.hasPointerCapture(e.pointerId)) {
                e.currentTarget.releasePointerCapture(e.pointerId);
              }
              onReorderPointerCancel?.(e);
            }}
          >
            <Icon name="drag_indicator" size={20} className="text-neutral-400" />
          </button>
        )}
      </div>

      {onTap ? (
        <button
          onClick={onTap}
          className="flex-1 text-left text-sm font-medium tracking-item"
        >
          {name}
        </button>
      ) : (
        <span className="flex-1 text-sm font-medium tracking-item">
          {name}
        </span>
      )}
    </li>
  );
}
