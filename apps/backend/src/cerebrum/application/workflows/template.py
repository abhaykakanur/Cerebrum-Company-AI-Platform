"""Safe variable resolution for CIS Phase 5 Prompt 2's Workflow
Variables (Workflow Variables, Step Outputs, Runtime Context,
Environment Variables, Secret References) and Conditional Branching.

Deliberately **not** a template/expression engine — no Jinja2, no
``eval()``/``exec()``. A step's config is authored by any user holding
``workflows:write`` and stored in the database; resolving it must never
execute attacker-controlled code (OWASP-relevant). Only whole-string
``"{{ dotted.path }}"`` references are recognized, and path resolution
is restricted to dict-key/list-index lookups into a fixed
:class:`ExecutionContext` — never attribute or method access — which is
the entire safety boundary.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

_TEMPLATE_PATTERN = re.compile(r"^\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}$")


class TemplateResolutionError(Exception):
    """A ``"{{ ... }}"`` reference could not be resolved against the
    current :class:`ExecutionContext` — an unknown root, a missing
    dict key, or an out-of-range list index.
    """


@dataclass(slots=True)
class ExecutionContext:
    """The four reference roots a step's config may address: prior
    ``steps`` output (keyed by step id), accumulated ``variables``,
    the ``trigger`` payload that started this run, and read-only
    ``environment``/``secrets`` maps a caller supplies at execution
    time (``secrets`` deliberately holds only values the caller already
    resolved through the existing configuration framework — this module
    never fetches a secret itself, it only looks one up by name once
    handed one).
    """

    variables: dict[str, Any] = field(default_factory=dict)
    steps: dict[str, Any] = field(default_factory=dict)
    trigger: dict[str, Any] = field(default_factory=dict)
    environment: dict[str, Any] = field(default_factory=dict)
    secrets: dict[str, Any] = field(default_factory=dict)

    def roots(self) -> dict[str, Any]:
        return {
            "variables": self.variables,
            "steps": self.steps,
            "trigger": self.trigger,
            "environment": self.environment,
            "secrets": self.secrets,
        }


def _resolve_path(path: str, roots: dict[str, Any]) -> Any:
    root_name, *rest = path.split(".")
    if root_name not in roots:
        raise TemplateResolutionError(
            f"Unknown reference root '{root_name}' in '{{{{ {path} }}}}'."
        )
    value: Any = roots[root_name]
    for part in rest:
        if isinstance(value, dict):
            if part not in value:
                raise TemplateResolutionError(f"'{path}' has no value at '{part}'.")
            value = value[part]
        elif isinstance(value, list):
            try:
                index = int(part)
                value = value[index]
            except (ValueError, IndexError) as exc:
                raise TemplateResolutionError(
                    f"'{path}' has no valid list index at '{part}'."
                ) from exc
        else:
            raise TemplateResolutionError(
                f"'{path}' cannot descend into a non-container value at '{part}'."
            )
    return value


def resolve_value(value: Any, context: ExecutionContext) -> Any:
    """Recursively resolves ``"{{ dotted.path }}"`` references. A
    whole-string match only — ``"{{ steps.a.output }} extra text"``
    passes through unchanged rather than partially interpolating, so
    this stays a pure lookup rather than growing into a string
    templating language. Dicts and lists are walked; every other value
    passes through unchanged.
    """
    if isinstance(value, str):
        match = _TEMPLATE_PATTERN.match(value)
        if match is None:
            return value
        return _resolve_path(match.group(1), context.roots())
    if isinstance(value, dict):
        return {key: resolve_value(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_value(item, context) for item in value]
    return value


def _safe_resolve(value: Any, context: ExecutionContext) -> Any:
    """An unresolvable reference in a *condition* operand is treated as
    ``None`` rather than aborting the workflow — a merely-unset
    variable should make a condition evaluate false, not fail the run.
    """
    try:
        return resolve_value(value, context)
    except TemplateResolutionError:
        return None


_OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    "eq": lambda a, b: bool(a == b),
    "neq": lambda a, b: bool(a != b),
    "gt": lambda a, b: bool(a > b),
    "gte": lambda a, b: bool(a >= b),
    "lt": lambda a, b: bool(a < b),
    "lte": lambda a, b: bool(a <= b),
    "contains": lambda a, b: bool(b in a),
    "exists": lambda a, _b: a is not None,
    "not_exists": lambda a, _b: a is None,
}


def evaluate_condition(condition: dict[str, Any], context: ExecutionContext) -> bool:
    """CIS Phase 5 Prompt 2's Conditional Branching — a structured,
    non-Turing-complete condition schema (``{"left": <templatable>,
    "operator": <"eq"|"neq"|"gt"|"gte"|"lt"|"lte"|"contains"|"exists"|
    "not_exists">, "right": <templatable, unused for exists/
    not_exists>}``), not an expression language — the same safety
    boundary :func:`resolve_value` establishes. An unknown operator or
    a comparison between incompatible types (e.g. ``"gt"`` on a string)
    evaluates false rather than raising — a malformed condition should
    route a run down its ``else`` branch, not crash it.
    """
    operator = condition.get("operator")
    handler = _OPERATORS.get(operator) if isinstance(operator, str) else None
    if handler is None:
        return False
    left = _safe_resolve(condition.get("left"), context)
    right = _safe_resolve(condition.get("right"), context)
    try:
        return handler(left, right)
    except TypeError:
        return False
