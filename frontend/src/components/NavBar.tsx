"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useQueryState } from "./useQueryState";

const LINKS = [
  { href: "/", label: "Rankings" },
  { href: "/matchups", label: "Matchups" },
  { href: "/waiver-wire", label: "Waiver Wire" },
  { href: "/ai", label: "AI Analyst" },
];

const SCORINGS: { value: string; label: string }[] = [
  { value: "ppr", label: "PPR" },
  { value: "half_ppr", label: "Half" },
  { value: "standard", label: "Std" },
];

function ScoringToggle() {
  const [scoring, setScoring] = useQueryState("scoring", "ppr");
  return (
    <div className="flex items-center rounded-md border border-border bg-surface p-0.5">
      {SCORINGS.map((s) => {
        const active = scoring === s.value;
        return (
          <button
            key={s.value}
            onClick={() => setScoring(s.value)}
            className={
              "rounded px-2.5 py-1 text-xs font-medium transition-colors " +
              (active
                ? "bg-accent text-white"
                : "text-muted hover:text-text")
            }
            aria-pressed={active}
          >
            {s.label}
          </button>
        );
      })}
    </div>
  );
}

function NavLinks() {
  const pathname = usePathname();
  const params = useSearchParams();
  // Carry the scoring choice across pages so the toggle is not reset by navigation.
  const scoring = params.get("scoring");
  const suffix = scoring ? `?scoring=${scoring}` : "";

  return (
    <nav className="flex items-center gap-1">
      {LINKS.map((l) => {
        const active =
          l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
        return (
          <Link
            key={l.href}
            href={`${l.href}${suffix}`}
            className={
              "rounded-md px-3 py-1.5 text-sm transition-colors " +
              (active
                ? "bg-surface text-text"
                : "text-muted hover:bg-surface hover:text-text")
            }
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}

export default function NavBar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={
        "sticky top-0 z-50 border-b transition-colors " +
        (scrolled
          ? "border-border bg-bg/80 backdrop-blur-md"
          : "border-transparent bg-bg")
      }
    >
      <div className="mx-auto flex h-14 max-w-[1600px] items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 whitespace-nowrap">
          <span className="text-base font-bold tracking-tight text-text">
            Fantasy Football
          </span>
          <span className="hidden text-base font-light text-muted sm:inline">
            Analytics
          </span>
        </Link>

        <div className="flex items-center gap-3">
          <Suspense fallback={null}>
            <NavLinks />
          </Suspense>
          <Suspense fallback={null}>
            <ScoringToggle />
          </Suspense>
        </div>
      </div>
    </header>
  );
}
