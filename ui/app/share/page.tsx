"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  FileText,
  Upload,
  Loader2,
  CheckCircle,
  XCircle,
  Pencil,
  Users,
  IndianRupee,
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SplitGroup {
  amount: number;
  groceryItems: { upc: string; description: string; total: number }[];
  splitEquallyAmong: string[];
}

interface SplitResult {
  paidBy: string;
  splits: SplitGroup[];
}

interface OrderResult {
  id: string;
  status: string;
  result: SplitResult;
  snapshot: Record<string, unknown>;
}

function ShareContent() {
  const searchParams = useSearchParams();
  const received = searchParams.get("received") === "true";

  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const [status, setStatus] = useState<
    | "idle"
    | "loading"
    | "received"
    | "uploading"
    | "splits"
    | "approving"
    | "done"
    | "error"
  >(received ? "loading" : "idle");
  const [error, setError] = useState<string>("");
  const [orderResult, setOrderResult] = useState<OrderResult | null>(null);
  const [token, setToken] = useState<string>("");

  // Pick up the shared file from Cache API (set by service worker)
  useEffect(() => {
    if (!received) return;

    async function loadSharedFile() {
      try {
        const cache = await caches.open("shared-files");
        const response = await cache.match("/shared-invoice");

        if (response) {
          const blob = await response.blob();
          const name =
            response.headers.get("X-File-Name") || "invoice.pdf";
          const sharedFile = new File([blob], name, {
            type: "application/pdf",
          });
          setFile(sharedFile);
          setFileName(name);
          setStatus("received");
          await cache.delete("/shared-invoice");
        } else {
          setStatus("idle");
        }
      } catch {
        setStatus("idle");
      }
    }

    loadSharedFile();
  }, [received]);

  // Dev login on mount (temporary — will be replaced by Supabase Auth)
  useEffect(() => {
    async function devLogin() {
      try {
        const resp = await fetch(`${API_URL}/api/v1/auth/dev-login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: "dev@cartwise.local",
            name: "Dev User",
          }),
        });
        if (resp.ok) {
          const data = await resp.json();
          setToken(data.access_token);
        }
      } catch {
        // Backend not running — that's ok for now
      }
    }
    devLogin();
  }, []);

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0];
    if (selected && selected.type === "application/pdf") {
      setFile(selected);
      setFileName(selected.name);
      setStatus("received");
    }
  }

  // Upload to backend and get splits
  async function handleProcess() {
    if (!file || !token) return;

    setStatus("uploading");
    setError("");

    try {
      // Get all users to use as participants
      const usersResp = await fetch(`${API_URL}/api/v1/users/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const users = await usersResp.json();
      const participantIds = users.map(
        (u: { id: string }) => u.id
      );

      // Upload invoice
      const formData = new FormData();
      formData.append("file", file);
      formData.append("participant_ids", JSON.stringify(participantIds));

      const resp = await fetch(`${API_URL}/api/v1/orders/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(
          errData.detail || `Server error: ${resp.status}`
        );
      }

      const order = await resp.json();
      setOrderResult(order);
      setStatus("splits");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Something went wrong"
      );
      setStatus("error");
    }
  }

  // Approve splits → send to (mock) Splitwise
  async function handleApprove() {
    setStatus("approving");
    // TODO: Wire to Splitwise service
    // For now just mark as done
    await new Promise((r) => setTimeout(r, 1000));
    setStatus("done");
  }

  function handleReject() {
    // Reset to upload state
    setOrderResult(null);
    setFile(null);
    setFileName("");
    setStatus("idle");
  }

  const totalSplit =
    orderResult?.result?.splits?.reduce(
      (sum, s) => sum + s.amount,
      0
    ) ?? 0;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6">
      <div className="w-full max-w-lg space-y-6">
        {/* Header */}
        <div className="text-center space-y-1">
          <h1 className="text-3xl font-semibold tracking-tight">
            CartWise
          </h1>
          <p className="text-sm text-muted-foreground">
            {status === "idle" &&
              "Share or upload a grocery invoice PDF"}
            {status === "loading" && "Loading shared file..."}
            {status === "received" && "Invoice ready to process"}
            {status === "uploading" && "Analyzing invoice..."}
            {status === "splits" && "Review your splits"}
            {status === "approving" && "Sending to Splitwise..."}
            {status === "done" && "Splits created!"}
            {status === "error" && "Something went wrong"}
          </p>
        </div>

        {/* File preview */}
        {file && status !== "idle" && (
          <div className="flex items-center gap-3 rounded-xl border border-border/50 bg-card p-4">
            <FileText className="h-8 w-8 text-red-500 shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="font-medium truncate text-sm">
                {fileName}
              </p>
              <p className="text-xs text-muted-foreground">
                {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
          </div>
        )}

        {/* Loading spinner */}
        {status === "loading" && (
          <div className="flex justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Upload area */}
        {status === "idle" && (
          <label className="flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border/50 p-10 cursor-pointer hover:border-primary/50 transition-colors">
            <Upload className="h-10 w-10 text-muted-foreground/60" />
            <div className="text-center">
              <p className="text-sm font-medium">
                Tap to select invoice
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                PDF files only
              </p>
            </div>
            <input
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={handleFileSelect}
            />
          </label>
        )}

        {/* Process button */}
        {status === "received" && (
          <Button
            onClick={handleProcess}
            className="w-full h-12 text-base font-medium"
          >
            Process Invoice
          </Button>
        )}

        {/* Uploading state */}
        {status === "uploading" && (
          <div className="space-y-4">
            <Button disabled className="w-full h-12">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </Button>
            <p className="text-xs text-center text-muted-foreground">
              Extracting items, classifying, and computing splits
            </p>
          </div>
        )}

        {/* Split results */}
        {status === "splits" && orderResult?.result && (
          <div className="space-y-4">
            {/* Summary */}
            <div className="rounded-xl border border-border/50 bg-card p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-muted-foreground">
                  Total
                </span>
                <span className="text-lg font-semibold flex items-center">
                  <IndianRupee className="h-4 w-4" />
                  {totalSplit.toFixed(2)}
                </span>
              </div>
              <div className="text-xs text-muted-foreground">
                {orderResult.result.splits.length} split
                {orderResult.result.splits.length !== 1 ? "s" : ""}{" "}
                across members
              </div>
            </div>

            {/* Individual splits */}
            <div className="space-y-3">
              {orderResult.result.splits.map((split, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-border/50 bg-card p-4 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-muted-foreground" />
                      <span className="text-xs text-muted-foreground">
                        {split.splitEquallyAmong.length} member
                        {split.splitEquallyAmong.length !== 1
                          ? "s"
                          : ""}
                      </span>
                    </div>
                    <span className="font-semibold flex items-center">
                      <IndianRupee className="h-3.5 w-3.5" />
                      {split.amount.toFixed(2)}
                    </span>
                  </div>

                  {/* Items in this split */}
                  <div className="space-y-1">
                    {split.groceryItems.map((item, j) => (
                      <div
                        key={j}
                        className="flex items-center justify-between text-xs"
                      >
                        <span className="text-muted-foreground truncate flex-1 mr-2">
                          {item.description}
                        </span>
                        <span className="text-muted-foreground shrink-0">
                          ₹{item.total.toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>

                  {/* Member IDs (abbreviated) */}
                  <div className="flex flex-wrap gap-1">
                    {split.splitEquallyAmong.map((id) => (
                      <span
                        key={id}
                        className="inline-block rounded-full bg-muted px-2 py-0.5 text-[10px] font-mono text-muted-foreground"
                      >
                        {id.slice(0, 8)}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Action buttons */}
            <div className="flex gap-3 pt-2">
              <Button
                onClick={handleApprove}
                className="flex-1 h-12 text-base font-medium"
              >
                <CheckCircle className="mr-2 h-4 w-4" />
                Approve
              </Button>
              <Button
                onClick={handleReject}
                variant="outline"
                className="h-12 px-4"
              >
                <XCircle className="h-4 w-4" />
              </Button>
              <Button variant="outline" className="h-12 px-4" disabled>
                <Pencil className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {/* Approving state */}
        {status === "approving" && (
          <Button disabled className="w-full h-12">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Sending to Splitwise...
          </Button>
        )}

        {/* Success */}
        {status === "done" && (
          <div className="text-center space-y-4">
            <CheckCircle className="h-14 w-14 text-green-500 mx-auto" />
            <p className="text-sm text-muted-foreground">
              Splits have been sent to Splitwise.
            </p>
            <Button
              onClick={handleReject}
              variant="outline"
              className="w-full"
            >
              Process Another Invoice
            </Button>
          </div>
        )}

        {/* Error */}
        {status === "error" && (
          <div className="space-y-4">
            <p className="text-sm text-red-500 text-center">{error}</p>
            <Button
              onClick={() => setStatus(file ? "received" : "idle")}
              variant="outline"
              className="w-full"
            >
              Try Again
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function SharePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <ShareContent />
    </Suspense>
  );
}
