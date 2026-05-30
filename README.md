# Harness Demo — bounded autonomy + a deterministic verifier

A tiny, **runnable, tested** example of "harness engineering": the model is not
the safety boundary, the code around it is.

An agent proposes a SQL mutation to satisfy a request. Instead of trusting it,
the harness:

1. runs the proposed SQL against a **shadow copy** of the DB (prod is never touched),
2. measures the real **blast radius** (rows changed),
3. **blocks + escalates to a human** if the radius exceeds a budget,
4. is **idempotent** (a re-run with the same key never double-applies),
5. records an **observable trace** of every step.

> A dumb deterministic check in the loop beats a clever model with no check.

## Run it

```bash
python seed.py        # create a throwaway demo.db (212 active + 12 inactive users)
python example.py     # same agent, three requests, one harness
python -m pytest -q   # 6 tests prove the harness is the boundary
```

## What you'll see

```
REQUEST: "archive inactive users"
  APPLIED  | rows=12  | bounded → applied

REQUEST: "archive everyone"
  BLOCKED  | rows=0   | no WHERE clause (unbounded)

REQUEST: "promote everyone to pro"
  BLOCKED  | rows=212 | blast radius 212 exceeds budget 50 (no human approval)

RE-RUN req-0 (idempotency)
  BLOCKED  | rows=0   | idempotent: already applied
```

The `agent.py` stub deliberately drops the `WHERE` clause on one phrasing — the
exact plausible-but-catastrophic output a real LLM produces under load. The
agent is unsafe; the **harness** is what makes the system safe.

## Files

| File | What |
|------|------|
| `harness.py` | the harness: shadow-run → blast-radius budget → human gate → idempotent apply → trace |
| `agent.py`   | a deterministic stand-in for an LLM that proposes SQL (swap in a real model) |
| `seed.py`    | throwaway SQLite DB |
| `example.py` | runnable end-to-end demo |
| `test_harness.py` | 6 tests: safe-applies, no-WHERE-blocked, over-budget-escalates, human-approve-applies, idempotency, non-mutation-refused |

## Swap in a real model

`agent.propose_sql()` is the only stub. Replace it with a real LLM call — the
harness contract is unchanged, and that's the point: **safety lives in the
harness, not the model.**

## License

MIT
