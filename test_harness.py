"""Tests that prove the harness is the safety boundary — not the agent."""

import os
import sqlite3

import pytest

from agent import propose_sql
from harness import Harness
from seed import seed

DB = "test_demo.db"


@pytest.fixture()
def db():
    seed(DB)
    yield DB
    if os.path.exists(DB):
        os.remove(DB)


def _archived_count(path):
    conn = sqlite3.connect(path)
    n = conn.execute("SELECT COUNT(*) FROM users WHERE archived = 1").fetchone()[0]
    conn.close()
    return n


def test_safe_bounded_mutation_applies(db):
    h = Harness(db, max_blast_radius=50)
    d = h.run(propose_sql("archive inactive users"), "k1")
    assert d.applied and not d.blocked
    assert d.rows_affected == 12          # only the inactive rows
    assert _archived_count(db) == 12


def test_missing_where_is_blocked(db):
    h = Harness(db, max_blast_radius=50)
    d = h.run(propose_sql("archive everyone"), "k2")
    assert d.blocked and not d.applied
    assert _archived_count(db) == 0       # prod untouched


def test_over_budget_escalates_and_blocks_without_approval(db):
    h = Harness(db, max_blast_radius=50)
    # "promote everyone" touches all 212 rows > budget 50, human gate declines
    d = h.run(propose_sql("promote everyone to pro"), "k3", human_gate=lambda s, r: False)
    assert d.blocked and d.rows_affected > 50


def test_over_budget_applies_with_human_approval(db):
    h = Harness(db, max_blast_radius=50)
    d = h.run(propose_sql("promote everyone to pro"), "k4", human_gate=lambda s, r: True)
    assert d.applied and d.rows_affected > 50


def test_idempotency_blocks_double_apply(db):
    h = Harness(db, max_blast_radius=50)
    first = h.run(propose_sql("archive inactive users"), "same-key")
    second = h.run(propose_sql("archive inactive users"), "same-key")
    assert first.applied
    assert not second.applied
    assert _archived_count(db) == 12      # not doubled


def test_non_mutation_refused(db):
    h = Harness(db, max_blast_radius=50)
    d = h.run("SELECT * FROM users", "k5")
    assert d.blocked and not d.applied
