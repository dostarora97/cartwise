"use client";

import { useEffect } from "react";
import "./globals.css";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="en" className="h-full">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap"
        />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&icon_names=account_circle,add,arrow_back_ios_new,check,chevron_right,close,delete,drag_indicator,edit,fork_spoon,login,logout,more_horiz,open_in_new,receipt_long,search,settings&display=swap"
        />
      </head>
      <body className="min-h-full flex flex-col font-mono bg-white text-black" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
        <main className="flex flex-1 flex-col items-center justify-center p-3">
          <span className="text-2xl font-bold tracking-heading uppercase leading-6">
            Something went wrong
          </span>
          <p className="mt-3 text-base leading-6 text-gray-500">
            {error.message}
          </p>
        </main>
        <button
          onClick={reset}
          className="sticky bottom-0 flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white"
        >
          Try again
        </button>
      </body>
    </html>
  );
}
