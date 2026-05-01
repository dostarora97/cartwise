"use client";

import { useState } from "react";

interface ConfirmDeleteDialogProps {
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export function ConfirmDeleteDialog({ onConfirm, onCancel, loading }: ConfirmDeleteDialogProps) {
  const [input, setInput] = useState("");

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="delete-title"
      aria-describedby="delete-message"
    >
      <div className="bg-white border border-black p-3 mx-3 max-w-sm w-full">
        <p id="delete-title" className="text-2xl font-bold tracking-label uppercase leading-6">
          Delete Account
        </p>
        <p id="delete-message" className="text-base leading-6 mt-3">
          This will permanently delete your account and all your data. This cannot be undone.
        </p>
        <input
          type="text"
          placeholder="Type delete to confirm"
          value={input}
          onChange={(e) => setInput(e.target.value.toLowerCase())}
          className="mt-3 w-full border border-black p-3 text-base tracking-wider"
          autoFocus
        />
        <div className="mt-3 flex gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="flex-1 border border-black p-3 text-base font-bold tracking-label uppercase"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={input !== "delete" || loading}
            className="flex-1 flex items-center justify-center bg-black p-3 text-base font-bold tracking-label uppercase text-white disabled:opacity-30"
          >
            {loading ? <div className="size-5 animate-spin rounded-full border-[3px] border-white border-t-transparent" /> : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}
