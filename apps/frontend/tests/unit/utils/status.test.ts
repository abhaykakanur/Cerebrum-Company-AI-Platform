import { describe, expect, it } from "vitest";

import { formatStatusLabel, statusVariant } from "@/utils/status";

describe("statusVariant", () => {
  it("maps known success-like statuses to the success variant", () => {
    expect(statusVariant("active")).toBe("success");
    expect(statusVariant("healthy")).toBe("success");
    expect(statusVariant("completed")).toBe("success");
  });

  it("maps known failure statuses to the danger variant", () => {
    expect(statusVariant("failed")).toBe("danger");
    expect(statusVariant("unhealthy")).toBe("danger");
    expect(statusVariant("quarantined")).toBe("danger");
  });

  it("is case-insensitive", () => {
    expect(statusVariant("ACTIVE")).toBe("success");
    expect(statusVariant("Failed")).toBe("danger");
  });

  it("falls back to outline for unrecognized statuses instead of guessing", () => {
    expect(statusVariant("some_future_backend_enum_value")).toBe("outline");
  });
});

describe("formatStatusLabel", () => {
  it("converts snake_case to Title Case", () => {
    expect(formatStatusLabel("connector_sync_completed")).toBe(
      "Connector Sync Completed",
    );
  });

  it("handles single words", () => {
    expect(formatStatusLabel("active")).toBe("Active");
  });
});
