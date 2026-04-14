"use client";

import { useEffect } from "react";

export default function ErrorPage({
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
    <div className="flex min-h-screen flex-col">
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
    </div>
  );
}
