/**
 * Matchup rating shown on the same scale the API returns: points allowed above
 * or below the league average for that position. Positive is a good matchup.
 */
export function matchupTier(rating: number): {
  label: string;
  color: string;
  dot: string;
} {
  if (rating > 2) return { label: "Smash", color: "#2ecc71", dot: "🟢" };
  if (rating > 0.5) return { label: "Favorable", color: "#82e0aa", dot: "🟢" };
  if (rating >= -0.5) return { label: "Neutral", color: "#aab7b8", dot: "⚪" };
  if (rating >= -2) return { label: "Tough", color: "#f5b041", dot: "🟡" };
  return { label: "Avoid", color: "#e74c3c", dot: "🔴" };
}

export default function MatchupRating({
  rating,
  showValue = false,
}: {
  rating: number | null | undefined;
  showValue?: boolean;
}) {
  if (rating === null || rating === undefined || Number.isNaN(rating)) {
    return <span className="text-faint">--</span>;
  }
  const t = matchupTier(rating);
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span aria-hidden>{t.dot}</span>
      <span style={{ color: t.color }} className="font-medium">
        {t.label}
      </span>
      {showValue && (
        <span className="tabular-nums text-faint">
          ({rating > 0 ? "+" : ""}
          {rating.toFixed(1)})
        </span>
      )}
    </span>
  );
}
