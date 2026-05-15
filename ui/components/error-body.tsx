"use client";

import { buildIssueUrl } from "@/lib/errors";

interface ErrorBodyProps {
  message: string;
  requestId?: string;
  traceId?: string;
  onRetry?: () => void;
}

export function ErrorBody({ message, requestId, traceId, onRetry }: ErrorBodyProps) {
  return (
    <div className="flex flex-col items-center gap-4">
      <p className="text-xs text-red-600 tracking-wider">{message}</p>
      {(requestId || traceId) && (
        <ul className="text-xs text-gray-400 font-mono">
          {requestId && <li>req: {requestId}</li>}
          {traceId && <li>trace: {traceId}</li>}
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
        href={buildIssueUrl({ message, requestId, traceId })}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-gray-400 underline"
      >
        Report issue
      </a>
    </div>
  );
}
