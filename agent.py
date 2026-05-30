"""A stand-in 'agent' that proposes SQL for a natural-language request.

In production this would be an LLM call. Here it's a deterministic stub so the
DEMO and TESTS are reproducible — the harness is what we're showing, and the
harness must be safe regardless of how good (or bad) the agent is.

The stub deliberately includes a realistic failure: one phrasing makes it drop
the WHERE clause — exactly the kind of plausible-but-catastrophic output a real
model produces under load.
"""

from __future__ import annotations


def propose_sql(request: str) -> str:
    r = request.lower()
    if "archive everyone" in r or "archive all" in r:
        # Plausible-but-catastrophic: no WHERE → would archive every row.
        return "UPDATE users SET archived = 1"
    if "archive" in r and "inactive" in r:
        # Correct, bounded version.
        return "UPDATE users SET archived = 1 WHERE last_login < '2025-01-01'"
    if "promote" in r and "everyone" in r:
        # Bounded (has WHERE) but over-broad → large blast radius → budget gate.
        return "UPDATE users SET tier = 'pro' WHERE tier = 'free'"
    if "promote" in r:
        return "UPDATE users SET tier = 'pro' WHERE id = 1"
    return "SELECT 1"  # unknown → no-op; harness refuses non-mutations anyway
