import * as React from "react";

import { cn } from "@/lib/utils";

// Responsive Grid — Layout System element (docs/architecture/specification/
// 85_Frontend_Architecture.md) spanning the five required device classes
// (Mobile: 1 col, Tablet: 2, Laptop/Desktop: `cols`, Ultrawide: capped by
// `maxColsUltrawide` so cards don't stretch unreadably wide).
export interface ResponsiveGridProps extends React.HTMLAttributes<HTMLDivElement> {
  cols?: 2 | 3 | 4;
  maxColsUltrawide?: 4 | 5 | 6;
}

const LAPTOP_COLS: Record<number, string> = {
  2: "lg:grid-cols-2",
  3: "lg:grid-cols-3",
  4: "lg:grid-cols-4",
};

const ULTRAWIDE_COLS: Record<number, string> = {
  4: "2xl:grid-cols-4",
  5: "2xl:grid-cols-5",
  6: "2xl:grid-cols-6",
};

const ResponsiveGrid = React.forwardRef<HTMLDivElement, ResponsiveGridProps>(
  ({ cols = 3, maxColsUltrawide = 4, className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "grid grid-cols-1 gap-4 sm:grid-cols-2",
        LAPTOP_COLS[cols],
        ULTRAWIDE_COLS[maxColsUltrawide],
        className,
      )}
      {...props}
    />
  ),
);
ResponsiveGrid.displayName = "ResponsiveGrid";

export { ResponsiveGrid };
