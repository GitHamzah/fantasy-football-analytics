"use client";

import { positionColor } from "./PositionBadge";

export default function PositionTabs({
  value,
  onChange,
  positions = ["QB", "RB", "WR", "TE"],
  includeAll = true,
}: {
  value: string;
  onChange: (next: string) => void;
  positions?: string[];
  includeAll?: boolean;
}) {
  const tabs = includeAll ? ["ALL", ...positions] : positions;

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {tabs.map((t) => {
        const active = value === t;
        const color = t === "ALL" ? "#3b82f6" : positionColor(t);
        return (
          <button
            key={t}
            onClick={() => onChange(t)}
            aria-pressed={active}
            className={
              "rounded-md border px-3 py-1.5 text-xs font-semibold tracking-wide transition-colors " +
              (active
                ? "text-white"
                : "border-border bg-surface text-muted hover:text-text")
            }
            style={
              active
                ? { background: color, borderColor: color }
                : undefined
            }
          >
            {t}
          </button>
        );
      })}
    </div>
  );
}
