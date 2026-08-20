"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import {
  DefenseRow,
  Scoring,
  TeamDefenseRow,
  getDefensiveRankings,
  getTeamDefense,
  tryGet,
} from "@/lib/api";
import PositionTabs from "@/components/PositionTabs";
import SeasonSelect from "@/components/SeasonSelect";
import TeamLogo from "@/components/TeamLogo";
import { TableSkeleton } from "@/components/SortableTable";
import { useQueryState } from "@/components/useQueryState";
import { positionColor } from "@/components/PositionBadge";

const POSITIONS = ["QB", "RB", "WR", "TE"];

function num(v: unknown): number {
  const n = typeof v === "string" ? Number(v) : (v as number);
  return Number.isNaN(n) || v === null || v === undefined ? 0 : n;
}

/** Green = the defense concedes more than average, so a good matchup to attack. */
function heatColor(value: number, mean: number, spread: number): string {
  if (!spread) return "transparent";
  const z = Math.max(-1.6, Math.min(1.6, (value - mean) / spread));
  const t = (z + 1.6) / 3.2; // 0 = stingy, 1 = generous
  const alpha = 0.09 + Math.abs(z / 1.6) * 0.32;
  return t >= 0.5
    ? `rgba(46, 204, 113, ${alpha.toFixed(3)})`
    : `rgba(231, 76, 60, ${alpha.toFixed(3)})`;
}

function MatchupsInner() {
  const [seasonStr, setSeason] = useQueryState("season", "2025");
  const [position, setPosition] = useQueryState("position", "ALL");
  const [scoringStr] = useQueryState("scoring", "ppr");
  const season = Number(seasonStr) || 2025;
  const scoring = scoringStr as Scoring;

  const [defense, setDefense] = useState<DefenseRow[] | null>(null);
  const [teamDef, setTeamDef] = useState<TeamDefenseRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setDefense(null);
    setTeamDef(null);
    setError(null);

    (async () => {
      const [d, td] = await Promise.all([
        tryGet(getDefensiveRankings(season, scoring)),
        tryGet(getTeamDefense(season)),
      ]);
      if (cancelled) return;
      if (!d) {
        setError(`Could not load defensive rankings for ${season}.`);
      }
      setDefense(d ?? []);
      setTeamDef(td ?? []);
    })();

    return () => {
      cancelled = true;
    };
  }, [season, scoring]);

  // Pivot into team x position, and compute per-position mean/spread for coloring.
  const { teams, grid, stats } = useMemo(() => {
    const g = new Map<string, Record<string, number>>();
    for (const r of defense ?? []) {
      const row = g.get(r.defense) ?? {};
      row[r.position] = num(r.avg_pts_allowed);
      g.set(r.defense, row);
    }
    const st: Record<string, { mean: number; spread: number }> = {};
    for (const p of POSITIONS) {
      const vals = [...g.values()].map((r) => r[p]).filter((v) => v > 0);
      const mean = vals.length
        ? vals.reduce((a, b) => a + b, 0) / vals.length
        : 0;
      const variance = vals.length
        ? vals.reduce((a, b) => a + (b - mean) ** 2, 0) / vals.length
        : 0;
      st[p] = { mean, spread: Math.sqrt(variance) || 1 };
    }
    const shown = position === "ALL" ? POSITIONS : [position];
    const sortKey = shown[0];
    const sorted = [...g.keys()].sort(
      (a, b) => (g.get(b)?.[sortKey] ?? 0) - (g.get(a)?.[sortKey] ?? 0),
    );
    return { teams: sorted, grid: g, stats: st };
  }, [defense, position]);

  const shownPositions = position === "ALL" ? POSITIONS : [position];
  const selected = teamDef?.find((t) => t.team === selectedTeam) ?? null;

  return (
    <>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Matchups
            <span className="ml-2 font-light text-muted">{season}</span>
          </h1>
          <p className="mt-1 text-sm text-muted">
            Fantasy points allowed per game by each defense. Green means the
            defense gives up more than average, so attack it.
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

      {defense === null ? (
        <TableSkeleton rows={16} cols={5} />
      ) : teams.length === 0 ? (
        <div className="rounded-lg border border-border bg-surface px-4 py-10 text-center text-sm text-muted">
          No defensive data for {season}.
        </div>
      ) : (
        <div className="overflow-auto rounded-lg border border-border">
          <table className="tbl">
            <thead>
              <tr className="cols">
                <th className="lft stick">Defense</th>
                {shownPositions.map((p) => (
                  <th key={p} style={{ color: positionColor(p) }}>
                    vs {p}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {teams.map((t) => (
                <tr
                  key={t}
                  onClick={() => setSelectedTeam(t)}
                  className="cursor-pointer"
                >
                  <td className="lft stick">
                    <TeamLogo team={t} size={18} />
                  </td>
                  {shownPositions.map((p) => {
                    const v = grid.get(t)?.[p] ?? 0;
                    return (
                      <td
                        key={p}
                        style={{
                          background: heatColor(
                            v,
                            stats[p]?.mean ?? 0,
                            stats[p]?.spread ?? 1,
                          ),
                        }}
                      >
                        {v ? v.toFixed(1) : "--"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-2 text-xs text-faint">
        {teams.length} defenses · click a row to see that unit&apos;s pressure and
        coverage profile
      </p>

      {/* Team defense detail */}
      <section className="mt-8">
        <h2 className="mb-3 border-b border-border pb-2 text-sm font-semibold uppercase tracking-wider text-muted">
          Team defense profile
        </h2>

        {!teamDef?.length ? (
          <p className="text-sm text-muted">
            Team defense metrics are unavailable for {season}.
          </p>
        ) : !selected ? (
          <p className="text-sm text-muted">
            Select a defense from the table above.
          </p>
        ) : (
          <>
            <div className="mb-3 flex items-center gap-2">
              <TeamLogo team={selected.team} size={26} showAbbr={false} />
              <span className="text-lg font-semibold">{selected.team}</span>
              <span className="text-sm text-muted">
                {selected.games} games
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              {[
                ["Sacks / g", selected.sacks_pg],
                ["QB hits / g", selected.qb_hits_pg],
                ["INT / g", selected.interceptions_pg],
                ["Pass def / g", selected.pass_defended_pg],
                ["Forced FUM / g", selected.fumbles_forced_pg],
                ["Pressure / g", selected.pressure_pg],
              ].map(([label, value]) => (
                <div
                  key={String(label)}
                  className="rounded-lg border border-border bg-surface px-3 py-2.5"
                >
                  <div className="text-lg font-bold tabular-nums">
                    {num(value).toFixed(1)}
                  </div>
                  <div className="mt-0.5 text-[10px] uppercase tracking-wider text-faint">
                    {label}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </section>
    </>
  );
}

export default function MatchupsPage() {
  return (
    <Suspense fallback={<TableSkeleton rows={16} cols={5} />}>
      <MatchupsInner />
    </Suspense>
  );
}
