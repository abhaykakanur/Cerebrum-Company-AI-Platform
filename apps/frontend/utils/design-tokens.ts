/** Reads a Design System HSL custom property (e.g. `--primary`) at
 * runtime and returns it as a usable `hsl(...)` string — for the rare
 * cases (Cytoscape, Recharts) where a library needs a literal color
 * value rather than a Tailwind class, so it still respects the active
 * theme (light/dark) instead of hardcoding a color. */
export function cssVarAsHsl(name: string, fallback = "0 0% 50%"): string {
  if (typeof window === "undefined") return `hsl(${fallback})`;
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return `hsl(${value || fallback})`;
}
