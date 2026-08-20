"use client";

import { useState } from "react";

/**
 * Team logo from the ESPN CDN, with the abbreviation beside it.
 *
 * A handful of nflverse abbreviations differ from the ones ESPN uses in its
 * logo paths, so those are remapped. Unknown or missing teams fall back to a
 * neutral dot rather than a broken image.
 */
const ESPN_ALIAS: Record<string, string> = {
  LA: "lar",
  LAR: "lar",
  STL: "lar",
  SD: "lac",
  LAC: "lac",
  OAK: "lv",
  LV: "lv",
  WAS: "wsh",
  WSH: "wsh",
  JAC: "jax",
  JAX: "jax",
  ARZ: "ari",
  BLT: "bal",
  CLV: "cle",
  HST: "hou",
};

export function espnLogoUrl(team?: string | null): string | null {
  if (!team) return null;
  const key = team.toUpperCase();
  const slug = ESPN_ALIAS[key] ?? key.toLowerCase();
  return `https://a.espncdn.com/i/teamlogos/nfl/500/${slug}.png`;
}

export default function TeamLogo({
  team,
  size = 20,
  showAbbr = true,
}: {
  team?: string | null;
  size?: number;
  showAbbr?: boolean;
}) {
  const [broken, setBroken] = useState(false);
  const url = espnLogoUrl(team);

  if (!team) {
    return <span className="text-faint">--</span>;
  }

  return (
    <span className="inline-flex items-center gap-1.5 align-middle">
      {url && !broken ? (
        // Plain img: the ESPN CDN is external and these are tiny, so the
        // next/image optimizer would add cost without benefit.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={url}
          alt={team}
          width={size}
          height={size}
          loading="lazy"
          onError={() => setBroken(true)}
          style={{ width: size, height: size, objectFit: "contain" }}
        />
      ) : (
        <span
          className="inline-block rounded-full bg-border"
          style={{ width: size * 0.6, height: size * 0.6 }}
        />
      )}
      {showAbbr && <span className="text-muted">{team.toUpperCase()}</span>}
    </span>
  );
}
