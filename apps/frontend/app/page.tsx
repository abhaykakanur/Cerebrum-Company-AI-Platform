"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/providers/auth-provider";
import { Button } from "@/components/ui/button";

export default function LandingPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (!isLoading && isAuthenticated) router.replace("/dashboard");
  }, [isLoading, isAuthenticated, router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 text-center">
      <h1 className="text-display font-semibold tracking-tight">Cerebrum</h1>
      <p className="max-w-md text-body text-foreground-muted">
        The enterprise AI platform that turns your organization&apos;s scattered
        knowledge into a living, evidence-backed intelligence layer.
      </p>
      <Button asChild size="lg">
        <Link href="/login">Sign in</Link>
      </Button>
    </div>
  );
}
