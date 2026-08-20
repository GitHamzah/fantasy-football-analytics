/**
 * Typed client for the Fantasy Football Analytics FastAPI backend.
 *
 * The API is hosted on the Render free tier, which cold-starts. A first request
 * after idle can take ~30s, so every call gets a long timeout and connection
 * errors are retried.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  "https://fantasy-football-api-34ko.onrender.com";

export type Scoring = "ppr" | "half_ppr" | "standard";

const TIMEOUT_MS = 60_000;
const RETRIES = 3;

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function qs(params: Record<string, unknown>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

/**
 * The API declares hard caps on `limit` (FastAPI Query(le=...)). Exceeding them
 * returns 422, so clamp here rather than letting a caller silently break a page.
 */
const LIMIT_CAPS = {
  consistency: 100,
  vor: 200,
  opportunity: 200,
} as const;

function clamp(value: number, max: number): number {
  return Math.max(1, Math.min(value, max));
}

async function request<T>(
  path: string,
  init?: RequestInit,
  attempt = 0,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });

    if (!res.ok) {
      // 4xx and 5xx are real answers, not transport failures - do not retry.
      throw new ApiError(
        `${res.status} ${res.statusText} for ${path}`,
        res.status,
      );
    }
    return (await res.json()) as T;
  } catch (err) {
    const isAbort = err instanceof Error && err.name === "AbortError";
    const isNetwork = err instanceof TypeError; // fetch throws TypeError on network failure
    if ((isAbort || isNetwork) && attempt < RETRIES - 1) {
      // Back off a little; a cold Render instance needs a moment.
      await new Promise((r) => setTimeout(r, 1500 * (attempt + 1)));
      return request<T>(path, init, attempt + 1);
    }
    if (err instanceof ApiError) throw err;
    throw new ApiError(
      isAbort
        ? `Request to ${path} timed out after ${TIMEOUT_MS / 1000}s`
        : `Could not reach the API (${path})`,
    );
  } finally {
    clearTimeout(timer);
  }
}

/** Resolves to null instead of throwing, for endpoints that may be down. */
export async function tryGet<T>(p: Promise<T>): Promise<T | null> {
  try {
    return await p;
  } catch {
    return null;
  }
}

/* ------------------------------------------------------------------ */
/* Response types                                                      */
/* ------------------------------------------------------------------ */

export interface Projection {
  player_id: string;
  player_name: string;
  position: string;
  team: string | null;
  age: number | null;
  projected_ppg: number;
  projected_games: number;
  projected_total: number;
  age_multiplier: number | null;
  base_ppg: number | null;
  opportunities_pg: number | null;
  last_season_ppg: number | null;
  last_season_games: number | null;
  seasons_of_data: number | null;
  method: string;
  overall_rank: number;
  pos_rank: number;
}

export interface LeaderEntry {
  player_id: string;
  player_name: string;
  position: string;
  team: string | null;
  games_played: number;
  total_points: number;
  ppg: number;
}

export interface VorEntry {
  player_id: string;
  player_name: string;
  position: string;
  team: string | null;
  games_played: number;
  pos_rank: number;
  ppg: number;
  baseline_ppg: number;
  vor_ppg: number;
  vor_total: number;
}

export interface ConsistencyEntry {
  player_id: string;
  player_name: string;
  position: string;
  team: string | null;
  games_played: number;
  total_points: number;
  ppg: number;
  std_dev: number | null;
  floor: number;
  ceiling: number;
  boom_weeks: number;
  bust_weeks: number;
  boom_pct: number | null;
  bust_pct: number | null;
  consistency_score: number | null;
}

export interface OpportunityEntry {
  player_id: string;
  player_name: string;
  position: string;
  team: string | null;
  games_played: number;
  opportunities_pg: number;
  targets_pg: number;
  carries_pg: number;
  fantasy_ppg: number;
  target_share_pct: number | null;
  air_yards_share_pct: number | null;
  wopr: number | null;
}

export interface DefenseRow {
  defense: string;
  position: string;
  games: number;
  avg_pts_allowed: number;
  total_pts_allowed: number;
}

