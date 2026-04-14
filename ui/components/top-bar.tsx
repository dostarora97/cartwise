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
    <header className="flex items-stretch justify-between border-b border-black">
      <div className="shrink-0">
        {showBack ? (
          <button onClick={onBack ?? (() => router.back())} className="flex h-full items-center justify-center p-3 bg-black">
            <Icon name="arrow_back_ios_new" size={24} className="text-white" />
          </button>
        ) : (
          <div className="w-12" />
        )}
      </div>

      <div className="flex items-center gap-1 h-12">
        <img src="/logo-grocery.avif" alt="" className="h-9 w-9 object-contain" />
        <img src="/logo-calculator.avif" alt="" className="h-9 w-9 object-contain" />
        <img src="/logo-pizza.avif" alt="" className="h-9 w-9 object-contain" />
      </div>

      <div className="w-12 shrink-0 flex items-stretch">{rightAction}</div>
    </header>
  );
}
