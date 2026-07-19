"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { useAuth } from "@/providers/auth-provider";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

// Login — the only Auth page this frontend has, since the backend's
// `cerebrum.api.v1.auth` module has no registration route: accounts are
// provisioned out-of-band (see that module's OAuth2 Password Flow-only
// surface). A self-serve sign-up page would be dead UI pointing at a
// capability that doesn't exist server-side.
export default function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (!isLoading && isAuthenticated) router.replace("/dashboard");
  }, [isLoading, isAuthenticated, router]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Login failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Sign in to Cerebrum</CardTitle>
          <CardDescription>
            Enter your credentials to access your organization&apos;s
            workspaces.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <Button type="submit" loading={submitting} className="mt-2">
              Sign in
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
