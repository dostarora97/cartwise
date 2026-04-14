"use client";

interface ErrorModalProps {
  message: string;
  onDismiss: () => void;
}

export function ErrorModal({ message, onDismiss }: ErrorModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="error-title"
      aria-describedby="error-message"
    >
      <div className="bg-white border border-black p-3 mx-3 max-w-sm w-full">
        <p id="error-title" className="text-2xl font-bold tracking-label uppercase leading-6">
          Something went wrong
        </p>
        <p id="error-message" className="text-base leading-6 mt-3">{message}</p>
        <button
          onClick={onDismiss}
          className="mt-3 flex w-full items-center justify-center p-3 bg-black text-2xl font-bold tracking-label uppercase leading-6 text-white"
        >
          OK
        </button>
      </div>
    </div>
  );
}
