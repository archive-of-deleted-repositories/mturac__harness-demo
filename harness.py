"""A real harness: bounded autonomy + deterministic verification for an LLM agent.

The point of "harness engineering": the model is not the safety boundary — the
code around it is. Here an agent proposes a SQL mutation to satisfy a request.
Instead of trusting it, the harness:

  1. runs the proposed SQL against a SHADOW copy of the DB (never prod),
  2. measures the real blast radius (rows changed),
  3. BLOCKS and escalates to a human if the radius exceeds a budget,
  4. is idempotent (a re-run with the same idempotency key never double-applies),
  5. records an observable trace of every step.

A dumb deterministic check in the loop beats a clever model with no check.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Decision:
    applied: bool
    blocked: bool
    rows_affected: int
    reason: str
    trace: list[str] = field(default_factory=list)


class Harness:
    """Wraps an agent's DB mutation with verify → budget → idempotency → apply."""

    def __init__(self, db_path: str, max_blast_radius: int = 50):
        self.db_path = db_path
        self.max_blast_radius = max_blast_radius
        self._applied_keys: set[str] = set()

    # --- guards -----------------------------------------------------------
    @staticmethod
    def _is_mutation(sql: str) -> bool:
        return bool(re.match(r"\s*(update|delete|insert)\b", sql, re.I))

    @staticmethod
    def _has_where(sql: str) -> bool:
        # UPDATE/DELETE without a WHERE is an unbounded blast radius.
        if re.match(r"\s*(update|delete)\b", sql, re.I):
            return bool(re.search(r"\bwhere\b", sql, re.I))
        return True

    def _shadow_blast_radius(self, sql: str) -> int:
        """Run the mutation on an in-memory copy of the DB; count changed rows."""
        src = sqlite3.connect(self.db_path)
        shadow = sqlite3.connect(":memory:")
        src.backup(shadow)  # full copy — prod is never touched
        src.close()
        cur = shadow.cursor()
        cur.execute(sql)
        n = cur.rowcount
        shadow.rollback()
        shadow.close()
        return max(n, 0)

    # --- main entrypoint --------------------------------------------------
    def run(self, sql: str, idempotency_key: str,
            human_gate: Optional[Callable[[str, int], bool]] = None) -> Decision:
        trace: list[str] = []

        if idempotency_key in self._applied_keys:
            return Decision(False, False, 0, "idempotent: already applied", ["dedup hit"])

        trace.append(f"proposed: {sql.strip()[:80]}")

        if not self._is_mutation(sql):
            return Decision(False, True, 0, "not a mutation — refused", trace)

        if not self._has_where(sql):
            trace.append("guard: mutation without WHERE → unbounded blast radius")
            return Decision(False, True, 0, "blocked: no WHERE clause (unbounded)", trace)

        radius = self._shadow_blast_radius(sql)
        trace.append(f"shadow run: {radius} rows would change")

        if radius > self.max_blast_radius:
            trace.append(f"budget: {radius} > {self.max_blast_radius} → escalate")
            approved = human_gate(sql, radius) if human_gate else False
            if not approved:
                return Decision(False, True, radius,
                                f"blocked: blast radius {radius} exceeds budget "
                                f"{self.max_blast_radius} (no human approval)", trace)
            trace.append("human gate: APPROVED")

        # safe (or human-approved) → apply for real, idempotently
        conn = sqlite3.connect(self.db_path)
        conn.execute(sql)
        conn.commit()
        conn.close()
        self._applied_keys.add(idempotency_key)
        trace.append("applied to prod")
        return Decision(True, False, radius, "applied", trace)
