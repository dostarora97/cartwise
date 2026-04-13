import { forwardRef } from "react";
import type { CSSProperties } from "react";
import type {
  DraggableAttributes,
  DraggableSyntheticListeners,
} from "@dnd-kit/core";
import { Icon } from "@/components/icon";

type Mode = "view" | "select" | "reorder";

interface MealPlanItemProps {
  name: string;
  mode: Mode;
  checked?: boolean;
  onToggle?: () => void;
  onTap?: () => void;
  /** Applied to the root `<li>` in reorder mode (transform / transition from @dnd-kit). */
  sortableRowStyle?: CSSProperties;
  /** Draggable a11y props from `useSortable`; must live on the same node as `sortableListeners` when using a handle. */
  sortableAttributes?: DraggableAttributes;
  sortableListeners?: DraggableSyntheticListeners;
  setSortableActivatorRef?: (element: HTMLButtonElement | null) => void;
  dragging?: boolean;
}

export const MealPlanItem = forwardRef<HTMLLIElement, MealPlanItemProps>(
  function MealPlanItem(
    {
      name,
      mode,
      checked,
      onToggle,
      onTap,
      sortableRowStyle,
      sortableAttributes,
      sortableListeners,
      setSortableActivatorRef,
      dragging,
    },
    ref,
  ) {
    return (
      <li
        ref={ref}
        style={mode === "reorder" ? sortableRowStyle : undefined}
        className={`flex items-center gap-4 border-b border-gray-200 py-5 ${
          dragging ? "opacity-50" : ""
        }`}
      >
        <div className="flex w-6 shrink-0 justify-center">
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
              ref={setSortableActivatorRef}
              aria-label="Drag to reorder"
              className="flex touch-none cursor-grab appearance-none items-center justify-center border-0 bg-transparent p-0 active:cursor-grabbing"
              {...(sortableAttributes ?? {})}
              {...(sortableListeners ?? {})}
            >
              <Icon
                name="drag_indicator"
                size={20}
                className="text-neutral-400"
              />
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
  },
);

MealPlanItem.displayName = "MealPlanItem";
