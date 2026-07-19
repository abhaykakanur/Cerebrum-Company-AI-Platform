"""Proves CIS Phase 5 Prompt 2's safe variable resolution
(cerebrum.application.workflows.template): whole-string
``"{{ dotted.path }}"`` lookups into a fixed :class:`ExecutionContext`
(Workflow Variables, Step Outputs, Runtime Context), and the
structured, non-Turing-complete Conditional Branching schema —
deliberately never an expression language (no eval()/exec()), so these
tests also double as the security boundary's specification.
"""

import pytest

from cerebrum.application.workflows.template import (
    ExecutionContext,
    TemplateResolutionError,
    evaluate_condition,
    resolve_value,
)

pytestmark = pytest.mark.unit


def _context() -> ExecutionContext:
    return ExecutionContext(
        variables={"threshold": 5, "name": "Acme"},
        steps={"fetch": {"count": 10, "items": ["a", "b", "c"]}},
        trigger={"source": "manual"},
        environment={"region": "us-east-1"},
    )


def test_resolve_value_passes_through_non_template_strings() -> None:
    assert resolve_value("plain text", _context()) == "plain text"


def test_resolve_value_resolves_variable_reference() -> None:
    assert resolve_value("{{ variables.threshold }}", _context()) == 5


def test_resolve_value_resolves_nested_step_output() -> None:
    assert resolve_value("{{ steps.fetch.count }}", _context()) == 10


def test_resolve_value_resolves_list_index() -> None:
    assert resolve_value("{{ steps.fetch.items.1 }}", _context()) == "b"


def test_resolve_value_resolves_trigger_and_environment() -> None:
    assert resolve_value("{{ trigger.source }}", _context()) == "manual"
    assert resolve_value("{{ environment.region }}", _context()) == "us-east-1"


def test_resolve_value_does_not_interpolate_partial_matches() -> None:
    assert (
        resolve_value("count is {{ steps.fetch.count }}", _context())
        == "count is {{ steps.fetch.count }}"
    )


def test_resolve_value_walks_dicts_and_lists() -> None:
    config = {
        "message": "{{ variables.name }}",
        "items": ["{{ steps.fetch.count }}", "literal"],
    }
    resolved = resolve_value(config, _context())
    assert resolved == {"message": "Acme", "items": [10, "literal"]}


def test_resolve_value_raises_for_unknown_root() -> None:
    with pytest.raises(TemplateResolutionError):
        resolve_value("{{ secrets_typo.token }}", _context())


def test_resolve_value_raises_for_missing_key() -> None:
    with pytest.raises(TemplateResolutionError):
        resolve_value("{{ variables.does_not_exist }}", _context())


def test_resolve_value_raises_for_out_of_range_index() -> None:
    with pytest.raises(TemplateResolutionError):
        resolve_value("{{ steps.fetch.items.99 }}", _context())


def test_resolve_value_never_executes_arbitrary_code() -> None:
    """The security boundary this module exists for: a string that
    looks like Python is just a literal string, never evaluated.
    """
    dangerous = "__import__('os').system('echo pwned')"
    assert resolve_value(dangerous, _context()) == dangerous
    assert (
        resolve_value(f"{{{{ {dangerous} }}}}", _context()) == f"{{{{ {dangerous} }}}}"
    )


@pytest.mark.parametrize(
    ("operator", "left", "right", "expected"),
    [
        ("eq", "{{ variables.name }}", "Acme", True),
        ("neq", "{{ variables.name }}", "Other", True),
        ("gt", "{{ steps.fetch.count }}", 5, True),
        ("gte", "{{ steps.fetch.count }}", 10, True),
        ("lt", "{{ variables.threshold }}", 10, True),
        ("lte", "{{ variables.threshold }}", 5, True),
        ("contains", "{{ steps.fetch.items }}", "b", True),
        ("exists", "{{ variables.threshold }}", None, True),
        ("not_exists", "{{ variables.missing }}", None, True),
    ],
)
def test_evaluate_condition_operators(operator, left, right, expected) -> None:  # type: ignore[no-untyped-def]
    condition = {"left": left, "operator": operator}
    if right is not None:
        condition["right"] = right
    assert evaluate_condition(condition, _context()) is expected


def test_evaluate_condition_unknown_operator_is_false() -> None:
    condition = {"left": 1, "operator": "frobnicate", "right": 1}
    assert evaluate_condition(condition, _context()) is False


def test_evaluate_condition_missing_reference_is_false_not_raising() -> None:
    condition = {
        "left": "{{ variables.does_not_exist }}",
        "operator": "eq",
        "right": "anything",
    }
    assert evaluate_condition(condition, _context()) is False


def test_evaluate_condition_incompatible_types_is_false_not_raising() -> None:
    condition = {"left": "{{ variables.name }}", "operator": "gt", "right": 5}
    assert evaluate_condition(condition, _context()) is False
