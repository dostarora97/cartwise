"use client";

import { useState, useRef, useImperativeHandle, forwardRef } from "react";
import { Chip } from "@/components/chip";

interface User {
  id: string;
  name: string;
}

interface ChipInputProps {
  participants: User[];
  selected: string[];
  onAdd: (userId: string) => void;
  onRemove: (userId: string) => void;
  /** User ID that cannot be removed when it's the sole selection */
  protectedId?: string;
  /** Called when the "show all" dropdown opens or closes */
  onShowAllChange?: (showing: boolean) => void;
}

export interface ChipInputHandle {
  toggleAll: () => void;
  isShowingAll: boolean;
}

export const ChipInput = forwardRef<ChipInputHandle, ChipInputProps>(
  function ChipInput({ participants, selected, onAdd, onRemove, protectedId, onShowAllChange }, ref) {
    const [query, setQuery] = useState("");
    const [open, setOpen] = useState(false);
    const [showAll, setShowAll] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);
    const backspaceTimestamps = useRef<number[]>([]);

    const participantMap = new Map(participants.map((u) => [u.id, u]));
    const selectedUsers = selected
      .map((id) => participantMap.get(id))
      .filter((u): u is User => u !== undefined);
    const unselected = participants.filter((u) => !selected.includes(u.id));
    const filtered = showAll
      ? unselected
      : unselected.filter((u) =>
          u.name.toLowerCase().includes(query.trim().toLowerCase()),
        );

    function closeDropdown() {
      setOpen(false);
      setShowAll(false);
      onShowAllChange?.(false);
    }

    useImperativeHandle(ref, () => ({
      toggleAll() {
        if (open && showAll) {
          closeDropdown();
        } else {
          setShowAll(true);
          setQuery("");
          setOpen(true);
          inputRef.current?.focus();
          onShowAllChange?.(true);
        }
      },
      get isShowingAll() {
        return open && showAll;
      },
    }));

    return (
      <div className="relative flex-1">
        <div
          className="flex flex-wrap gap-1 items-center"
          onClick={() => inputRef.current?.focus()}
        >
          {selectedUsers.map((u) => {
            const isProtected = selected.length === 1 && u.id === protectedId;
            return (
              <Chip
                key={u.id}
                label={u.name}
                onRemove={isProtected ? undefined : () => onRemove(u.id)}
              />
            );
          })}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setShowAll(false);
              setOpen(true);
            }}
            onKeyDown={(e) => {
              if (e.key === "Backspace" && query === "" && selected.length > 0) {
                const now = Date.now();
                const recent = backspaceTimestamps.current.filter((t) => now - t < 1000);
                recent.push(now);
                backspaceTimestamps.current = recent;
                if (recent.length >= 3) {
                  const lastId = selected[selected.length - 1];
                  if (lastId !== protectedId || selected.length > 1) {
                    onRemove(lastId);
                  }
                  backspaceTimestamps.current = [];
                }
              }
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(closeDropdown, 150)}
            placeholder={selected.length === 0 ? "Add member..." : ""}
            className="h-6 min-w-[4rem] flex-1 text-xs font-bold tracking-label uppercase leading-4 outline-none bg-transparent placeholder:text-gray-400 placeholder:font-normal placeholder:normal-case placeholder:tracking-normal"
          />
        </div>

        {open && (showAll || query.trim().length > 0) && filtered.length > 0 && (
          <div className="absolute left-0 right-0 top-full z-10 border border-black bg-white max-h-48 overflow-y-auto">
            {filtered.map((u) => (
              <button
                key={u.id}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  onAdd(u.id);
                  setQuery("");
                  closeDropdown();
                }}
                className="block w-full text-left p-3 text-xs font-bold tracking-label uppercase leading-6 border-b border-gray-200 last:border-b-0"
              >
                {u.name}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  },
);
