import os
import re
from typing import Dict, List

from huggingface_hub import InferenceClient


def get_hf_client() -> InferenceClient:
    hf_token = os.getenv("HUGGINGFACE_HUB_TOKEN")
    if not hf_token:
        raise RuntimeError("Missing HUGGINGFACE_HUB_TOKEN in .env")
    return InferenceClient("HuggingFaceH4/zephyr-7b-beta", token=hf_token)


# ── simple deterministic rule ──────────────────────────────────────
def _simple_percent_rule(prompt: str, names: List[str], total: float) -> Dict | None:
    """
    Detect patterns like 'George only split 20%' and return a calculated allocation.
    Returns None if no such pattern is found.
    """
    m = re.search(r"(\w+).*?(\d+)%", prompt, re.I)
    if not m:
        return None

    target, pct = m.group(1), float(m.group(2)) / 100
    if target not in names:
        return None

    allocation = {n: 0.0 for n in names}
    allocation[target] = round(total * pct, 2)

    remaining = round(total - allocation[target], 2)
    others    = [n for n in names if n != target]
    even      = round(remaining / len(others), 2) if others else 0.0
    for n in others:
        allocation[n] = even

    return {"allocation": allocation, "summary": "Split by explicit percent rule in prompt."}

# ── main helper ───────────────────────────────────────────────────────────────
def get_split_suggestion(parsed: Dict, user_prompt: str, names: List[str]) -> Dict:
    """
    Return a dict with keys 'allocation' and 'summary'.
    Falls back to LLM if a deterministic rule isn't detected.
    """
    total = parsed["total"]

    # 1. deterministic percent rule
    if result := _simple_percent_rule(user_prompt, names, total):
        return result

    # 2. LLM fallback
    items_desc = "\n".join(f"- {it['name']}: ${it['price']:.2f}" for it in parsed["items"])
    prompt = f"""
        Participants: {', '.join(names)}

        Items:
        {items_desc}
        Tax: {parsed['tax']:.2f}
        Total: {total:.2f}

        Instruction: {user_prompt}

        Return JSON exactly in this form:
        {{
        "allocation": {{"<name>": <amount>, ...}},
        "summary": "<brief>"
        }}
            """.strip()

    client = get_hf_client()
    raw = client.text_generation(prompt=prompt, max_new_tokens=256)


    # try to eval clean JSON/dict the model outputs
    try:
        data = eval(raw)
        if isinstance(data, dict) and "allocation" in data:
            return data
    except Exception:
        pass

    return {"raw": raw, "summary": "Model response could not be parsed."}
