import * as React from "react";

import { cn } from "@/lib/utils";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, invalid, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        aria-invalid={invalid || undefined}
        className={cn(
          "flex min-h-20 w-full rounded-md border border-input bg-background-elevated px-3 py-2 text-sm",
          "shadow-xs transition-colors duration-fast placeholder:text-foreground-muted",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          "focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
          invalid && "border-danger focus-visible:ring-danger",
          className,
        )}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";

export { Textarea };
