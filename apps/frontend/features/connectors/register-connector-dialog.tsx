"use client";

import * as React from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import type { ConnectorAuthType, ConnectorType } from "@/lib/api/connectors";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useRegisterConnector } from "@/services/connectors";

const CONNECTOR_TYPES: ConnectorType[] = [
  "github",
  "gitlab",
  "bitbucket",
  "jira",
  "azure_devops",
  "confluence",
  "notion",
  "slack",
  "teams",
];

const AUTH_TYPES: ConnectorAuthType[] = [
  "oauth2",
  "personal_access_token",
  "api_key",
  "service_account",
];

export function RegisterConnectorDialog() {
  const [open, setOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [connectorType, setConnectorType] =
    React.useState<ConnectorType>("github");
  const [authType, setAuthType] = React.useState<ConnectorAuthType>(
    "personal_access_token",
  );
  const [token, setToken] = React.useState("");
  const register = useRegisterConnector();

  const handleSubmit = async () => {
    try {
      await register.mutateAsync({
        connector_type: connectorType,
        name: name.trim(),
        auth_type: authType,
        credentials: { token },
      });
      toast.success(`Connector "${name}" registered.`);
      setOpen(false);
      setName("");
      setToken("");
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Failed to register connector.",
      );
    }
  };

  return (
    <>
      <Button className="gap-1.5" onClick={() => setOpen(true)}>
        <Plus className="h-icon-sm w-icon-sm" />
        Register connector
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Register connector</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label>Connector type</Label>
              <Select
                value={connectorType}
                onValueChange={(v) => setConnectorType(v as ConnectorType)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CONNECTOR_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="connector-name">Name</Label>
              <Input
                id="connector-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label>Auth type</Label>
              <Select
                value={authType}
                onValueChange={(v) => setAuthType(v as ConnectorAuthType)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {AUTH_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type.replace(/_/g, " ")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="connector-token">Access token</Label>
              <Input
                id="connector-token"
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                autoComplete="off"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              onClick={handleSubmit}
              loading={register.isPending}
              disabled={!name.trim() || !token.trim()}
            >
              Register
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
