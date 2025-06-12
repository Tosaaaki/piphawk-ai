"""Select final trade mode with rule fallback."""
from __future__ import annotations

from backend.utils import env_loader

FALLBACK_MAP = {
    "trend": "trend_follow",
    "range": "scalp_reversal",
    "vol_spike": "scalp_momentum",
}

STRAT_VOTE_MIN = int(env_loader.get_env("STRAT_VOTE_MIN", "2"))


def choose_mode(conf_ok: bool, voted_mode: str, regime: str, indicators: dict) -> str:
    """Return final trade mode."""
    if conf_ok:
        return voted_mode
    return FALLBACK_MAP.get(regime, "scalp_momentum")

__all__ = ["choose_mode"]
