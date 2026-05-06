"use client";

import { useRef } from "react";
import { Icon } from "@/components/icon";

interface InvoiceUploadProps {
  file: File | null;
  onFileChange: (f: File | null) => void;
}

export function InvoiceUpload({ file, onFileChange }: InvoiceUploadProps) {
  const fileRef = useRef<HTMLInputElement>(null);

  return (
    <div className="flex items-stretch border-b border-gray-200">
      <label className="flex items-center gap-3 p-3 flex-1 min-w-0 cursor-pointer">
        <Icon name={file ? "description" : "upload_file"} size={24} />
        <span className="text-base leading-6 truncate">
          {file ? file.name : "Invoice"}
        </span>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
        />
      </label>
      {file && (
        <button
          type="button"
          onClick={() => {
            onFileChange(null);
            if (fileRef.current) fileRef.current.value = "";
          }}
          aria-label="Remove file"
          className="flex items-center justify-center p-3"
        >
          <Icon name="delete" size={24} />
        </button>
      )}
    </div>
  );
}
