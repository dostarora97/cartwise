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
}

export function ChipInput({
  participants,
  selected,
  onAdd,
  onRemove,
}: ChipInputProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedUsers = participants.filter((u) => selected.includes(u.id));
  const filtered = participants.filter(
    (u) =>
      !selected.includes(u.id) &&
      u.name.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className="relative">
      <div
        className="flex flex-wrap gap-1 items-center"
        onClick={() => inputRef.current?.focus()}
      >
        {selectedUsers.map((u) => (
          <Chip key={u.id} label={u.name} onRemove={() => onRemove(u.id)} />
        ))}
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
          className="min-w-[4rem] flex-1 text-xs leading-4 outline-none bg-transparent placeholder:text-gray-400"
        />
      </div>

      {open && query.length > 0 && filtered.length > 0 && (
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
              className="block w-full text-left p-3 text-base leading-6 border-b border-gray-200 last:border-b-0"
            >
              {u.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
