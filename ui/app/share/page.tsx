"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { FileText, Upload, Loader2, CheckCircle } from "lucide-react";

function ShareContent() {
  const searchParams = useSearchParams();
  const received = searchParams.get("received") === "true";

  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const [status, setStatus] = useState<
    "idle" | "loading" | "received" | "uploading" | "done" | "error"
  >(received ? "loading" : "idle");
  const [error, setError] = useState<string>("");

  // Pick up the shared file from Cache API (set by service worker)
  useEffect(() => {
    if (!received) return;

    async function loadSharedFile() {
      try {
        const cache = await caches.open("shared-files");
        const response = await cache.match("/shared-invoice");

        if (response) {
          const blob = await response.blob();
          const name = response.headers.get("X-File-Name") || "invoice.pdf";
          const sharedFile = new File([blob], name, { type: "application/pdf" });
          setFile(sharedFile);
          setFileName(name);
          setStatus("received");

          // Clean up cache
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

  // Manual file picker
  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0];
    if (selected && selected.type === "application/pdf") {
      setFile(selected);
      setFileName(selected.name);
      setStatus("received");
    }
  }

  // Upload to backend
  async function handleProcess() {
    if (!file) return;

    setStatus("uploading");
    setError("");

    try {
      // TODO: Wire to actual backend API
      // For now, simulate processing
      await new Promise((resolve) => setTimeout(resolve, 2000));
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setStatus("error");
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold">CartWise</h1>
          <p className="text-muted-foreground">
            {status === "idle" && "Share or upload a grocery invoice PDF"}
            {status === "loading" && "Loading shared file..."}
            {status === "received" && "Invoice received"}
            {status === "uploading" && "Processing invoice..."}
            {status === "done" && "Invoice processed!"}
            {status === "error" && "Something went wrong"}
          </p>
        </div>

        {/* File preview */}
        {file && (
          <div className="flex items-center gap-3 rounded-lg border p-4">
            <FileText className="h-8 w-8 text-red-500 shrink-0" />
            <div className="min-w-0">
              <p className="font-medium truncate">{fileName}</p>
              <p className="text-sm text-muted-foreground">
                {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
          </div>
        )}

        {/* Loading spinner */}
        {status === "loading" && (
          <div className="flex justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Upload area (when no file) */}
        {status === "idle" && (
          <label className="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 cursor-pointer hover:border-primary transition-colors">
            <Upload className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Tap to select a PDF invoice
            </p>
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
          <Button onClick={handleProcess} className="w-full" size="lg">
            Process Invoice
          </Button>
        )}

        {/* Uploading state */}
        {status === "uploading" && (
          <Button disabled className="w-full" size="lg">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Processing...
          </Button>
        )}

        {/* Success */}
        {status === "done" && (
          <div className="text-center space-y-4">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto" />
            <p className="text-muted-foreground">
              Your invoice has been processed. View the splits in your
              dashboard.
            </p>
            <a href="/dashboard/orders">
              <Button variant="outline" className="w-full">
                View Orders
              </Button>
            </a>
          </div>
        )}

        {/* Error */}
        {status === "error" && (
          <div className="space-y-4">
            <p className="text-sm text-red-500 text-center">{error}</p>
            <Button
              onClick={() => setStatus("received")}
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
