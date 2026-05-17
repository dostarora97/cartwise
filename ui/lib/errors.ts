export interface ErrorContext {
  message: string;
  requestId?: string;
  traceId?: string;
  status?: number;
  stack?: string;
  pageUrl?: string;
  build?: string;
}

export type ApiError = Pick<ErrorContext, "message" | "requestId" | "traceId" | "status">;

export function extractRequestIds(response: Response): {
  requestId?: string;
  traceId?: string;
} {
  return {
    requestId: response.headers.get("X-Request-ID") ?? undefined,
    traceId: response.headers.get("X-Trace-ID") ?? undefined,
  };
}

export function toApiError(message: string, response: Response): ApiError {
  return {
    message,
    ...extractRequestIds(response),
    status: response.status,
  };
}

export function buildIssueUrl(ctx: ErrorContext): string {
  const reproduce = [
    `**Error:** ${ctx.message}`,
    ctx.status && `**HTTP Status:** ${ctx.status}`,
    ctx.pageUrl && `**Page:** ${ctx.pageUrl}`,
    ctx.requestId && `**Request ID:** \`${ctx.requestId}\``,
    ctx.traceId && `**Trace ID:** \`${ctx.traceId}\``,
    ctx.build && `**Build:** \`${ctx.build}\``,
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
