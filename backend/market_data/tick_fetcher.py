import logging
import requests
from backend.utils import env_loader

# env_loader automatically loads default env files at import time

OANDA_API_URL = env_loader.get_env('OANDA_API_URL', 'https://api-fxtrade.oanda.com/v3')
OANDA_API_KEY = env_loader.get_env('OANDA_API_KEY')
OANDA_ACCOUNT_ID = env_loader.get_env('OANDA_ACCOUNT_ID')

logger = logging.getLogger(__name__)

def fetch_tick_data(instrument: str | None = None, *, include_liquidity: bool = False):
    """Fetch the latest tick (pricing) data from the OANDA API.

    Parameters
    ----------
    instrument : str | None
        The instrument to fetch (e.g. ``"USD_JPY"``). If ``None`` the value of
        ``DEFAULT_PAIR`` from the environment is used.

    include_liquidity : bool
        If ``True`` the request includes order book liquidity information.

    Returns
    -------
    dict | None
        JSON response from the OANDA API with tick data, or ``None`` on error.
    """
    if instrument is None:
        instrument = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")
    if not OANDA_API_KEY or not OANDA_ACCOUNT_ID:
        raise EnvironmentError("OANDA_API_KEY or OANDA_ACCOUNT_ID not set in environment variables.")
    url = f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/pricing"
    headers = {
        "Authorization": f"Bearer {OANDA_API_KEY}"
    }
    params = {
        "instruments": instrument,
        "since": None,
        "includeUnitsAvailable": str(include_liquidity).lower(),
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error("Error fetching tick data: %s", e)
        return None

# Example usage (remove or comment out in production)
if __name__ == "__main__":
    instrument = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")
    data = fetch_tick_data(instrument)
    logger.debug("%s", data)
