"""Runnable demo: the same agent, three requests, one harness.

    python seed.py && python example.py

Shows the harness applying a safe bounded mutation, blocking an unbounded one
(no WHERE), and escalating an over-budget one to a human gate.
"""

from __future__ import annotations

from agent import propose_sql
from harness import Harness
from seed import seed


def deny(_sql: str, _radius: int) -> bool:
    return False  # demo human-gate that always declines


def line(label: str, d) -> None:
    status = "APPLIED " if d.applied else "BLOCKED "
    print(f"\n{label}\n  {status} | rows={d.rows_affected} | {d.reason}")
    for step in d.trace:
        print(f"    · {step}")


def main() -> None:
    seed("demo.db")
    h = Harness("demo.db", max_blast_radius=50)

    reqs = [
        "archive inactive users",     # bounded → applied
        "archive everyone",           # no WHERE → blocked outright
        "promote everyone to pro",    # huge blast radius → human gate (declined)
    ]
    for i, req in enumerate(reqs):
        sql = propose_sql(req)
        d = h.run(sql, idempotency_key=f"req-{i}", human_gate=deny)
        line(f'REQUEST: "{req}"', d)

    # idempotency: re-running the first request does nothing
    again = h.run(propose_sql(reqs[0]), idempotency_key="req-0", human_gate=deny)
    line('RE-RUN req-0 (idempotency)', again)


if __name__ == "__main__":
    main()
