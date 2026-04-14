"use client";

import { useEffect } from "react";
import { JetBrains_Mono } from "next/font/google";
import "./globals.css";

const mono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

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
    <html lang="en" className={`${mono.variable} h-full`}>
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap"
        />
      </head>
      <body className="min-h-full flex flex-col font-mono bg-white text-black">
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
