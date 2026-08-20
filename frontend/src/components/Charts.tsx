"use client";

/**
 * Minimal inline-SVG charts. Charts are secondary to the tables here, so these
 * are deliberately small and dependency-free rather than a charting library.
 */

const AXIS = "#1e293b";
const MUTED = "#94a3b8";

function niceMax(v: number): number {
  if (v <= 0) return 10;
  const step = v > 100 ? 50 : v > 40 ? 10 : 5;
  return Math.ceil(v / step) * step;
}

export function LineChart({
  points,
  height = 200,
  projected,
  yLabel = "PPG",
}: {
  points: { x: number | string; y: number }[];
  height?: number;
  projected?: { x: number | string; y: number };
  yLabel?: string;
}) {
  const all = projected ? [...points, projected] : points;
  if (all.length === 0) {
    return <p className="text-sm text-muted">No data.</p>;
  }

  const padL = 34;
  const padB = 22;
  const padT = 10;
  const width = 100; // viewBox units, scales to container
  const maxY = niceMax(Math.max(...all.map((p) => p.y)));
  const n = all.length;
  const xAt = (i: number) =>
    padL + (n === 1 ? (width - padL) / 2 : (i * (width - padL - 4)) / (n - 1));
  const yAt = (v: number) =>
    padT + (1 - v / maxY) * (height - padT - padB);

  const linePts = points.map((p, i) => `${xAt(i)},${yAt(p.y)}`).join(" ");

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="h-[200px] w-full"
      role="img"
      aria-label={`${yLabel} by season`}
    >
      {[0, 0.5, 1].map((t) => (
        <g key={t}>
          <line
            x1={padL}
            x2={width}
            y1={yAt(maxY * t)}
            y2={yAt(maxY * t)}
            stroke={AXIS}
            strokeWidth={0.3}
          />
          <text
            x={padL - 4}
            y={yAt(maxY * t) + 3}
            fontSize={7}
            fill={MUTED}
            textAnchor="end"
          >
            {Math.round(maxY * t)}
          </text>
        </g>
      ))}

      <polyline
        points={linePts}
        fill="none"
        stroke="#3b82f6"
        strokeWidth={1.2}
        vectorEffect="non-scaling-stroke"
      />
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={xAt(i)} cy={yAt(p.y)} r={1.6} fill="#3b82f6" />
          <text
            x={xAt(i)}
            y={height - 6}
            fontSize={7}
            fill={MUTED}
            textAnchor="middle"
          >
            {p.x}
          </text>
        </g>
      ))}

      {projected && (
        <g>
          <line
            x1={xAt(n - 2)}
            y1={yAt(points[points.length - 1]?.y ?? 0)}
            x2={xAt(n - 1)}
            y2={yAt(projected.y)}
            stroke="#f1c40f"
            strokeWidth={1}
            strokeDasharray="2 2"
            vectorEffect="non-scaling-stroke"
          />
          <circle cx={xAt(n - 1)} cy={yAt(projected.y)} r={2.4} fill="#f1c40f" />
          <text
            x={xAt(n - 1)}
            y={height - 6}
            fontSize={7}
            fill="#f1c40f"
            textAnchor="middle"
          >
            {projected.x}
          </text>
        </g>
      )}
    </svg>
  );
}

export function BarChart({
  bars,
  height = 200,
  average,
  diverging = false,
}: {
  bars: { label: string | number; value: number; hint?: string }[];
  height?: number;
  average?: number;
  diverging?: boolean;
}) {
  if (!bars.length) return <p className="text-sm text-muted">No data.</p>;

  const padL = 30;
  const padB = 20;
  const padT = 8;
  const width = 100;
  const vals = bars.map((b) => b.value);
  const maxAbs = Math.max(...vals.map(Math.abs), 1);
  const maxY = diverging ? niceMax(maxAbs) : niceMax(Math.max(...vals, 0));
  const minY = diverging ? -maxY : 0;
  const span = maxY - minY;
  const plotH = height - padT - padB;
  const yAt = (v: number) => padT + (1 - (v - minY) / span) * plotH;
  const bw = (width - padL - 2) / bars.length;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="h-[200px] w-full"
      role="img"
      aria-label="Weekly values"
    >
      <line
        x1={padL}
        x2={width}
        y1={yAt(0)}
        y2={yAt(0)}
        stroke={AXIS}
        strokeWidth={0.4}
      />
      <text x={padL - 3} y={yAt(maxY) + 3} fontSize={7} fill={MUTED} textAnchor="end">
        {Math.round(maxY)}
      </text>
      {diverging && (
        <text x={padL - 3} y={yAt(minY) + 1} fontSize={7} fill={MUTED} textAnchor="end">
          {Math.round(minY)}
        </text>
      )}

      {bars.map((b, i) => {
        const x = padL + i * bw + bw * 0.15;
        const w = bw * 0.7;
        const top = b.value >= 0 ? yAt(b.value) : yAt(0);
        const h = Math.max(0.6, Math.abs(yAt(b.value) - yAt(0)));
        const fill = diverging
          ? b.value > 0.5
            ? "#2ecc71"
            : b.value < -0.5
              ? "#e74c3c"
              : "#64748b"
          : b.value >= 20
            ? "#2ecc71"
            : b.value < 8
              ? "#e74c3c"
              : "#3b82f6";
        return (
          <g key={i}>
            <rect x={x} y={top} width={w} height={h} fill={fill} rx={0.6}>
              <title>{b.hint ?? `${b.label}: ${b.value}`}</title>
            </rect>
            {bars.length <= 22 && (
              <text
                x={x + w / 2}
                y={height - 5}
                fontSize={6}
                fill={MUTED}
                textAnchor="middle"
              >
                {b.label}
              </text>
            )}
          </g>
        );
      })}

      {average !== undefined && (
        <line
          x1={padL}
          x2={width}
          y1={yAt(average)}
          y2={yAt(average)}
          stroke="#3b82f6"
          strokeWidth={0.6}
          strokeDasharray="3 2"
          vectorEffect="non-scaling-stroke"
        />
      )}
    </svg>
  );
}
