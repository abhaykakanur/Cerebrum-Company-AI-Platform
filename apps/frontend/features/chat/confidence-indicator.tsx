import { AlertTriangle, Gauge } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ConfidenceBreakdown } from "@/lib/api/ai";

/**
 * FR-CF-003's low-confidence threshold is org-configurable via
 * 62_AI_Governance.md, but no such governance/config endpoint exists yet
 * in the implemented backend (`AIProviderConfigResponse` has no
 * threshold field) — this is a frontend presentation default only,
 * deciding when to flip the visual warning state, not a computed
 * confidence value itself (the `overall` score is 100% backend-computed
 * and rendered as-is).
 */
const LOW_CONFIDENCE_THRESHOLD = 0.5;

// Confidence indicator — FR-CF-002: always visibly presented, never
// behind a click. FR-CF-003: low-confidence responses are visibly,
// unambiguously labeled using the Warning token.
export function ConfidenceIndicator({
  confidence,
}: {
  confidence: ConfidenceBreakdown;
}) {
  const isLow = confidence.overall < LOW_CONFIDENCE_THRESHOLD;
  const percent = Math.round(confidence.overall * 100);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant={isLow ? "warning" : "info"}
          className="cursor-default gap-1"
        >
          {isLow ? (
            <AlertTriangle className="h-icon-xs w-icon-xs" />
          ) : (
            <Gauge className="h-icon-xs w-icon-xs" />
          )}
          {isLow ? "Low confidence" : "Confidence"}: {percent}%
        </Badge>
      </TooltipTrigger>
      <TooltipContent className="w-56">
        <dl className="flex flex-col gap-1 text-xs">
          <div className="flex justify-between">
            <dt>Retrieval</dt>
            <dd>{Math.round(confidence.retrieval_confidence * 100)}%</dd>
          </div>
          <div className="flex justify-between">
            <dt>Citation coverage</dt>
            <dd>{Math.round(confidence.citation_coverage * 100)}%</dd>
          </div>
          <div className="flex justify-between">
            <dt>Context completeness</dt>
            <dd>{Math.round(confidence.context_completeness * 100)}%</dd>
          </div>
          <div className="flex justify-between">
            <dt>Source diversity</dt>
            <dd>{Math.round(confidence.source_diversity * 100)}%</dd>
          </div>
        </dl>
      </TooltipContent>
    </Tooltip>
  );
}
