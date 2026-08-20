"use client";

import { ChevronDown } from "lucide-react";

export default function SeasonSelect({
  value,
  onChange,
  seasons = [2026, 2025, 2024, 2023, 2022, 2021],
  label = "Season",
}: {
  value: number;
  onChange: (next: number) => void;
  seasons?: number[];
  label?: string;
}) {
  return (
    <label className="relative inline-flex items-center">
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="appearance-none rounded-md border border-border bg-surface py-1.5 pl-3 pr-8 text-sm text-text outline-none transition-colors hover:border-accent focus:border-accent"
      >
        {seasons.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      <ChevronDown
        size={14}
        className="pointer-events-none absolute right-2.5 text-muted"
      />
    </label>
  );
}