export interface TeamDefenseRow {
  team: string;
  season: number;
  games: number;
  sacks_pg: number;
  qb_hits_pg: number;
  interceptions_pg: number;
  pass_defended_pg: number;
  fumbles_forced_pg: number;
  tfl_pg: number;
  pressure_pg: number;
  coverage_pg: number;
  playmaker_pg: number;
  dst_score: number;
}

export interface PlayerSummary {
  player_id: string;
  player_name: string | null;
  position: string | null;
  position_group: string | null;
  current_team: string | null;
}

export interface PlayerDetailRow extends PlayerSummary {
  height_inches?: number | null;
  weight_lbs?: number | null;
  birth_date?: string | null;
  age?: number | null;
  college?: string | null;
  rookie_year?: number | null;
  draft_year?: number | null;
  draft_round?: number | null;
  draft_pick?: number | null;
  status?: string | null;
}

export interface SeasonStats {
  season: number;
  games_played: number;
  total_points: number;
  ppg: number;
  [k: string]: number | string | null;
}

export interface WeekStats {
  season: number;
  week: number;
  opponent_team?: string | null;
  fantasy_points: number;
  [k: string]: number | string | null | undefined;
}

export interface TrajectoryEntry {
  player_id: string;
  player_name: string;
  position: string;
  team: string | null;
  season: number;
  games_played: number;
  total_points: number;
  ppg: number;
  opportunities_pg: number;
  targets_pg: number;
  carries_pg: number;
}

export interface WeeklyMatchup {
  week: number;
  opponent: string;
  home_away: string;
  opp_pts_allowed: number;
  matchup_rating: number;
}

export interface ScheduleStrength {
  team: string;
  position: string;
  schedule_strength: number;
  total_weeks: number;
  easy_weeks: number;
  hard_weeks: number;
  weekly_matchups: WeeklyMatchup[];
}

export interface CompareEntry {
  player_id: string;
  player_name: string;
  position: string;
  team: string | null;
  games_played: number;
  ppg: number;
  std_dev: number | null;
  floor: number;
  ceiling: number;
  boom_weeks: number;
  bust_weeks: number;
  consistency_score: number | null;
  recent_ppg: number | null;
}

export interface PfrPlayerRow {
  season: number;
  player_name: string;
  position: string;
  team: string;
  games: number;
  bad_throw_pct: number | null;
  pressured_pct: number | null;
  blitzed_pg: number | null;
  hurried_pg: number | null;
  hit_pg: number | null;
  sacked_pg: number | null;
  ybc_per_carry: number | null;
  yac_per_carry: number | null;
  broken_tackles_pg: number | null;
  drop_pct: number | null;
  target_passer_rating: number | null;
  rec_broken_tackles_pg: number | null;
}

export interface DefenseUnitRow {
  defense: string;
  unit: string;
  games: number;
  completion_pct_allowed: number | null;
  yards_per_target_allowed: number | null;
  passer_rating_allowed: number | null;
  targets_pg: number | null;
  ints_pg: number | null;
  sacks_pg: number | null;
  pressures_pg: number | null;
  qb_hits_pg: number | null;
  tackles_pg: number | null;
  missed_tackle_pct: number | null;
}

export interface AiResponse {
  question: string;
  answer: string;
  data_context: string;
}

/* ------------------------------------------------------------------ */
/* Endpoints                                                           */
/* ------------------------------------------------------------------ */

export const getProjections = (
  season: number,
  position?: string,
  scoring: Scoring = "ppr",
  limit = 300,
) =>
  request<Projection[]>(
    `/projections/players${qs({ season, position, scoring, limit })}`,
  );

export const getSeasonLeaders = (
  season: number,
  position?: string,
  scoring: Scoring = "ppr",
  limit = 100,
) =>
  request<LeaderEntry[]>(
    `/leaders/season${qs({ season, position, scoring, limit })}`,
  );

