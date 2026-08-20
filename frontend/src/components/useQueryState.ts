"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useCallback } from "react";

/**
 * Read and write a single URL search param, so filtered views stay shareable.
 * Writes replace history rather than pushing, so filter changes do not fill up
 * the back button.
 */
export function useQueryState(key: string, fallback: string) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const value = params.get(key) ?? fallback;

  const setValue = useCallback(
    (next: string) => {
      const sp = new URLSearchParams(params.toString());
      if (next === fallback) sp.delete(key);
      else sp.set(key, next);
      const q = sp.toString();
      router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false });
    },
    [key, fallback, params, pathname, router],
  );

  return [value, setValue] as const;
}
