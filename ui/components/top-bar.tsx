"use client";

import { useRouter } from "next/navigation";
import Image from "next/image";
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
          <button onClick={onBack ?? (() => router.back())} aria-label="Go back" className="flex h-full items-center justify-center p-3 bg-black">
            <Icon name="arrow_back_ios_new" size={24} className="text-white" />
          </button>
        ) : (
          <div className="w-12" />
        )}
      </div>

      <div className="flex items-center gap-1 h-12">
        <Image src="/logo-grocery.avif" alt="" width={36} height={36} className="object-contain" unoptimized />
        <Image src="/logo-calculator.avif" alt="" width={36} height={36} className="object-contain" unoptimized />
        <Image src="/logo-pizza.avif" alt="" width={36} height={36} className="object-contain" unoptimized />
      </div>

      <div className="w-12 shrink-0 flex items-stretch">{rightAction}</div>
    </header>
  );
}
