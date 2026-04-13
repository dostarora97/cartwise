type Mode = "view" | "select";

interface MealPlanItemProps {
  name: string;
  mode: Mode;
  checked?: boolean;
  onToggle?: () => void;
  onTap?: () => void;
}

export function MealPlanItem({
  name,
  mode,
  checked,
  onToggle,
  onTap,
}: MealPlanItemProps) {
  return (
    <li className="flex items-center gap-4 border-b border-gray-200 py-5 last:border-b-0">
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
