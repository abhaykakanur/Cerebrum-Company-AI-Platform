"""CIS Phase 5 Prompt 2's Workflow Validation — Trigger and Steps.
Mirrors cerebrum.infrastructure.connectors.validation's contract
exactly: a function returning a list of human-readable error strings,
empty meaning valid — called both at
:meth:`~cerebrum.application.workflows.workflow_service.WorkflowService.create`
time and at
:meth:`~cerebrum.application.workflows.workflow_service.WorkflowService.update_definition`
time.
"""

from __future__ import annotations

from typing import Any

from cerebrum.infrastructure.database.models.workflow_version import (
    StepType,
    TriggerType,
)

# A workflow step tree is authored by any user holding "workflows:write"
# and interpreted recursively (parallel/condition branches nest further
# steps) — an unbounded depth would let one workflow definition trigger
# unbounded recursion in the execution engine. Five levels comfortably
# covers every realistic automation without risking a DoS via a
# maliciously (or accidentally) deeply nested definition.
_MAX_NESTING_DEPTH = 5

_REQUIRED_STEP_CONFIG_KEYS: dict[StepType, tuple[str, ...]] = {
    StepType.CONNECTOR_ACTION: ("connector_id",),
    StepType.AI_REASONING: ("question",),
    StepType.RETRIEVAL: ("query",),
    StepType.SEARCH: ("query",),
    StepType.NOTIFICATION: ("message",),
    StepType.CUSTOM: ("handler",),
    StepType.CONDITION: ("condition", "then"),
    StepType.DELAY: ("seconds",),
    StepType.PARALLEL: ("steps",),
}


def validate_trigger(trigger_type: str, _trigger_config: dict[str, Any]) -> list[str]:
    try:
        TriggerType(trigger_type)
    except ValueError:
        return [f"'{trigger_type}' is not a supported trigger type."]
    return []


def validate_steps(steps: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    _validate_step_list(steps, depth=1, seen_ids=seen_ids, errors=errors)
    return errors


def _validate_step_list(
    steps: Any, *, depth: int, seen_ids: set[str], errors: list[str]
) -> None:
    if depth > _MAX_NESTING_DEPTH:
        errors.append(
            f"Steps nested deeper than {_MAX_NESTING_DEPTH} levels are not allowed."
        )
        return
    if not isinstance(steps, list):
        errors.append("'steps' must be a list.")
        return
    if not steps and depth == 1:
        errors.append("A workflow must define at least one step.")

    for step in steps:
        if not isinstance(step, dict):
            errors.append("Every step must be an object.")
            continue

        step_id = step.get("id")
        if not step_id or not isinstance(step_id, str):
            errors.append("Every step must have a non-empty string 'id'.")
            continue
        if step_id in seen_ids:
            errors.append(f"Duplicate step id '{step_id}'.")
        seen_ids.add(step_id)

        step_type_raw = step.get("type")
        try:
            step_type = StepType(str(step_type_raw))
        except ValueError:
            errors.append(f"Step '{step_id}' has unknown type '{step_type_raw}'.")
            continue

        config = step.get("config", {})
        if not isinstance(config, dict):
            errors.append(f"Step '{step_id}' config must be an object.")
            continue
        missing = [
            key
            for key in _REQUIRED_STEP_CONFIG_KEYS.get(step_type, ())
            if key not in config
        ]
        if missing:
            errors.append(
                f"Step '{step_id}' ({step_type.value}) is missing config keys: "
                f"{', '.join(missing)}."
            )

        if step_type is StepType.PARALLEL:
            nested = config.get("steps")
            if nested is not None:
                _validate_step_list(
                    nested, depth=depth + 1, seen_ids=seen_ids, errors=errors
                )
        elif step_type is StepType.CONDITION:
            for branch_key in ("then", "else"):
                nested = config.get(branch_key)
                if nested is not None:
                    _validate_step_list(
                        nested, depth=depth + 1, seen_ids=seen_ids, errors=errors
                    )
