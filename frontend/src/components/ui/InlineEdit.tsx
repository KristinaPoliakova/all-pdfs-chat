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
        className="flex-1 rounded-[var(--r-md)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1 text-[var(--fs-sm)] text-[var(--text)] outline-none focus:ring-2 focus:ring-[var(--focus-ring)]"
      />
      <button
        type="button"
        onClick={submit}
        className="rounded-[var(--r-md)] bg-[var(--accent)] px-2 py-1 text-xs font-medium text-[var(--accent-ink)] transition-opacity hover:opacity-90"
      >
        Save
      </button>
      <button
        type="button"
        onClick={onCancel}
        className="rounded-[var(--r-md)] border border-[var(--border)] px-2 py-1 text-xs text-[var(--text)] transition-colors hover:bg-[var(--surface-2)]"
      >
        Cancel
      </button>
    </div>
  );
}
