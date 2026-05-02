"use client";

import { useState, useRef, useEffect } from "react";

const PROVIDERS: Record<string, { label: string; methods: string[] }> = {
  swiggy: { label: "Swiggy", methods: ["order"] },
  zomato: { label: "Zomato", methods: ["invoice"] },
};

const METHODS: Record<string, { label: string }> = {
  order: { label: "Order" },
  invoice: { label: "Invoice" },
};

interface BreadcrumbNavProps {
  provider: string | null;
  method: string | null;
  onProviderChange: (p: string | null) => void;
  onMethodChange: (m: string | null) => void;
}

export function BreadcrumbNav({
  provider,
  method,
  onProviderChange,
  onMethodChange,
}: BreadcrumbNavProps) {
  const [openDropdown, setOpenDropdown] = useState<
    "provider" | "method" | null
  >(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-select method when provider has only one option
  useEffect(() => {
    if (!provider || method) return;
    const methods = PROVIDERS[provider]?.methods ?? [];
    if (methods.length === 1) {
      onMethodChange(methods[0]);
    }
  }, [provider, method, onMethodChange]);

  useEffect(() => {
    if (!openDropdown) return;
    function handleMouseDown(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpenDropdown(null);
      }
    }
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [openDropdown]);

  // State 1: no provider selected — show provider dropdown
  if (!provider && !openDropdown) {
    return (
      <div ref={containerRef} className="border-b border-gray-200">
        <DropdownSelect
          options={Object.entries(PROVIDERS).map(([k, v]) => ({
            value: k,
            label: v.label,
          }))}
          placeholder="For"
          onSelect={(v) => {
            onProviderChange(v);
            setOpenDropdown(null);
          }}
        />
      </div>
    );
  }

  const availableMethods = provider ? PROVIDERS[provider]?.methods ?? [] : [];

  return (
    <div
      ref={containerRef}
      className="relative flex items-stretch border-b border-gray-200"
    >
      {/* Provider crumb */}
      {provider && (
        <button
          type="button"
          onClick={() =>
            setOpenDropdown(openDropdown === "provider" ? null : "provider")
          }
          className="shrink-0 p-3 text-base font-bold tracking-label uppercase leading-6 whitespace-nowrap underline underline-offset-4"
        >
          {PROVIDERS[provider]?.label ?? provider}
        </button>
      )}

      {/* Provider dropdown (open state) */}
      {openDropdown === "provider" && (
        <DropdownOverlay
          options={Object.entries(PROVIDERS).map(([k, v]) => ({
            value: k,
            label: v.label,
          }))}
          selected={provider}
          onSelect={(v) => {
            if (v !== provider) {
              onProviderChange(v);
              onMethodChange(null);
            }
            setOpenDropdown(null);
          }}
        />
      )}

      {/* Separator */}
      {provider && (
        <span className="flex shrink-0 items-center text-base leading-6 text-gray-400">
          /
        </span>
      )}

      {/* Method crumb (selected) */}
      {provider && method && (
        <button
          type="button"
          onClick={() =>
            setOpenDropdown(openDropdown === "method" ? null : "method")
          }
          className="shrink-0 p-3 text-base font-bold tracking-label uppercase leading-6 whitespace-nowrap underline underline-offset-4"
        >
          {METHODS[method]?.label ?? method}
        </button>
      )}

      {/* Method dropdown (open state) */}
      {openDropdown === "method" && (
        <DropdownOverlay
          options={availableMethods.map((m) => ({
            value: m,
            label: METHODS[m]?.label ?? m,
          }))}
          selected={method}
          onSelect={(v) => {
            if (v !== method) {
              onMethodChange(v);
            }
            setOpenDropdown(null);
          }}
        />
      )}

      {/* Method placeholder (not yet selected) */}
      {provider && !method && openDropdown !== "method" && (
        <div className="shrink-0">
          <DropdownSelect
            options={availableMethods.map((m) => ({
              value: m,
              label: METHODS[m]?.label ?? m,
            }))}
            placeholder="For"
            onSelect={(v) => {
              onMethodChange(v);
            }}
          />
        </div>
      )}
    </div>
  );
}

// --- Internal dropdown components ---

interface Option {
  value: string;
  label: string;
}

function DropdownSelect({
  options,
  placeholder,
  onSelect,
}: {
  options: Option[];
  placeholder: string;
  onSelect: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleMouseDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="p-3 text-base font-bold tracking-label uppercase leading-6 whitespace-nowrap underline decoration-dashed underline-offset-4 text-gray-500"
      >
        {placeholder}
      </button>
      {open && (
        <div className="absolute top-full left-0 z-10 min-w-full border border-black bg-white">
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => {
                onSelect(opt.value);
                setOpen(false);
              }}
              className="flex w-full items-center p-3 text-base font-bold tracking-label uppercase leading-6 hover:bg-gray-100 whitespace-nowrap"
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function DropdownOverlay({
  options,
  selected,
  onSelect,
}: {
  options: Option[];
  selected: string | null;
  onSelect: (value: string) => void;
}) {
  return (
    <div className="absolute top-full left-0 z-10 min-w-full border border-black bg-white">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onSelect(opt.value)}
          className={`flex w-full items-center p-3 text-base font-bold tracking-label uppercase leading-6 whitespace-nowrap ${
            opt.value === selected ? "bg-black text-white" : "hover:bg-gray-100"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
