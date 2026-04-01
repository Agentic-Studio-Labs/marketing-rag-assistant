from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import anthropic as anthropic_mod

_lock = threading.Lock()
_client: anthropic_mod.Anthropic | None = None

COST_PER_1M_INPUT: dict[str, float] = {
    "claude-haiku-4-5-20251001": 0.80,
    "claude-sonnet-4-20250514": 3.00,
    "claude-opus-4-20250514": 15.00,
}
COST_PER_1M_OUTPUT: dict[str, float] = {
    "claude-haiku-4-5-20251001": 4.00,
    "claude-sonnet-4-20250514": 15.00,
    "claude-opus-4-20250514": 75.00,
}
DEFAULT_INPUT_COST = 1.00
DEFAULT_OUTPUT_COST = 5.00


@dataclass
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


def _get_client(api_key: str) -> anthropic_mod.Anthropic:
    global _client
    with _lock:
        if _client is None:
            import anthropic

            _client = anthropic.Anthropic(api_key=api_key)
        return _client


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    inp = COST_PER_1M_INPUT.get(model, DEFAULT_INPUT_COST)
    out = COST_PER_1M_OUTPUT.get(model, DEFAULT_OUTPUT_COST)
    return (input_tokens * inp + output_tokens * out) / 1_000_000


def generate_answer(user_query: str, context_blocks: list[str]) -> LLMResult:
    key = os.environ.get("ANTHROPIC_API_KEY")
    context = "\n\n---\n\n".join(context_blocks)
    if not key:
        text = (
            "ANTHROPIC_API_KEY is not set — retrieval-only mode.\n\n"
            f"Your question: {user_query}\n\n"
            "Retrieved passages:\n\n"
            f"{context}"
        )
        return LLMResult(text=text, model="none", input_tokens=0, output_tokens=0, cost_usd=0.0)

    client = _get_client(key)
    system = (
        "You are a marketing content assistant. Answer using only the provided passages. "
        "If the passages do not contain enough information, say what is missing. "
        "Be concise and cite which themes you used implicitly."
    )
    user = f"Passages:\n\n{context}\n\nQuestion: {user_query}"

    model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    msg = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )

    block = msg.content[0]
    text = block.text if block.type == "text" else str(block)
    input_tokens = msg.usage.input_tokens
    output_tokens = msg.usage.output_tokens
    cost = _estimate_cost(model, input_tokens, output_tokens)

    return LLMResult(
        text=text,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
    )
