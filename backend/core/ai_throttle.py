"""AI call cooldown management."""

from backend.utils import env_loader


def get_cooldown(mode: str) -> int:
    """Return cooldown seconds for the given mode."""
    scalp_val = int(env_loader.get_env("SCALP_MOMENTUM_COOLDOWN_SEC", "20"))
    default_val = int(env_loader.get_env("AI_COOLDOWN_SEC", "60"))
    return scalp_val if mode == "scalp_momentum" else default_val
