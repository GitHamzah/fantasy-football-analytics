const COLORS: Record<string, string> = {
  QB: "#e74c3c",
  RB: "#2ecc71",
  WR: "#3498db",
  TE: "#f39c12",
  K: "#9b59b6",
  DEF: "#95a5a6",
  DST: "#95a5a6",
};

export function positionColor(position?: string | null): string {
  return COLORS[(position ?? "").toUpperCase()] ?? "#95a5a6";
}

export default function PositionBadge({
  position,
  size = "sm",
}: {
  position?: string | null;
  size?: "sm" | "lg";
}) {
  const label = (position ?? "--").toUpperCase();
  return (
    <span
      className={
        size === "lg"
          ? "inline-block rounded px-2.5 py-1 text-xs font-bold tracking-wide text-white"
          : "inline-block rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide text-white"
      }
      style={{ background: positionColor(position) }}
    >
      {label}
    </span>
  );
}
