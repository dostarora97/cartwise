export interface ErrorContext {
  message: string;
  requestId?: string;
  traceId?: string;
  stack?: string;
  pageUrl?: string;
}

export function extractRequestIds(response: Response): {
  requestId?: string;
  traceId?: string;
} {
  return {
    requestId: response.headers.get("X-Request-ID") ?? undefined,
    traceId: response.headers.get("X-Trace-ID") ?? undefined,
  };
}

export function buildIssueUrl(ctx: ErrorContext): string {
  const reproduce = [
    `**Error:** ${ctx.message}`,
    ctx.pageUrl && `**Page:** ${ctx.pageUrl}`,
    ctx.requestId && `**Request ID:** \`${ctx.requestId}\``,
    ctx.traceId && `**Trace ID:** \`${ctx.traceId}\``,
    ctx.stack && `**Stack:**\n\`\`\`\n${ctx.stack}\n\`\`\``,
  ]
    .filter(Boolean)
    .join("\n");
  const params = new URLSearchParams({
    template: "bug_report.yml",
    description: ctx.message,
    reproduce,
  });
  return `https://github.com/dostarora97/cartwise/issues/new?${params}`;
}
