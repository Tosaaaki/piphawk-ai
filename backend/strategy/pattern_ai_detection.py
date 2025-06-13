import json

from backend.utils import env_loader, openai_client

# Environment-driven defaults
AI_PATTERN_MODEL = env_loader.get_env("AI_PATTERN_MODEL", openai_client.AI_MODEL)
AI_PATTERN_MAX_TOKENS = int(env_loader.get_env("AI_PATTERN_MAX_TOKENS", "256"))


def detect_chart_pattern(candles: list, patterns: list[str]) -> dict:
    """Detect chart patterns using OpenAI.

    Parameters
    ----------
    candles : list
        List of candlestick data dictionaries.
    patterns : list[str]
        Chart pattern names to check for.

    Returns
    -------
    dict
        {"pattern": "<name>"} if a match was found, otherwise {"pattern": None}.
    """
    if not patterns:
        return {"pattern": None}

    system_prompt = (
        "You are a technical analysis assistant. "
        "Respond strictly with a JSON object like {\"pattern\": \"double_top\"} "
        "or {\"pattern\": null}."
    )

    patterns_str = ", ".join(patterns)
    user_prompt = (
        f"Candlestick data:\n{json.dumps(candles, ensure_ascii=False)}\n\n"
        f"Check for these patterns: {patterns_str}. "
        "Return the pattern name if found, otherwise null."
    )

    try:
        data = openai_client.ask_openai(
            user_prompt,
            system_prompt=system_prompt,
            model=AI_PATTERN_MODEL,
            max_tokens=AI_PATTERN_MAX_TOKENS,
            temperature=0.0,
        )
        if isinstance(data, dict) and "pattern" in data:
            return {"pattern": data.get("pattern")}
    except Exception:
        pass

    return {"pattern": None}
