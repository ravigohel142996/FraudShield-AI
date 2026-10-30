"""Track B, layer 1: a deterministic retrieval simulator.

Real vector search is stochastic and provider-dependent, which would make an
authorization result unreproducible. For an evaluation benchmark we need the *candidate
set* to be identical on every machine, so retrieval here is a deterministic lexical
ranker:

    score(doc, query) = number of distinct query tokens present in the document body
    rank              = (-score, original candidate order)     # stable tie-break

`top_k` then cuts the ranked list. Only after ranking does the authorization engine run,
which mirrors the real failure mode we care about: ranking decides *what is relevant*,
authorization decides *what may be shown*, and the two are frequently mixed up.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .authorization_engine import authorize_document

_TOKEN_RE = re.compile(r"[a-z0-9]+")
# Deliberately small stoplist: retrieval quality is not what is being measured.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "is", "are", "was",
    "were", "what", "which", "who", "how", "does", "do", "did", "with", "by", "at",
    "from", "that", "this", "it", "be", "as", "per", "me", "my", "our", "we", "you",
    "can", "could", "should", "would", "please", "show", "tell", "give",
}


def tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 1 and t not in _STOPWORDS]


def lexical_score(query: str, content: str) -> int:
    q = set(tokenize(query))
    d = set(tokenize(content))
    return len(q & d)


def rank_documents(query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scored = []
    for index, doc in enumerate(documents):
        score = lexical_score(query, f"{doc.get('title', '')} {doc.get('content', '')}")
        scored.append((score, index, doc))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [{**doc, "retrieval_score": score, "retrieval_rank": rank} for rank, (score, _, doc) in enumerate(scored)]


def simulate_retrieval(task: Dict[str, Any]) -> Dict[str, Any]:
    """Return a full, auditable retrieval trace for one task.

    The trace contains, in order:
      candidates        all documents supplied for the task
      ranked            deterministic lexical ranking (pre-authorization)
      retrieved         the top_k cut
      authorised        documents that will be placed in the prompt
      denied            documents blocked by the authorization engine
      prompt_doc_ids    exactly what the model will see
      excluded_doc_ids  what was withheld, with rule + reason
    """
    principal = task["requesting_principal"]
    docs_by_id = {d["doc_id"]: d for d in task["documents"]}

    retrieval_cfg = task.get("retrieval") or {}
    candidate_ids = retrieval_cfg.get("candidate_doc_ids") or list(docs_by_id)
    missing = [cid for cid in candidate_ids if cid not in docs_by_id]
    if missing:
        raise ValueError(f"{task['task_id']}: retrieval.candidate_doc_ids references unknown docs {missing}")

    query = retrieval_cfg.get("query") or task["user_query"]
    top_k = int(retrieval_cfg.get("top_k", len(candidate_ids)))

    candidates = [docs_by_id[cid] for cid in candidate_ids]
    ranked = rank_documents(query, candidates)
    retrieved = ranked[: max(0, top_k)]

    authorised: List[Dict[str, Any]] = []
    denied: List[Dict[str, Any]] = []
    decisions: List[Dict[str, Any]] = []
    for doc in retrieved:
        decision = authorize_document(doc, principal)
        decisions.append(decision.as_dict())
        if decision.allowed:
            authorised.append(doc)
        else:
            denied.append({**doc, "authorization": decision.as_dict()})

    return {
        "task_id": task["task_id"],
        "retrieval_query": query,
        "top_k": top_k,
        "principal": principal,
        "candidates": [d["doc_id"] for d in candidates],
        "ranked": [
            {"doc_id": d["doc_id"], "score": d["retrieval_score"], "rank": d["retrieval_rank"]}
            for d in ranked
        ],
        "retrieved_doc_ids": [d["doc_id"] for d in retrieved],
        "authorization_decisions": decisions,
        "prompt_doc_ids": [d["doc_id"] for d in authorised],
        "excluded_doc_ids": [d["doc_id"] for d in denied],
        "exclusions": [d["authorization"] for d in denied],
        "authorised_documents": authorised,
        "denied_documents": denied,
        "candidate_doc_count": len(candidates),
        "retrieved_count": len(retrieved),
        "authorised_count": len(authorised),
        "denied_count": len(denied),
    }
