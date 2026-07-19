import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merges conditional class names, then resolves conflicting Tailwind
 * utility classes (e.g. `p-2 p-4` -> `p-4`) — the standard helper every
 * Design System component below composes classes through, so no
 * component ever string-concatenates class names ad hoc. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
