"use client";

import * as React from "react";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

// Context Drawer — Layout System element for contextual detail panels
// (e.g. a citation's source preview per FR-CT-002). Feature pages call
// `useContextDrawer().open(...)` rather than mounting their own Sheet, so
// only one drawer is ever open app-wide and its slide-in/out state is
// centrally managed.
interface DrawerState {
  title: string;
  content: React.ReactNode;
}

interface ContextDrawerContextValue {
  open: (state: DrawerState) => void;
  close: () => void;
}

const ContextDrawerContext =
  React.createContext<ContextDrawerContextValue | null>(null);

export function ContextDrawerProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [state, setState] = React.useState<DrawerState | null>(null);

  const value = React.useMemo<ContextDrawerContextValue>(
    () => ({
      open: (next) => setState(next),
      close: () => setState(null),
    }),
    [],
  );

  return (
    <ContextDrawerContext.Provider value={value}>
      {children}
      <Sheet
        open={state !== null}
        onOpenChange={(open) => !open && setState(null)}
      >
        <SheetContent side="right">
          <SheetHeader>
            <SheetTitle>{state?.title}</SheetTitle>
          </SheetHeader>
          {state?.content}
        </SheetContent>
      </Sheet>
    </ContextDrawerContext.Provider>
  );
}

export function useContextDrawer(): ContextDrawerContextValue {
  const context = React.useContext(ContextDrawerContext);
  if (!context)
    throw new Error(
      "useContextDrawer must be used within ContextDrawerProvider",
    );
  return context;
}
