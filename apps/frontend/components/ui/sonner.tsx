"use client";

import { useTheme } from "next-themes";
import { Toaster as Sonner } from "sonner";

type ToasterProps = React.ComponentProps<typeof Sonner>;

// Toast — Feedback & Status catalog. Transient, non-blocking feedback,
// visually/behaviorally distinct from the Notification Center
// (layouts/notification-center.tsx), which is persistent/reviewable
// (87_Component_Library.md).
function Toaster({ ...props }: ToasterProps) {
  const { theme = "dark" } = useTheme();

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-popover group-[.toaster]:text-popover-foreground " +
            "group-[.toaster]:border-border group-[.toaster]:shadow-md",
          description: "group-[.toast]:text-foreground-muted",
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton:
            "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
          error: "group-[.toaster]:text-danger",
          success: "group-[.toaster]:text-success",
          warning: "group-[.toaster]:text-warning",
        },
      }}
      {...props}
    />
  );
}

export { Toaster };
