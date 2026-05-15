"use client";

import { usePathname } from "next/navigation";
import { type ErrorContext, buildIssueUrl } from "@/lib/errors";

interface ErrorBodyProps {
  message: string;
  requestId?: string;
  traceId?: string;
  status?: number;
  stack?: string;
  onRetry?: () => void;
}

export function ErrorBody({ message, requestId, traceId, status, stack, onRetry }: ErrorBodyProps) {
  const pathname = usePathname();

  const ctx: ErrorContext = {
    message,
    requestId,
    traceId,
    status,
    stack,
    pageUrl: typeof window !== "undefined" ? window.location.href : pathname,
  };

  const meta = [
    requestId && `req: ${requestId}`,
    traceId && `trace: ${traceId}`,
    status && `status: ${status}`,
  ].filter(Boolean) as string[];

  return (
    <div className="flex flex-col items-center gap-4">
      <p className="text-xs text-red-600 tracking-wider">{message}</p>
      {meta.length > 0 && (
        <ul className="text-xs text-gray-400 font-mono">
          {meta.map((line) => <li key={line}>{line}</li>)}
        </ul>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="border-2 border-black px-6 py-3 text-base font-bold tracking-label uppercase"
        >
          Retry
        </button>
      )}
      <a
        href={buildIssueUrl(ctx)}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-gray-400 underline"
      >
        Report issue
      </a>
    </div>
  );
}
