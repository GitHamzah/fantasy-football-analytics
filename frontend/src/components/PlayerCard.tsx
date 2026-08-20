import Link from "next/link";
import PositionBadge from "./PositionBadge";
import TeamLogo from "./TeamLogo";

/** Compact player identity: badge, linked name, team. Used inside table cells. */
export default function PlayerCard({
  playerId,
  name,
  position,
  team,
  stat,
  statLabel,
  scoring,
}: {
  playerId: string;
  name: string;
  position?: string | null;
  team?: string | null;
  stat?: string | number;
  statLabel?: string;
  scoring?: string;
}) {
  const href = scoring
    ? `/players/${encodeURIComponent(playerId)}?scoring=${scoring}`
    : `/players/${encodeURIComponent(playerId)}`;

  return (
    <span className="flex items-center justify-between gap-3">
      <span className="flex min-w-0 items-center gap-2">
        <PositionBadge position={position} />
        <Link
          href={href}
          className="truncate font-medium text-text underline-offset-2 hover:text-accent hover:underline"
        >
          {name}
        </Link>
        <TeamLogo team={team} size={18} />
      </span>
      {stat !== undefined && (
        <span className="whitespace-nowrap text-right">
          <span className="font-semibold text-accent tabular-nums">{stat}</span>
          {statLabel && (
            <span className="ml-1 text-[10px] uppercase text-faint">
              {statLabel}
            </span>
          )}
        </span>
      )}
    </span>
  );
}
