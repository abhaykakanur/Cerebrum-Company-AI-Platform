/** Organization API — mirrors apps/backend/src/cerebrum/api/v1/organizations.py. */

import { apiGet, apiSend } from "@/lib/api/client";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

export async function getMyOrganization(): Promise<Organization> {
  return apiGet<Organization>("/organizations/me", { skipWorkspace: true });
}

export async function renameMyOrganization(
  name: string,
): Promise<Organization> {
  return apiSend<Organization>(
    "/organizations/me",
    "PATCH",
    { name },
    { skipWorkspace: true },
  );
}