export const getWeeklyLeaders = (
  season: number,
  week: number,
  position?: string,
  scoring: Scoring = "ppr",
  limit = 100,
) =>
  request<LeaderEntry[]>(
    `/leaders/weekly${qs({ season, week, position, scoring, limit })}`,
  );

export const getVOR = (season: number, scoring: Scoring = "ppr", limit = 200) =>
  request<VorEntry[]>(
    `/analytics/vor${qs({ season, scoring, limit: clamp(limit, LIMIT_CAPS.vor) })}`,
  );

export const getConsistency = (
  season: number,
  position?: string,
  scoring: Scoring = "ppr",
  limit = 100,
) =>
  request<ConsistencyEntry[]>(
    `/analytics/consistency${qs({
      season,
      position,
      scoring,
      limit: clamp(limit, LIMIT_CAPS.consistency),
    })}`,
  );

export const getOpportunity = (
  season: number,
  position?: string,
  scoring: Scoring = "ppr",
  limit = 200,
) =>
  request<OpportunityEntry[]>(
    `/analytics/opportunity${qs({
      season,
      position,
      scoring,
      limit: clamp(limit, LIMIT_CAPS.opportunity),
    })}`,
  );

export const getDefensiveRankings = (
  season: number,
  scoring: Scoring = "ppr",
) => request<DefenseRow[]>(`/analytics/defense${qs({ season, scoring })}`);

export const getTeamDefense = (season = 2025) =>
  request<TeamDefenseRow[]>(`/advanced/team-defense${qs({ season })}`);

export const getDefenseVsPosition = (season: number, unit?: string) =>
  request<DefenseUnitRow[]>(
    `/advanced/pfr/defense-vs-position${qs({ season, unit })}`,
  );

export const getPlayerDetail = (playerId: string) =>
  request<PlayerDetailRow>(`/players/${encodeURIComponent(playerId)}`);

export const getSeasonStats = (
  playerId: string,
  season?: number,
  scoring: Scoring = "ppr",
) =>
  request<SeasonStats[]>(
    `/stats/season/${encodeURIComponent(playerId)}${qs({ season, scoring })}`,
  );

export const getWeeklyStats = (
  playerId: string,
  season: number,
  scoring: Scoring = "ppr",
) =>
  request<WeekStats[]>(
    `/stats/weekly/${encodeURIComponent(playerId)}${qs({ season, scoring })}`,
  );

export const getTrajectory = (playerId: string, scoring: Scoring = "ppr") =>
  request<TrajectoryEntry[]>(
    `/analytics/trajectory/${encodeURIComponent(playerId)}${qs({ scoring })}`,
  );

export const getPfrPlayerStats = (playerId: string, season?: number) =>
  request<PfrPlayerRow[]>(
    `/advanced/pfr/player/${encodeURIComponent(playerId)}${qs({ season })}`,
  );

export const getScheduleStrength = (
  season: number,
  position?: string,
  scoring: Scoring = "ppr",
) =>
  request<ScheduleStrength[]>(
    `/projections/schedule${qs({ season, position, scoring })}`,
  );

export const getTeamSchedule = (
  team: string,
  season: number,
  position = "RB",
  scoring: Scoring = "ppr",
) =>
  request<ScheduleStrength>(
    `/projections/schedule/${encodeURIComponent(team)}${qs({
      season,
      position,
      scoring,
    })}`,
  );

export const getCompare = (
  playerIds: string[],
  season: number,
  scoring: Scoring = "ppr",
) =>
  request<CompareEntry[]>(
    `/analytics/compare${qs({
      player_ids: playerIds.join(","),
      season,
      scoring,
    })}`,
  );

export const searchPlayers = (query: string, position?: string, limit = 20) =>
  request<PlayerSummary[]>(`/players/search${qs({ q: query, position, limit })}`);

export const getFantasyPlayers = (minSeason = 2024) =>
  request<PlayerSummary[]>(
    `/players/fantasy-relevant${qs({ min_season: minSeason })}`,
  );

export const askAI = (question: string) =>
  request<AiResponse>(`/ai/ask`, {
    method: "POST",
    body: JSON.stringify({ question }),
  });
