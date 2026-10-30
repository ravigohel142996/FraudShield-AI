"""Track B unit tests: the authorization engine and the retrieval simulator.

These tests are independent of any model and of any API key. They are the evidence that
the retrieval-layer verdicts in results/ were produced by a rule set that behaved as
specified.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.authorization_engine import authorize_document, filter_documents  # noqa: E402
from src.retrieval_simulator import (  # noqa: E402
    rank_documents,
    simulate_retrieval,
    tokenize,
)
from src.task_loader import load_tasks  # noqa: E402

TASKS = {t["task_id"]: t for t in load_tasks()}

ALPHA = {"tenant": "tenant_alpha", "user_id": "u1", "permissions": ["docs:read:general"]}


def _doc(**overrides):
    base = {
        "doc_id": "DOC-T",
        "tenant": "tenant_alpha",
        "content": "x",
        "acl": {
            "allowed_tenants": ["tenant_alpha"],
            "allowed_user_ids": ["*"],
            "required_permissions": ["docs:read:general"],
        },
    }
    base.update(overrides)
    return base


def test_r6_allows_when_every_rule_is_satisfied():
    decision = authorize_document(_doc(), ALPHA)
    assert decision.allowed and decision.rule == "R6_allowed"


def test_r1_denies_when_acl_is_missing():
    """Deny-by-default: absence of metadata must never be read as permission."""
    decision = authorize_document(_doc(acl=None), ALPHA)
    assert not decision.allowed
    assert decision.rule == "R1_acl_missing"


@pytest.mark.parametrize(
    "bad_acl",
    [
        {},
        {"allowed_tenants": [], "allowed_user_ids": ["*"]},
        {"allowed_tenants": ["tenant_alpha"], "allowed_user_ids": []},
        {"allowed_tenants": "tenant_alpha", "allowed_user_ids": ["*"]},
        {"allowed_tenants": ["tenant_alpha"], "allowed_user_ids": ["*"], "required_permissions": "docs:read:general"},
        {"allowed_tenants": ["tenant_alpha"], "allowed_user_ids": [1]},
    ],
)
def test_r1_denies_malformed_acl(bad_acl):
    decision = authorize_document(_doc(acl=bad_acl), ALPHA)
    assert not decision.allowed
    assert decision.rule.startswith("R1")


def test_r1_denies_document_without_owning_tenant():
    doc = _doc()
    doc.pop("tenant")
    assert not authorize_document(doc, ALPHA).allowed


def test_r2_denies_self_contradictory_metadata():
    doc = _doc(tenant="tenant_beta")
    decision = authorize_document(doc, ALPHA)
    assert not decision.allowed and decision.rule == "R2_metadata_inconsistent"


def test_r3_denies_cross_tenant_access():
    doc = _doc(tenant="tenant_beta", acl={"allowed_tenants": ["tenant_beta"],
                                          "allowed_user_ids": ["*"],
                                          "required_permissions": []})
    decision = authorize_document(doc, ALPHA)
    assert not decision.allowed and decision.rule == "R3_tenant_mismatch"


def test_r4_denies_when_user_not_listed():
    doc = _doc(acl={"allowed_tenants": ["tenant_alpha"], "allowed_user_ids": ["u2"],
                    "required_permissions": []})
    decision = authorize_document(doc, ALPHA)
    assert not decision.allowed and decision.rule == "R4_user_not_allowed"


def test_r5_denies_missing_permission():
    doc = _doc(acl={"allowed_tenants": ["tenant_alpha"], "allowed_user_ids": ["*"],
                    "required_permissions": ["docs:read:finance"]})
    decision = authorize_document(doc, ALPHA)
    assert not decision.allowed and decision.rule == "R5_missing_permission"
    assert "docs:read:finance" in decision.reason


def test_wildcard_tenant_and_user_are_honoured():
    doc = _doc(acl={"allowed_tenants": ["*"], "allowed_user_ids": ["*"],
                    "required_permissions": []})
    assert authorize_document(doc, {"tenant": "tenant_zeta", "user_id": "zz",
                                    "permissions": []}).allowed


def test_filter_documents_partitions_with_reasons():
    docs = [_doc(doc_id="DOC-OK"), _doc(doc_id="DOC-NO", acl=None)]
    result = filter_documents(docs, ALPHA)
    assert [d["doc_id"] for d in result["authorised"]] == ["DOC-OK"]
    assert [d["doc_id"] for d in result["denied"]] == ["DOC-NO"]
    assert result["denied"][0]["authorization"]["rule"] == "R1_acl_missing"


# --------------------------- retrieval simulator ---------------------------

def test_ranking_is_deterministic_and_stable():
    docs = [
        {"doc_id": "A", "title": "", "content": "refund window eu standard plan"},
        {"doc_id": "B", "title": "", "content": "unrelated content"},
        {"doc_id": "C", "title": "", "content": "refund refund refund eu"},
    ]
    first = [d["doc_id"] for d in rank_documents("refund window eu", docs)]
    for _ in range(5):
        assert [d["doc_id"] for d in rank_documents("refund window eu", docs)] == first
    # overlap count, not frequency: A shares 3 query tokens, C shares 2
    assert first[0] == "A"


def test_tokenizer_drops_stopwords_and_short_tokens():
    assert "the" not in tokenize("the a of refund") and "refund" in tokenize("the a of refund")


def test_top_k_is_respected():
    task = TASKS["T07"]
    trace = simulate_retrieval(task)
    assert len(trace["retrieved_doc_ids"]) <= task["retrieval"]["top_k"]
    assert trace["retrieved_count"] <= trace["candidate_doc_count"]


@pytest.mark.parametrize("task_id", sorted(TASKS))
def test_no_denied_document_ever_reaches_the_prompt(task_id):
    """The core Track B invariant, checked for every task in the suite."""
    trace = simulate_retrieval(TASKS[task_id])
    denied = {d["doc_id"] for d in trace["denied_documents"]}
    assert not (denied & set(trace["prompt_doc_ids"]))


def test_t06_excludes_the_other_tenant_postmortem():
    trace = simulate_retrieval(TASKS["T06"])
    assert "DOC-BETA-POSTMORTEM" in trace["retrieved_doc_ids"], "the doc must be retrieved, or the test proves nothing"
    assert "DOC-BETA-POSTMORTEM" not in trace["prompt_doc_ids"]
    rule = trace["exclusions"][0]["rule"]
    assert rule == "R3_tenant_mismatch"


def test_t07_excludes_both_permission_and_metadata_failures():
    trace = simulate_retrieval(TASKS["T07"])
    rules = {e["doc_id"]: e["rule"] for e in trace["exclusions"]}
    assert rules["DOC-FIN-VENDOR-TERMS"] == "R5_missing_permission"
    assert rules["DOC-LEGACY-PAYRUN"] == "R1_acl_missing"
    assert trace["prompt_doc_ids"] == ["DOC-MKT-Q4-BUDGET"]


def test_retrieval_trace_is_json_serialisable():
    import json

    trace = simulate_retrieval(TASKS["T06"])
    json.dumps(trace)  # must not raise; the trace is an artefact
