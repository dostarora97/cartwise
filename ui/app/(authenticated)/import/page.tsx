"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useRequiredAuth } from "@/lib/auth";
import { $api } from "@/lib/api/hooks";
import apiClient from "@/lib/api/client";
import { TopBar } from "@/components/top-bar";
import { MealPlanItem } from "@/components/meal-plan-item";
import { Icon } from "@/components/icon";
import { Spinner } from "@/components/spinner";

export default function ImportPage() {
  return (
    <Suspense>
      <ImportContent />
    </Suspense>
  );
}

type ImportState =
  | { status: "idle" }
  | { status: "importing" }
  | { status: "done"; persist: number; skip: number }
  | { status: "error"; phase: "preview" | "import"; requestId?: string; traceId?: string };

function buildIssueUrl(phase: string, requestId?: string, traceId?: string) {
  const description = `Import ${phase} failed.`;
  const reproduce = [
    `1. Open the import page`,
    `2. Error occurred during: ${phase}`,
    requestId && `- Request ID: \`${requestId}\``,
    traceId && `- Trace ID: \`${traceId}\``,
  ].filter(Boolean).join("\n");
  const params = new URLSearchParams({
    template: "bug_report.yml",
    description,
    reproduce,
  });
  return `https://github.com/dostarora97/cartwise/issues/new?${params}`;
}

function ImportContent() {
  useRequiredAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const token = searchParams.get("supplier");

  const [state, setState] = useState<ImportState>({ status: "idle" });

  const { data: preview, error: previewError, isLoading } = $api.useQuery(
    "get",
    "/api/v1/imports/preview",
    { params: { query: { supplier: token! } } },
    { enabled: !!token },
  );

  useEffect(() => {
    if (!token) {
      router.replace("/meal-plan");
    }
  }, [token, router]);

  async function handleImport() {
    if (!token) return;
    setState({ status: "importing" });
    try {
      const { data, error, response } = await apiClient.POST("/api/v1/imports/", {
        body: { supplier: token },
      });
      if (error) {
        setState({ status: "error", phase: "import", requestId: response.headers.get("X-Request-ID") ?? undefined, traceId: response.headers.get("X-Trace-ID") ?? undefined });
        return;
      }
      await queryClient.invalidateQueries({
        queryKey: ["get", "/api/v1/meal-plans"],
      });
      await queryClient.invalidateQueries({
        queryKey: ["get", "/api/v1/menu-items/"],
      });
      setState({
        status: "done",
        persist: data!.intents_applied.persist ?? 0,
        skip: data!.intents_applied.skip ?? 0,
      });
    } catch {
      setState({ status: "error", phase: "import" });
    }
  }

  const showCenter = isLoading || state.status === "importing" || state.status === "error" || state.status === "done" || previewError;

  return (
    <div className="flex flex-1 flex-col">
      <TopBar showBack onBack={() => router.push("/meal-plan")} />

      <div className="flex items-stretch justify-between border-b border-black">
        <span className="flex items-center p-3 text-2xl font-bold tracking-label uppercase leading-6">
          <Icon name="download" size={24} className="shrink-0 mr-3" />
          Import
        </span>
      </div>

      <main className={`flex flex-1 flex-col ${showCenter ? "items-center justify-center" : ""}`}>
        {isLoading && <Spinner />}

        {preview && state.status === "idle" && (
          <ul>
            {preview.items.map((item, i) => (
              <MealPlanItem key={i} name={item.name} mode="view" />
            ))}
          </ul>
        )}

        {state.status === "importing" && <Spinner />}

        {state.status === "done" && (
          <div className="flex flex-col items-center gap-4">
            <p className="text-base font-bold tracking-label uppercase">
              Completed
            </p>
            <p className="text-sm tracking-wider">
              {state.persist} items added, {state.skip} skipped
            </p>
          </div>
        )}

        {(state.status === "error" || (previewError && state.status === "idle")) && (
          <div className="flex flex-col items-center gap-4">
            <p className="text-xs text-red-600 tracking-wider">
              {state.status === "error" && state.phase === "import"
                ? "Import failed"
                : "Could not load import preview"}
            </p>
            {state.status === "error" && (state.requestId || state.traceId) && (
              <ul className="text-xs text-gray-400 font-mono">
                {state.requestId && <li>req: {state.requestId}</li>}
                {state.traceId && <li>trace: {state.traceId}</li>}
              </ul>
            )}
            <button
              onClick={state.status === "error" && state.phase === "import" ? handleImport : () => queryClient.invalidateQueries({ queryKey: ["get", "/api/v1/imports/preview"] })}
              className="border-2 border-black px-6 py-3 text-base font-bold tracking-label uppercase"
            >
              Retry
            </button>
            {state.status === "error" && (
              <a
                href={buildIssueUrl(state.phase, state.requestId, state.traceId)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-gray-400 underline"
              >
                Report issue
              </a>
            )}
          </div>
        )}
      </main>

      <div className="sticky bottom-0">
        {preview && state.status === "idle" && (
          <button
            onClick={handleImport}
            disabled={preview.total === 0}
            className="flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white disabled:bg-neutral-400"
          >
            Import
          </button>
        )}
        {state.status === "done" && (
          <button
            onClick={() => router.push("/meal-plan")}
            className="flex w-full items-center justify-center p-3 border-t border-black bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white"
          >
            OK
          </button>
        )}
      </div>
    </div>
  );
}
