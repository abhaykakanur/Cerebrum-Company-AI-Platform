import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

// Button — Form & Input catalog (docs/architecture/specification/
// 87_Component_Library.md). States: Hover/Focus/Disabled built into the
// variant classes below; Loading via the `loading` prop (spinner +
// implicit disabled); "destructive" variant carries the `color-danger`
// token per that document's binding requirement for irreversible
// actions; Dark/Light come for free from the semantic color tokens;
// Accessibility via a real `<button>`/`<a>` element, visible focus
// ring, and `aria-busy`/`aria-disabled` while loading.
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium " +
    "transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 " +
    "focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background " +
    "disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow-xs hover:bg-primary/90",
        secondary:
          "bg-secondary text-secondary-foreground shadow-xs hover:bg-secondary/90",
        destructive:
          "bg-danger text-danger-foreground shadow-xs hover:bg-danger/90",
        outline:
          "border border-border-strong bg-transparent hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        sm: "h-8 rounded-sm px-3 text-xs",
        default: "h-9 px-4",
        lg: "h-11 rounded-md px-6",
        icon: "h-9 w-9 shrink-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      loading = false,
      disabled,
      children,
      ...props
    },
    ref,
  ) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        {...props}
      >
        {asChild ? (
          children
        ) : (
          <>
            {loading && (
              <Loader2
                className="h-icon-sm w-icon-sm animate-spin"
                aria-hidden="true"
              />
            )}
            {children}
          </>
        )}
      </Comp>
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
