import * as React from "react";

import { cn } from "@/lib/utils";

// Input — Form & Input catalog. States: Hover/Focus/Disabled via the
// classes below; Error/Success via the `invalid`/`valid` props (paired
// with the danger/success color tokens, never a hardcoded color);
// Accessibility via native `<input>` semantics plus
// `aria-invalid`/`aria-describedby` wiring left to the consuming form
// field (this component only renders the visual state).
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
  valid?: boolean;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, invalid, valid, ...props }, ref) => {
    return (
      <input
        type={type}
        ref={ref}
        aria-invalid={invalid || undefined}
        className={cn(
          "flex h-9 w-full rounded-md border border-input bg-background-elevated px-3 py-1 text-sm",
          "shadow-xs transition-colors duration-fast placeholder:text-foreground-muted",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          "focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
          "file:border-0 file:bg-transparent file:text-sm file:font-medium",
          invalid && "border-danger focus-visible:ring-danger",
          valid && "border-success focus-visible:ring-success",
          className,
        )}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

export { Input };
