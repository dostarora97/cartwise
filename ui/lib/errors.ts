export function extractRequestIds(response: Response): {
  requestId?: string;
  traceId?: string;
} {
  return {
    requestId: response.headers.get("X-Request-ID") ?? undefined,
    traceId: response.headers.get("X-Trace-ID") ?? undefined,
  };
}

export function buildIssueUrl(opts: {
  message: string;
  requestId?: string;
  traceId?: string;
}) {
  const reproduce = [
    `Error: ${opts.message}`,
    opts.requestId && `- Request ID: \`${opts.requestId}\``,
    opts.traceId && `- Trace ID: \`${opts.traceId}\``,
  ]
    .filter(Boolean)
    .join("\n");
  const params = new URLSearchParams({
    template: "bug_report.yml",
    description: opts.message,
    reproduce,
  });
  return `https://github.com/dostarora97/cartwise/issues/new?${params}`;
}
