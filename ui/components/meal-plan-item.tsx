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
    <li className="flex items-center border-b border-gray-200 last:border-b-0">
      {/* Icon container — owns all padding, is the touch target in select mode */}
      {mode === "view" && (
        <div className="p-3 shrink-0">
          <div className="w-6 h-0.5 bg-black" />
        </div>
      )}
      {mode === "select" && (
        <label className="flex p-3 shrink-0 cursor-pointer">
          <input
            type="checkbox"
            checked={checked}
            onChange={onToggle}
            className="h-6 w-6 appearance-none border-2 border-neutral-400 checked:border-black checked:bg-black checked:shadow-[inset_0_0_0_3px_white]"
          />
        </label>
      )}

      {/* Text — owns vertical + right padding, navigates on tap */}
      {onTap ? (
        <button
          onClick={onTap}
          className="flex-1 min-w-0 py-3 pr-3 text-left text-2xl font-medium tracking-item leading-6 truncate"
        >
          {name}
        </button>
      ) : (
        <span className="flex-1 min-w-0 py-3 pr-3 text-2xl font-medium tracking-item leading-6 truncate">
          {name}
        </span>
      )}
    </li>
  );
}
