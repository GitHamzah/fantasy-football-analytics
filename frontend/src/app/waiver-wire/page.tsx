"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Suspense, useEffect, useMemo, useState } from "react";
import {
  Scoring,
  getSeasonLeaders,
  getWeeklyStats,
  tryGet,
} from "@/lib/api";
import GradeBar from "@/components/GradeBar";
import PlayerCard from "@/components/PlayerCard";
import PositionTabs from "@/components/PositionTabs";
import SeasonSelect from "@/components/SeasonSelect";
import SortableTable, {
  ColumnMeta,
  TableSkeleton,
} from "@/components/SortableTable";
import { useQueryState } from "@/components/useQueryState";

type TrendRow = {
  player_id: string;
  player_name: string;
  position: string;
  team: string | null;
  games: number;
  season_ppg: number;
  recent_ppg: number;
  trend: number;
};

function num(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const n = typeof v === "string" ? Number(v) : (v as number);
  return Number.isNaN(n) ? null : n;
}

/** How many leaders to pull weekly logs for. Each is one request, so keep it bounded. */
const POOL = 60;

function WaiverInner() {
  const [seasonStr, setSeason] = useQueryState("season", "2025");
  const [position, setPosition] = useQueryState("position", "ALL");
  const [scoringStr] = useQueryState("scoring", "ppr");
  const season = Number(seasonStr) || 2025;
  const scoring = scoringStr as Scoring;

  const [rows, setRows] = useState<TrendRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setRows(null);
    setError(null);
    setProgress(0);

    (async () => {
      const leaders = await tryGet(
        getSeasonLeaders(season, undefined, scoring, POOL),
      );
      if (cancelled) return;
      if (!leaders?.length) {
        setError(`No ${season} season leaders returned by the API.`);
        setRows([]);
        return;
      }

      // Bind the narrowed value: TypeScript loses the null check inside the
      // worker closure below.
      const pool = leaders;

      // Fetch weekly logs with a small concurrency limit so we do not open 60
      // sockets at once against a free-tier backend.
      const out: TrendRow[] = [];
      const CONCURRENCY = 6;
      let idx = 0;

      async function worker() {
        while (idx < pool.length && !cancelled) {
          const mine = pool[idx++];
          const weekly = await tryGet(
            getWeeklyStats(mine.player_id, season, scoring),
          );
          if (cancelled) return;
          setProgress((p) => p + 1);
          if (!weekly || weekly.length < 4) continue;

          const pts = weekly
            .slice()
            .sort((a, b) => a.week - b.week)
            .map((w) => num(w.fantasy_points) ?? 0);
          const seasonPpg = pts.reduce((a, b) => a + b, 0) / pts.length;
          const last3 = pts.slice(-3);
          const recentPpg = last3.reduce((a, b) => a + b, 0) / last3.length;

          out.push({
            player_id: mine.player_id,
            player_name: mine.player_name,
            position: mine.position,
            team: mine.team,
            games: pts.length,
            season_ppg: Number(seasonPpg.toFixed(1)),
            recent_ppg: Number(recentPpg.toFixed(1)),
            trend: Number((recentPpg - seasonPpg).toFixed(1)),
          });
        }
      }

      await Promise.all(
        Array.from({ length: CONCURRENCY }, () => worker()),
      );
      if (!cancelled) setRows(out);
    })();

    return () => {
      cancelled = true;
    };
  }, [season, scoring]);

  const filtered = useMemo(() => {
    if (!rows) return null;
    const base =
      position === "ALL" ? rows : rows.filter((r) => r.position === position);
    return [...base].sort((a, b) => b.trend - a.trend);
  }, [rows, position]);

  const columns = useMemo<ColumnDef<TrendRow, unknown>[]>(() => {
    const meta = (m: ColumnMeta) => m;
    return [
      {
        id: "rank",
        header: "#",
        accessorFn: (_r, i) => i + 1,
        enableSorting: false,
        cell: (c) => <span className="text-faint">{c.row.index + 1}</span>,
        meta: meta({ align: "left", width: 44 }),
      },
      {
        id: "player",
        header: "Player",
        accessorFn: (r) => r.player_name,
        cell: (c) => {
          const r = c.row.original;
          return (
            <PlayerCard
              playerId={r.player_id}
              name={r.player_name}
              position={r.position}
              team={r.team}
              scoring={scoring}
            />
          );
        },
        meta: meta({ align: "left", sticky: true, width: 250 }),
      },
      {
        id: "season_ppg",
        header: "Season PPG",
        accessorFn: (r) => r.season_ppg,
        cell: (c) => (
          <span className="tabular-nums text-muted">
            {(c.getValue() as number).toFixed(1)}
          </span>
        ),
        meta: meta({ group: "FORM" }),
      },
      {
        id: "recent_ppg",
        header: "Last 3 PPG",
        accessorFn: (r) => r.recent_ppg,
        cell: (c) => (
          <GradeBar value={c.getValue() as number} min={4} max={24} showBar={false} />
        ),
        meta: meta({ group: "FORM" }),
      },
      {
        id: "trend",
        header: "Trend",
        accessorFn: (r) => r.trend,
        cell: (c) => {
          const v = c.getValue() as number;
          const color =
            v > 3 ? "#2ecc71" : v > 0 ? "#82e0aa" : v < -3 ? "#e74c3c" : "#94a3b8";
          return (
            <span style={{ color }} className="font-semibold tabular-nums">
              {v > 0 ? "+" : ""}
              {v.toFixed(1)}
            </span>
          );
        },
        meta: meta({ group: "FORM" }),
      },
      {
        id: "games",
        header: "G",
        accessorFn: (r) => r.games,
        meta: meta({ group: "CONTEXT" }),
      },
    ];
  }, [scoring]);

  return (
    <>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Waiver Wire
            <span className="ml-2 font-light text-muted">{season}</span>
          </h1>
          <p className="mt-1 text-sm text-muted">
            Players whose last three weeks outpaced their season average. The
            widest positive gaps are heating up.
          </p>
        </div>
        <SeasonSelect
          value={season}
          onChange={(s) => setSeason(String(s))}
          seasons={[2025, 2024, 2023, 2022, 2021]}
        />
      </div>

      <div className="mb-4">
        <PositionTabs value={position} onChange={setPosition} />
      </div>

      {error && (
        <p className="mb-3 rounded-md border border-border bg-surface px-3 py-2 text-xs text-grade-bad">
          {error}
        </p>
      )}

      {!filtered ? (
        <>
          <p className="mb-2 text-xs text-muted">
            Reading weekly logs… {progress}/{POOL}
          </p>
          <TableSkeleton rows={12} cols={6} />
        </>
      ) : (
        <>
          <SortableTable
            data={filtered}
            columns={columns}
            emptyMessage={`No trending ${position === "ALL" ? "players" : position + "s"} for ${season}.`}
            maxHeight={720}
          />
          <p className="mt-2 text-xs text-faint">
            Computed client-side from the top {POOL} scorers&apos; weekly logs ·
            trend = last 3 weeks minus season average
          </p>
        </>
      )}
    </>
  );
}

export default function WaiverWirePage() {
  return (
    <Suspense fallback={<TableSkeleton rows={12} cols={6} />}>
      <WaiverInner />
    </Suspense>
  );
}
