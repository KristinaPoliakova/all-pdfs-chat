'use client';

import { useId, useState, type KeyboardEvent } from 'react';

export function InlineEdit({
  initialValue,
  maxLength,
  onSubmit,
  onCancel,
}: {
  initialValue: string;
  maxLength: number;
  onSubmit: (value: string) => void;
  onCancel: () => void;
}) {
  const inputId = useId();
  const [value, setValue] = useState(initialValue);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      submit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onCancel();
    }
  };

  return (
    <div className="flex items-center gap-2">
      <label htmlFor={inputId} className="sr-only">
        Edit value
      </label>
      <input
        id={inputId}
        autoFocus
        value={value}
        maxLength={maxLength}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground outline-none focus:ring-2 focus:ring-[var(--color-accent-cyan)]"
      />
      <button
        type="button"
        onClick={submit}
        className="rounded-md bg-foreground px-2 py-1 text-xs font-medium text-background hover:opacity-90"
      >
        Save
      </button>
      <button
        type="button"
        onClick={onCancel}
        className="rounded-md border border-border px-2 py-1 text-xs text-foreground hover:bg-surface"
      >
        Cancel
      </button>
    </div>
  );
}
