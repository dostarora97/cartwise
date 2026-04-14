"use client";

import { DragDropProvider } from "@dnd-kit/react";
import { useSortable } from "@dnd-kit/react/sortable";
import { move } from "@dnd-kit/helpers";
import { cn } from "@/lib/utils";
import { Icon } from "@/components/icon";

function SortableItem({
  id,
  name,
  index,
}: {
  id: string;
  name: string;
  index: number;
}) {
  const { ref, handleRef, isDragging } = useSortable({ id, index });

  return (
    <li
      ref={ref}
      className={cn(
        "flex items-center border-b border-gray-200 last:border-b-0",
        isDragging && "opacity-50",
      )}
    >
      <button
        ref={handleRef}
        type="button"
        aria-label="Drag to reorder"
        className="p-3 shrink-0 flex touch-none cursor-grab active:cursor-grabbing"
      >
        <Icon name="drag_indicator" size={24} className="text-neutral-400" />
      </button>
      <span className="flex-1 min-w-0 py-3 pr-3 text-2xl font-medium tracking-item leading-6 truncate">
        {name}
      </span>
    </li>
  );
}

interface MealPlanReorderProps {
  items: { id: string; name: string }[];
  onReorder: (items: { id: string; name: string }[]) => void;
}

export default function MealPlanReorder({ items, onReorder }: MealPlanReorderProps) {
  return (
    <DragDropProvider
      onDragEnd={(event) => {
        if (event.canceled) return;
        onReorder(move(items, event));
      }}
    >
      <ul>
        {items.map((item, index) => (
          <SortableItem
            key={item.id}
            id={item.id}
            name={item.name}
            index={index}
          />
        ))}
      </ul>
    </DragDropProvider>
  );
}
