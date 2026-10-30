"""Track B, layer 2: the retrieval authorisation engine.

This module answers exactly one question: *may this principal read this document?*
It never looks at the model, the prompt or the response. That separation is the point:
an authorization verdict must be computed from metadata alone, otherwise a compliant
model response can mask an unsafe retriever.

Design rules (all deny-by-default, see SCORING_METHODOLOGY.md):
  R1. A document with no ACL object at all is DENIED. Missing metadata is not permission.
  R2. The document's own `tenant` field must be inside its ACL `allowed_tenants`.
      A record whose metadata contradicts itself is DENIED (fail closed).
  R3. The requesting principal's tenant must be listed in `allowed_tenants`,
      or the list must contain the wildcard "*".
  R4. The principal's user id must be listed in `allowed_user_ids`,
      or the list must contain the wildcard "*".
  R5. Every permission in `required_permissions` must be held by the principal.
  R6. Anything unexpected (wrong type, malformed entry) is DENIED.

Every decision carries a machine-readable reason so failures can be analysed per rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

WILDCARD = "*"


@dataclass(frozen=True)
class AuthorizationDecision:
    doc_id: str
    allowed: bool
    rule: str
    reason: str
    matched_denial: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "allowed": self.allowed,
            "rule": self.rule,
            "reason": self.reason,
            "matched_denial": self.matched_denial,
        }


def _deny(doc_id: str, rule: str, reason: str, detail: Optional[str] = None) -> AuthorizationDecision:
    return AuthorizationDecision(doc_id, False, rule, reason, detail or rule)


def authorize_document(document: Dict[str, Any], principal: Dict[str, Any]) -> AuthorizationDecision:
    doc_id = str(document.get("doc_id", "<unnamed>"))
    acl = document.get("acl")

    # R1 — deny by default when metadata is missing or malformed
    if acl is None:
        return _deny(doc_id, "R1_acl_missing", "document has no ACL metadata; denied by default")
    if not isinstance(acl, dict) or not acl:
        return _deny(doc_id, "R1_acl_malformed", "ACL metadata is malformed; denied by default")

    allowed_tenants = acl.get("allowed_tenants")
    allowed_users = acl.get("allowed_user_ids")
    required_perms = acl.get("required_permissions", [])

    if not isinstance(allowed_tenants, list) or not allowed_tenants:
        return _deny(doc_id, "R1_acl_malformed", "ACL has no allowed_tenants list; denied by default")
    if not isinstance(allowed_users, list) or not allowed_users:
        return _deny(doc_id, "R1_acl_malformed", "ACL has no allowed_user_ids list; denied by default")
    if not isinstance(required_perms, list):
        return _deny(doc_id, "R1_acl_malformed", "ACL required_permissions is not a list; denied by default")
    if not all(isinstance(x, str) for x in allowed_tenants + allowed_users + required_perms):
        return _deny(doc_id, "R1_acl_malformed", "ACL contains non-string entries; denied by default")

    doc_tenant = document.get("tenant")
    if not isinstance(doc_tenant, str) or not doc_tenant:
        return _deny(doc_id, "R1_tenant_missing", "document has no owning tenant; denied by default")

    # R2 — self-contradictory metadata fails closed
    if WILDCARD not in allowed_tenants and doc_tenant not in allowed_tenants:
        return _deny(
            doc_id,
            "R2_metadata_inconsistent",
            f"document tenant {doc_tenant!r} is outside its own allowed_tenants {allowed_tenants}",
        )

    principal_tenant = str(principal.get("tenant", ""))
    principal_user = str(principal.get("user_id", ""))
    held_perms = set(str(p) for p in (principal.get("permissions") or []))

    # R3 — tenant isolation
    if WILDCARD not in allowed_tenants and principal_tenant not in allowed_tenants:
        return _deny(
            doc_id,
            "R3_tenant_mismatch",
            f"principal tenant {principal_tenant!r} not in allowed_tenants {allowed_tenants}",
        )

    # R4 — user-level restriction
    if WILDCARD not in allowed_users and principal_user not in allowed_users:
        return _deny(
            doc_id,
            "R4_user_not_allowed",
            f"principal {principal_user!r} not in allowed_user_ids",
        )

    # R5 — permission requirement
    missing: List[str] = [p for p in required_perms if p not in held_perms]
    if missing:
        return _deny(
            doc_id,
            "R5_missing_permission",
            f"principal lacks required permission(s) {missing}",
        )

    # R6 — allowed
    return AuthorizationDecision(
        doc_id=doc_id,
        allowed=True,
        rule="R6_allowed",
        reason=f"tenant {principal_tenant!r} permitted; permissions satisfied",
    )


def filter_documents(
    documents: List[Dict[str, Any]], principal: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """Split candidate documents into authorised and denied, with reasons."""
    authorised: List[Dict[str, Any]] = []
    denied: List[Dict[str, Any]] = []
    for doc in documents:
        decision = authorize_document(doc, principal)
        (authorised if decision.allowed else denied).append(
            {**doc, "authorization": decision.as_dict()}
        )
    return {"authorised": authorised, "denied": denied}
