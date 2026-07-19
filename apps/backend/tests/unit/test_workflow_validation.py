"""Proves CIS Phase 5 Prompt 2's Workflow Validation
(cerebrum.application.workflows.validation): Trigger and Steps, mirroring
cerebrum.infrastructure.connectors.validation's "list of error strings,
empty means valid" contract.
"""

import pytest

from cerebrum.application.workflows.validation import validate_steps, validate_trigger

pytestmark = pytest.mark.unit


def test_validate_trigger_accepts_known_type() -> None:
    assert validate_trigger("manual", {}) == []


def test_validate_trigger_rejects_unknown_type() -> None:
    errors = validate_trigger("not_a_real_trigger", {})
    assert len(errors) == 1


def test_validate_steps_requires_at_least_one_step() -> None:
    errors = validate_steps([])
    assert any("at least one step" in error for error in errors)


def test_validate_steps_accepts_a_minimal_valid_step() -> None:
    steps = [{"id": "notify", "type": "notification", "config": {"message": "hi"}}]
    assert validate_steps(steps) == []


def test_validate_steps_rejects_missing_id() -> None:
    steps = [{"type": "notification", "config": {"message": "hi"}}]
    errors = validate_steps(steps)
    assert any("non-empty string 'id'" in error for error in errors)


def test_validate_steps_rejects_duplicate_ids() -> None:
    steps = [
        {"id": "a", "type": "notification", "config": {"message": "1"}},
        {"id": "a", "type": "notification", "config": {"message": "2"}},
    ]
    errors = validate_steps(steps)
    assert any("Duplicate step id" in error for error in errors)


def test_validate_steps_rejects_unknown_type() -> None:
    steps = [{"id": "a", "type": "teleport", "config": {}}]
    errors = validate_steps(steps)
    assert any("unknown type" in error for error in errors)


def test_validate_steps_rejects_missing_required_config_keys() -> None:
    steps = [{"id": "a", "type": "ai_reasoning", "config": {}}]
    errors = validate_steps(steps)
    assert any(
        "missing config keys" in error and "question" in error for error in errors
    )


def test_validate_steps_validates_parallel_branches() -> None:
    steps = [
        {
            "id": "fan_out",
            "type": "parallel",
            "config": {
                "steps": [
                    {"id": "branch_a", "type": "notification", "config": {}},
                ]
            },
        }
    ]
    errors = validate_steps(steps)
    assert any("branch_a" in error and "message" in error for error in errors)


def test_validate_steps_validates_condition_then_else_branches() -> None:
    steps = [
        {
            "id": "check",
            "type": "condition",
            "config": {
                "condition": {"left": 1, "operator": "eq", "right": 1},
                "then": [{"id": "then_step", "type": "notification", "config": {}}],
                "else": [{"id": "else_step", "type": "notification", "config": {}}],
            },
        }
    ]
    errors = validate_steps(steps)
    assert any("then_step" in error for error in errors)
    assert any("else_step" in error for error in errors)


def test_validate_steps_rejects_duplicate_ids_across_nesting_levels() -> None:
    steps = [
        {"id": "shared", "type": "notification", "config": {"message": "top"}},
        {
            "id": "fan_out",
            "type": "parallel",
            "config": {
                "steps": [
                    {
                        "id": "shared",
                        "type": "notification",
                        "config": {"message": "nested"},
                    }
                ]
            },
        },
    ]
    errors = validate_steps(steps)
    assert any("Duplicate step id 'shared'" in error for error in errors)


def test_validate_steps_rejects_excessive_nesting_depth() -> None:
    innermost = {"id": "leaf", "type": "notification", "config": {"message": "hi"}}
    nested = innermost
    for level in range(10):
        nested = {
            "id": f"level_{level}",
            "type": "parallel",
            "config": {"steps": [nested]},
        }
    errors = validate_steps([nested])
    assert any("nested deeper than" in error for error in errors)
