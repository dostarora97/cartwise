import { Icon } from "@/components/icon";

type Mode = "view" | "select" | "reorder";

interface MealPlanItemProps {
  name: string;
  mode: Mode;
  checked?: boolean;
  onToggle?: () => void;
  onTap?: () => void;
  onDragStart?: () => void;
  onDragOver?: (e: React.DragEvent) => void;
  onDragEnd?: () => void;
  dragging?: boolean;
}

export function MealPlanItem({
  name,
  mode,
  checked,
  onToggle,
  onTap,
  onDragStart,
  onDragOver,
  onDragEnd,
  dragging,
}: MealPlanItemProps) {
  return (
    <li
      draggable={mode === "reorder"}
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDragEnd={onDragEnd}
      className={`flex items-center gap-4 border-b border-gray-200 py-5 ${
        mode === "reorder" ? "cursor-grab active:cursor-grabbing" : ""
      } ${dragging ? "opacity-50" : ""}`}
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
          <Icon name="drag_indicator" size={20} className="text-neutral-400" />
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
