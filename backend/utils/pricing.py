# OpenAI pricing as of 2025. Update when prices change.
# https://openai.com/api/pricing/

PRICING = {
    "gpt-4.1-mini": {
        "input_per_1m": 0.40,
        "output_per_1m": 1.60,
    },
    "gpt-4o-mini": {
        "input_per_1m": 0.15,
        "output_per_1m": 0.60,
    },
    "gpt-4o": {
        "input_per_1m": 2.50,
        "output_per_1m": 10.00,
    },
    "gpt-4.1": {
        "input_per_1m": 2.00,
        "output_per_1m": 8.00,
    },
    "text-embedding-3-small": {
        "input_per_1m": 0.02,
    },
    "text-embedding-3-large": {
        "input_per_1m": 0.13,
    },
    "whisper-1": {
        # TODO: confirm exact price — OpenAI lists $0.006/min for Whisper API
        "per_minute": 0.006,
    },
    "gpt-4o-mini-transcribe": {
        # TODO: confirm — listed as $0.003/min on some OpenAI pages
        "per_minute": 0.003,
    },
}


def estimate_text_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICING.get(model)
    if not p or "input_per_1m" not in p:
        return 0.0
    cost = (input_tokens / 1_000_000) * p["input_per_1m"]
    cost += (output_tokens / 1_000_000) * p.get("output_per_1m", 0.0)
    return round(cost, 8)


def estimate_embedding_cost(model: str, input_tokens: int) -> float:
    p = PRICING.get(model)
    if not p or "input_per_1m" not in p:
        return 0.0
    return round((input_tokens / 1_000_000) * p["input_per_1m"], 8)


def estimate_transcription_cost(model: str, duration_minutes: float) -> float:
    p = PRICING.get(model)
    if not p or "per_minute" not in p:
        return 0.0
    return round(duration_minutes * p["per_minute"], 8)
