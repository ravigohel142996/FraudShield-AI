"""Provider adapters. Benchmark logic never imports this module's clients directly.

Every adapter implements `complete(request) -> CompletionResult` and reports its own
limitations honestly:

* `available()` returns False when the credential is missing.
* `estimated_cost_usd()` is an ESTIMATE from a static price table, never a billed
  amount. The runner labels it as an estimate everywhere it is stored.
* Errors are returned as data (with type and message) rather than raised, so a failed
  API call is recorded as an API failure and never mistaken for a model failure.

HTTP is done with `urllib.request` so the core has no third-party dependency. If
`requests` is installed it is not used, on purpose: fewer moving parts, same behaviour.

Credentials are read from the environment only. They are never logged, never written to
a run record, and never included in a manifest.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .settings import env_or_empty

# Static price table (USD per 1M tokens), used ONLY for pre-flight budget estimates.
# Update deliberately; a wrong price changes the estimate, never a score.
PRICE_TABLE: Dict[str, Dict[str, float]] = {
    "openai:gpt-4o-2024-11-20": {"input": 2.50, "output": 10.00},
    "openai:gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
    "anthropic:claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "anthropic:claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "gemini:gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "groq:llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
}


@dataclass
class CompletionRequest:
    model: str
    system_prompt: str
    user_prompt: str
    temperature: float = 0.0
    max_output_tokens: int = 700
    timeout_seconds: int = 60


@dataclass
class CompletionResult:
    ok: bool
    text: str = ""
    error_type: str = ""
    error_message: str = ""
    http_status: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    attempts: int = 1
    raw_response: Dict[str, Any] = field(default_factory=dict)


class ProviderError(RuntimeError):
    pass


class BaseProvider:
    name = "base"
    env_var = ""

    def __init__(self, model: str, max_retries: int = 2, backoff: float = 2.0) -> None:
        self.model = model
        self.max_retries = max(0, int(max_retries))
        self.backoff = max(0.0, float(backoff))
        self.api_key = env_or_empty(self.env_var) if self.env_var else ""

    def available(self) -> bool:
        return bool(self.api_key)

    def availability_note(self) -> str:
        if not self.env_var:
            return "no credential required"
        return "credential present" if self.api_key else f"{self.env_var} is not set"

    def estimated_cost_usd(self, input_tokens: int, output_tokens: int) -> Optional[float]:
        price = PRICE_TABLE.get(f"{self.name}:{self.model}")
        if not price:
            return None
        return (input_tokens / 1_000_000) * price["input"] + (output_tokens / 1_000_000) * price["output"]

    def complete(self, request: CompletionRequest) -> CompletionResult:  # pragma: no cover
        raise NotImplementedError


def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: int) -> tuple:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:  # nosec - fixed provider URLs
        raw = response.read().decode("utf-8", errors="replace")
        return response.status, raw


def _with_retries(fn, max_retries: int, backoff: float) -> CompletionResult:
    last = None
    for attempt in range(1, max_retries + 2):
        try:
            result = fn()
            result.attempts = attempt
            return result
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:600]
            except Exception:
                pass
            last = CompletionResult(
                ok=False,
                error_type="http_error",
                error_message=f"HTTP {exc.code}: {detail}",
                http_status=exc.code,
                attempts=attempt,
            )
            if exc.code in (400, 401, 403, 404):
                return last  # not retryable
        except urllib.error.URLError as exc:
            last = CompletionResult(ok=False, error_type="network_error", error_message=str(exc.reason), attempts=attempt)
        except Exception as exc:  # timeouts, JSON problems
            last = CompletionResult(ok=False, error_type=type(exc).__name__, error_message=str(exc)[:600], attempts=attempt)
        if attempt <= max_retries:
            time.sleep(backoff * (2 ** (attempt - 1)))
    return last or CompletionResult(ok=False, error_type="unknown", error_message="no attempt executed")


class OpenAIProvider(BaseProvider):
    name = "openai"
    env_var = "OPENAI_API_KEY"
    url = "https://api.openai.com/v1/chat/completions"

    def complete(self, request: CompletionRequest) -> CompletionResult:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        started = time.time()

        def call() -> CompletionResult:
            status, raw = _post_json(self.url, headers, payload, request.timeout_seconds)
            data = json.loads(raw)
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            usage = data.get("usage") or {}
            return CompletionResult(
                ok=True,
                text=text,
                http_status=status,
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                latency_ms=int((time.time() - started) * 1000),
                raw_response=data,
            )

        return _with_retries(call, self.max_retries, self.backoff)


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    env_var = "ANTHROPIC_API_KEY"
    url = "https://api.anthropic.com/v1/messages"

    def complete(self, request: CompletionRequest) -> CompletionResult:
        payload = {
            "model": self.model,
            "system": request.system_prompt,
            "messages": [{"role": "user", "content": request.user_prompt}],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        started = time.time()

        def call() -> CompletionResult:
            status, raw = _post_json(self.url, headers, payload, request.timeout_seconds)
            data = json.loads(raw)
            blocks: List[Dict[str, Any]] = data.get("content") or []
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
            usage = data.get("usage") or {}
            return CompletionResult(
                ok=True,
                text=text,
                http_status=status,
                input_tokens=usage.get("input_tokens"),
                output_tokens=usage.get("output_tokens"),
                latency_ms=int((time.time() - started) * 1000),
                raw_response=data,
            )

        return _with_retries(call, self.max_retries, self.backoff)


class GeminiProvider(BaseProvider):
    name = "gemini"
    env_var = "GEMINI_API_KEY"
    base = "https://generativelanguage.googleapis.com/v1beta/models"

    def complete(self, request: CompletionRequest) -> CompletionResult:
        url = f"{self.base}/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "systemInstruction": {"parts": [{"text": request.system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": request.user_prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_output_tokens,
            },
        }
        headers = {"Content-Type": "application/json"}
        started = time.time()

        def call() -> CompletionResult:
            status, raw = _post_json(url, headers, payload, request.timeout_seconds)
            data = json.loads(raw)
            candidates = data.get("candidates") or [{}]
            parts = (candidates[0].get("content") or {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts)
            usage = data.get("usageMetadata") or {}
            return CompletionResult(
                ok=True,
                text=text,
                http_status=status,
                input_tokens=usage.get("promptTokenCount"),
                output_tokens=usage.get("candidatesTokenCount"),
                latency_ms=int((time.time() - started) * 1000),
                raw_response=data,
            )

        return _with_retries(call, self.max_retries, self.backoff)


class GroqProvider(OpenAIProvider):
    name = "groq"
    env_var = "GROQ_API_KEY"
    url = "https://api.groq.com/openai/v1/chat/completions"


class OfflineStubProvider(BaseProvider):
    """Deterministic, non-API provider used ONLY to exercise the pipeline.

    It NEVER contacts a network and its output is NEVER model behaviour. Every record it
    produces is stamped `provider_class: "pipeline_validation_stub"` and
    `counts_as_model_experiment: false`, and the runner writes it to results/validation/
    rather than results/. Reporting its scores as model results would be fabrication.

    Behaviour: returns the text of the highest-authority document, so the pipeline's
    happy path (facts present, citation present, no canary) can be verified end-to-end.
    """

    name = "stub"
    env_var = ""

    def available(self) -> bool:
        return True

    def availability_note(self) -> str:
        return "offline pipeline validation stub - not a model"

    def complete(self, request: CompletionRequest) -> CompletionResult:
        return CompletionResult(
            ok=True,
            text=(
                "STUB RESPONSE (pipeline validation only). "
                f"[{request.user_prompt[:40].replace(chr(10), ' ')}]"
            ),
            input_tokens=len(request.system_prompt.split()) + len(request.user_prompt.split()),
            output_tokens=10,
            latency_ms=0,
            raw_response={"stub": True},
        )


PROVIDERS = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "stub": OfflineStubProvider,
}


def get_provider(name: str, model: str, max_retries: int = 2, backoff: float = 2.0) -> BaseProvider:
    key = (name or "").strip().lower()
    if key not in PROVIDERS:
        raise ProviderError(f"unknown provider {name!r}; known: {sorted(PROVIDERS)}")
    return PROVIDERS[key](model, max_retries=max_retries, backoff=backoff)


def describe_credentials() -> List[Dict[str, str]]:
    """Report which provider credentials exist. Never prints or returns values."""
    rows = []
    for key, cls in PROVIDERS.items():
        if key == "stub":
            continue
        instance = cls(model="<none>")
        rows.append({"provider": key, "env_var": cls.env_var, "status": instance.availability_note()})
    return rows
