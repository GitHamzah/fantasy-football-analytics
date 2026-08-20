"use client";

import { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import {
  PfrPlayerRow,
  PlayerDetailRow,
  Projection,
  Scoring,
  ScheduleStrength,
  SeasonStats,
  TrajectoryEntry,
  WeekStats,
  getPfrPlayerStats,
  getPlayerDetail,
  getProjections,
  getSeasonStats,
  getTeamSchedule,
  getTrajectory,
  getWeeklyStats,
  tryGet,
} from "@/lib/api";
import { BarChart, LineChart } from "@/components/Charts";
import MatchupRating from "@/components/MatchupRating";
import PositionBadge from "@/components/PositionBadge";
import SeasonSelect from "@/components/SeasonSelect";
import SortableTable, { TableSkeleton } from "@/components/SortableTable";
import TeamLogo from "@/components/TeamLogo";
import { useQueryState } from "@/components/useQueryState";

const TARGET_SEASON = 2026;

function num(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const n = typeof v === "string" ? Number(v) : (v as number);
  return Number.isNaN(n) ? null : n;
}

function Metric({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface px-4 py-3">
      <div
        className={
          "text-xl font-bold tabular-nums " + (accent ? "text-accent" : "")
        }
      >
        {value}
      </div>
      <div className="mt-0.5 text-[10px] uppercase tracking-wider text-faint">
        {label}
      </div>
    </div>
  );
}

function Section({
  title,
  children,
  note,
}: {
  title: string;
  children: React.ReactNode;
  note?: string;
}) {
  return (
    <section className="mt-8">
      <h2 className="mb-3 border-b border-border pb-2 text-sm font-semibold uppercase tracking-wider text-muted">
        {title}
      </h2>
      {note && <p className="mb-3 text-xs text-faint">{note}</p>}
      {children}
    </section>
  );
}

function PlayerInner() {
  const params = useParams<{ slug: string }>();
  const playerId = decodeURIComponent(params.slug);
  const [scoringStr] = useQueryState("scoring", "ppr");
  const scoring = scoringStr as Scoring;

  const [detail, setDetail] = useState<PlayerDetailRow | null>(null);
  const [traj, setTraj] = useState<TrajectoryEntry[] | null>(null);
  const [seasons, setSeasons] = useState<SeasonStats[] | null>(null);
  const [proj, setProj] = useState<Projection | null>(null);
  const [pfr, setPfr] = useState<PfrPlayerRow[] | null>(null);
  const [sched, setSched] = useState<ScheduleStrength | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [weekSeason, setWeekSeason] = useState<number>(2025);
  const [weekly, setWeekly] = useState<WeekStats[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      const [d, t, s, pr, adv] = await Promise.all([
        tryGet(getPlayerDetail(playerId)),
        tryGet(getTrajectory(playerId, scoring)),
        tryGet(getSeasonStats(playerId, undefined, scoring)),
        tryGet(getProjections(TARGET_SEASON, undefined, scoring, 300)),
        tryGet(getPfrPlayerStats(playerId)),
      ]);
      if (cancelled) return;

      if (!d && !t) {
        setError("Could not load this player from the API.");
        setLoading(false);
        return;
      }

      setDetail(d);
      setTraj(t);
      setSeasons(s);
      setPfr(adv);
      const mine = pr?.find((p) => p.player_id === playerId) ?? null;
      setProj(mine);

      const latest = t && t.length ? t[t.length - 1].season : 2025;
      setWeekSeason(latest);

      const team = mine?.team ?? d?.current_team ?? (t?.length ? t[t.length - 1].team : null);
      const pos = mine?.position ?? d?.position ?? (t?.length ? t[t.length - 1].position : null);
      if (team && pos && ["QB", "RB", "WR", "TE"].includes(pos)) {
        const sc = await tryGet(
          getTeamSchedule(team, TARGET_SEASON, pos, scoring),
        );
        if (!cancelled) setSched(sc);
      }

      setLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [playerId, scoring]);

  useEffect(() => {
    let cancelled = false;
    setWeekly(null);
    (async () => {
      const w = await tryGet(getWeeklyStats(playerId, weekSeason, scoring));
      if (!cancelled) setWeekly(w ?? []);
    })();
    return () => {
      cancelled = true;
    };
  }, [playerId, weekSeason, scoring]);

  const position =
    proj?.position ?? detail?.position ?? traj?.[traj.length - 1]?.position ?? null;
  const team =
    proj?.team ?? detail?.current_team ?? traj?.[traj.length - 1]?.team ?? null;
  const name =
    detail?.player_name ?? proj?.player_name ?? traj?.[0]?.player_name ?? playerId;

  const seasonCols = useMemo<ColumnDef<SeasonStats, unknown>[]>(() => {
    if (!seasons?.length) return [];
    const preferred = [
      "season",
      "games_played",
      "total_points",
      "ppg",
      "passing_yards",
      "passing_tds",
      "rushing_yards",
      "rushing_tds",
      "receptions",
      "targets",
      "receiving_yards",
      "receiving_tds",
    ];
    const present = preferred.filter((k) => k in seasons[0]);
    return present.map((k) => ({
      id: k,
      header: k.replace(/_/g, " "),
      accessorFn: (r: SeasonStats) => num(r[k]),
      cell: (c) => {
        const v = c.getValue() as number | null;
        if (v === null) return <span className="text-faint">--</span>;
        return (
          <span className="tabular-nums">
            {k === "season" ? v : Number.isInteger(v) ? v : v.toFixed(1)}
          </span>
        );
      },
      meta: { align: k === "season" ? "left" : "right" },
    })) as ColumnDef<SeasonStats, unknown>[];
  }, [seasons]);

  const weeklyCols = useMemo<ColumnDef<WeekStats, unknown>[]>(() => {
    if (!weekly?.length) return [];
    const preferred = [
      "week",
      "opponent_team",
      "fantasy_points",
      "passing_yards",
      "passing_tds",
      "rushing_yards",
      "rushing_tds",
      "receptions",
      "targets",
      "receiving_yards",
      "receiving_tds",
    ];
    const present = preferred.filter((k) => k in weekly[0]);
    return present.map((k) => ({
      id: k,
      header: k === "opponent_team" ? "opp" : k.replace(/_/g, " "),
      accessorFn: (r: WeekStats) =>
        k === "opponent_team" ? (r[k] as string) : num(r[k]),
      cell: (c) => {
        const v = c.getValue();
        if (v === null || v === undefined)
          return <span className="text-faint">--</span>;
        if (k === "opponent_team")
          return <TeamLogo team={String(v)} size={16} />;
        const n = v as number;
        return (
          <span className="tabular-nums">
            {Number.isInteger(n) ? n : n.toFixed(1)}
          </span>
        );
      },
      meta: {
        align: k === "week" || k === "opponent_team" ? "left" : "right",
      },
    })) as ColumnDef<WeekStats, unknown>[];
  }, [weekly]);

  if (error) {
    return (
      <div className="rounded-lg border border-border bg-surface px-4 py-12 text-center">
        <p className="text-sm text-grade-bad">{error}</p>
        <Link href="/" className="mt-3 inline-block text-sm text-accent hover:underline">
          Back to rankings
        </Link>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="skeleton h-8 w-72" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-20" />
          ))}
        </div>
        <TableSkeleton rows={6} cols={8} />
      </div>
    );
  }

  const weeklyVals = (weekly ?? [])
    .map((w) => num(w.fantasy_points))
    .filter((v): v is number => v !== null);
  const weeklyAvg = weeklyVals.length
    ? weeklyVals.reduce((a, b) => a + b, 0) / weeklyVals.length
    : undefined;

  const pfrLatest = pfr?.length ? pfr[pfr.length - 1] : null;

  return (
    <>
      <Link href="/" className="text-xs text-muted hover:text-accent">
        &larr; Rankings
      </Link>

      {/* Header */}
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <PositionBadge position={position} size="lg" />
        <h1 className="text-3xl font-bold tracking-tight">{name}</h1>
        <TeamLogo team={team} size={30} showAbbr={false} />
        <span className="text-lg text-muted">{team ?? "FA"}</span>
      </div>

      <p className="mt-2 text-sm text-muted">
        {[
          detail?.age ? `Age ${detail.age}` : null,
          detail?.draft_round
            ? `Round ${detail.draft_round}${detail.draft_pick ? `, pick ${detail.draft_pick}` : ""}${detail.draft_year ? ` (${detail.draft_year})` : ""}`
            : detail?.rookie_year
              ? `Rookie year ${detail.rookie_year}`
              : null,
          detail?.college,
        ]
          .filter(Boolean)
          .join(" · ") || "Biographical detail unavailable"}
      </p>

      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Metric
          label={`${TARGET_SEASON} proj PPG`}
          value={proj ? proj.projected_ppg.toFixed(1) : "--"}
          accent
        />
        <Metric
          label={`${TARGET_SEASON} proj total`}
          value={proj ? proj.projected_total.toFixed(0) : "--"}
        />
        <Metric
          label="Career seasons"
          value={traj?.length ? String(traj.length) : "--"}
        />
        <Metric
          label="Best season PPG"
          value={
            traj?.length
              ? Math.max(...traj.map((t) => num(t.ppg) ?? 0)).toFixed(1)
              : "--"
          }
        />
      </div>

      {/* Season stats + trajectory */}
      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h2 className="mb-3 border-b border-border pb-2 text-sm font-semibold uppercase tracking-wider text-muted">
            Season stats
          </h2>
          {seasons?.length ? (
            <SortableTable
              data={seasons}
              columns={seasonCols}
              initialSort={[{ id: "season", desc: true }]}
            />
          ) : (
            <p className="text-sm text-muted">No season stats available.</p>
          )}
        </div>
        <div>
          <h2 className="mb-3 border-b border-border pb-2 text-sm font-semibold uppercase tracking-wider text-muted">
            Career trajectory
          </h2>
          {traj?.length ? (
            <>
              <LineChart
                points={traj.map((t) => ({
                  x: t.season,
                  y: num(t.ppg) ?? 0,
                }))}
                projected={
                  proj
                    ? { x: TARGET_SEASON, y: proj.projected_ppg }
                    : undefined
                }
              />
              <p className="mt-1 text-xs text-faint">
                Blue line is actual PPG by season
                {proj ? "; the yellow point is the 2026 projection." : "."}
              </p>
            </>
          ) : (
            <p className="text-sm text-muted">No trajectory available.</p>
          )}
        </div>
      </div>

      {/* Weekly */}
      <Section title="Weekly performance">
        <div className="mb-3 flex items-center gap-3">
          <SeasonSelect
            value={weekSeason}
            onChange={setWeekSeason}
            seasons={traj?.length ? traj.map((t) => t.season).reverse() : [2025]}
          />
          {weeklyAvg !== undefined && (
            <span className="text-xs text-muted">
              Average{" "}
              <span className="font-semibold text-accent tabular-nums">
                {weeklyAvg.toFixed(1)}
              </span>{" "}
              points per game
            </span>
          )}
        </div>

        {weekly === null ? (
          <div className="skeleton h-[200px]" />
        ) : weekly.length ? (
          <>
            <BarChart
              bars={weekly.map((w) => ({
                label: w.week,
                value: num(w.fantasy_points) ?? 0,
                hint: `Week ${w.week}${w.opponent_team ? ` vs ${w.opponent_team}` : ""}: ${(num(w.fantasy_points) ?? 0).toFixed(1)}`,
              }))}
              average={weeklyAvg}
            />
            <p className="mt-1 text-xs text-faint">
              Green bars are 20+ point weeks, red are under 8. Dashed line is the
              season average.
            </p>
            <div className="mt-4">
              <SortableTable
                data={weekly}
                columns={weeklyCols}
                initialSort={[{ id: "week", desc: false }]}
                maxHeight={420}
              />
            </div>
          </>
        ) : (
          <p className="text-sm text-muted">
            No {weekSeason} regular-season games found.
          </p>
        )}
      </Section>

      {/* Schedule */}
      <Section
        title={`${TARGET_SEASON} schedule preview`}
        note={
          sched
            ? undefined
            : `No ${TARGET_SEASON} schedule is loaded in the warehouse yet, so matchup difficulty cannot be computed.`
        }
      >
        {sched?.weekly_matchups?.length ? (
          <>
            <BarChart
              bars={sched.weekly_matchups.map((m) => ({
                label: m.week,
                value: num(m.matchup_rating) ?? 0,
                hint: `Week ${m.week} ${m.home_away === "home" ? "vs" : "@"} ${m.opponent}`,
              }))}
              diverging
            />
            <p className="mt-1 text-xs text-faint">
              Green is an easier matchup than league average, red is harder.{" "}
              {sched.easy_weeks} favourable and {sched.hard_weeks} tough weeks
              across {sched.total_weeks} games.
            </p>
            <div className="mt-4 overflow-auto rounded-lg border border-border">
              <table className="tbl">
                <thead>
                  <tr className="cols">
                    <th className="lft">Wk</th>
                    <th className="lft">Opponent</th>
                    <th className="lft">H/A</th>
                    <th>Pts allowed</th>
                    <th className="lft">Rating</th>
                  </tr>
                </thead>
                <tbody>
                  {sched.weekly_matchups.map((m) => (
                    <tr key={m.week}>
                      <td className="lft text-faint">{m.week}</td>
                      <td className="lft">
                        <TeamLogo team={m.opponent} size={18} />
                      </td>
                      <td className="lft text-muted">
                        {m.home_away === "home" ? "Home" : "Away"}
                      </td>
                      <td className="tabular-nums">
                        {(num(m.opp_pts_allowed) ?? 0).toFixed(1)}
                      </td>
                      <td className="lft">
                        <MatchupRating
                          rating={num(m.matchup_rating)}
                          showValue
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </Section>

      {/* Advanced */}
      <Section
        title="Advanced metrics (Pro Football Reference)"
        note={
          pfrLatest
            ? "Percentages are shown as percentages."
            : "No PFR coverage for this player."
        }
      >
        {pfrLatest && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {position === "QB" && (
              <>
                <Metric
                  label="Bad throw %"
                  value={
                    pfrLatest.bad_throw_pct !== null
                      ? `${(pfrLatest.bad_throw_pct * 100).toFixed(1)}%`
                      : "--"
                  }
                />
                <Metric
                  label="Pressured %"
                  value={
                    pfrLatest.pressured_pct !== null
                      ? `${(pfrLatest.pressured_pct * 100).toFixed(1)}%`
                      : "--"
                  }
                />
                <Metric
                  label="Blitzed / game"
                  value={pfrLatest.blitzed_pg?.toFixed(1) ?? "--"}
                />
                <Metric
                  label="Sacked / game"
                  value={pfrLatest.sacked_pg?.toFixed(1) ?? "--"}
                />
              </>
            )}
            {position === "RB" && (
              <>
                <Metric
                  label="Yds before contact"
                  value={pfrLatest.ybc_per_carry?.toFixed(2) ?? "--"}
                />
                <Metric
                  label="Yds after contact"
                  value={pfrLatest.yac_per_carry?.toFixed(2) ?? "--"}
                />
                <Metric
                  label="Broken tackles / g"
                  value={pfrLatest.broken_tackles_pg?.toFixed(2) ?? "--"}
                />
              </>
            )}
            {(position === "WR" || position === "TE") && (
              <>
                <Metric
                  label="Drop rate"
                  value={
                    pfrLatest.drop_pct !== null
                      ? `${(pfrLatest.drop_pct * 100).toFixed(1)}%`
                      : "--"
                  }
                />
                <Metric
                  label="Passer rtg when targeted"
                  value={pfrLatest.target_passer_rating?.toFixed(1) ?? "--"}
                />
                <Metric
                  label="Broken tackles / g"
                  value={pfrLatest.rec_broken_tackles_pg?.toFixed(2) ?? "--"}
                />
              </>
            )}
            <Metric label="PFR season" value={String(pfrLatest.season)} />
          </div>
        )}
      </Section>
    </>
  );
}

export default function PlayerPage() {
  return (
    <Suspense fallback={<TableSkeleton rows={8} cols={8} />}>
      <PlayerInner />
    </Suspense>
  );
}
