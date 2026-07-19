import { cn } from "@/lib/utils";

// Skeleton Loader — Feedback & Status catalog. The Design System's
// standard loading-state placeholder, used wherever content is being
// fetched — supports the "Extremely fast"-feeling goal even when the
// actual fetch takes longer than instantaneous
// (87_Component_Library.md).
function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-shimmer rounded-md bg-gradient-to-r from-muted via-accent to-muted bg-[length:200%_100%]",
        className,
      )}
      {...props}
    />
  );
}

export { Skeleton };
