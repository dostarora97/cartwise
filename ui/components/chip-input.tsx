"use client";

import { useState, useRef } from "react";
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
}

export function ChipInput({
  participants,
  selected,
  onAdd,
  onRemove,
  protectedId,
}: ChipInputProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const participantMap = new Map(participants.map((u) => [u.id, u]));
  const selectedUsers = selected
    .map((id) => participantMap.get(id))
    .filter((u): u is User => u !== undefined);
  const filtered = participants.filter(
    (u) =>
      !selected.includes(u.id) &&
      u.name.toLowerCase().includes(query.trim().toLowerCase()),
  );

  return (
    <div className="relative">
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
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder={selected.length === 0 ? "Add member..." : ""}
          className="h-6 min-w-[4rem] flex-1 text-xs font-bold tracking-label uppercase leading-4 outline-none bg-transparent placeholder:text-gray-400 placeholder:font-normal placeholder:normal-case placeholder:tracking-normal"
        />
      </div>

      {open && query.trim().length > 0 && filtered.length > 0 && (
        <div className="absolute left-0 right-0 top-full z-10 border border-black bg-white max-h-48 overflow-y-auto">
          {filtered.map((u) => (
            <button
              key={u.id}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onAdd(u.id);
                setQuery("");
                setOpen(false);
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
}
