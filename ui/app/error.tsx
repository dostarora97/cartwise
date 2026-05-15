"use client";

import { useEffect } from "react";
import { ErrorBody } from "@/components/error-body";

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
    <div className="flex min-h-dvh flex-col">
      <main className="flex flex-1 flex-col items-center justify-center p-3">
        <ErrorBody
          message={error.message || "Something went wrong"}
          stack={error.stack}
          onRetry={reset}
        />
      </main>
    </div>
  );
}
