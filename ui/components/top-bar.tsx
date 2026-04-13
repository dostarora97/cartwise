"use client";

import { useRouter } from "next/navigation";
import { Icon } from "@/components/icon";

interface TopBarProps {
  showBack?: boolean;
  onBack?: () => void;
  rightAction?: React.ReactNode;
}

export function TopBar({ showBack = false, onBack, rightAction }: TopBarProps) {
  const router = useRouter();

  return (
    <header className="flex h-14 items-center justify-between border-b border-black px-4">
      <div className="w-10">
        {showBack && (
          <button onClick={onBack ?? (() => router.back())}>
            <Icon name="chevron_left" size={24} />
          </button>
        )}
      </div>

      <span className="text-sm font-bold tracking-heading uppercase">
        CartWise
      </span>

      <div className="w-10 flex justify-end">{rightAction}</div>
    </header>
  );
}
