/**
 * A rating shown as a colored number, optionally over a proportional bar.
 *
 * Color comes from where the value sits between `min` and `max`, so the same
 * component works for projected PPG, VOR, consistency and matchup ratings by
 * passing the appropriate domain.
 */
export function gradeColor(value: number, min: number, max: number): string {
  if (max <= min) return "#94a3b8";
  const t = Math.min(1, Math.max(0, (value - min) / (max - min)));
  if (t >= 0.8) return "#2ecc71";
  if (t >= 0.6) return "#82e0aa";
  if (t >= 0.4) return "#f1c40f";
  if (t >= 0.2) return "#f5b041";
  return "#e74c3c";
}

export default function GradeBar({
  value,
  min,
  max,
  decimals = 1,
  showBar = true,
  signed = false,
}: {
  value: number | null | undefined;
  min: number;
  max: number;
  decimals?: number;
  showBar?: boolean;
  signed?: boolean;
}) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return <span className="text-faint">--</span>;
  }

  const color = gradeColor(value, min, max);
  const pct =
    max > min
      ? Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100))
      : 0;
  const text =
    (signed && value > 0 ? "+" : "") + value.toFixed(decimals);

  return (
    <span className="inline-flex flex-col items-end gap-1">
      <span style={{ color }} className="font-semibold tabular-nums">
        {text}
      </span>
      {showBar && (
        <span className="block h-[3px] w-14 overflow-hidden rounded-full bg-border-soft">
          <span
            className="block h-full rounded-full"
            style={{ width: `${pct}%`, background: color }}
          />
        </span>
      )}
    </span>
  );
}
