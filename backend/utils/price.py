"""
Utility helpers for price formatting / rounding before sending orders
to the OANDA REST v3 API.

OANDA rejects an order when the supplied price contains more decimal
places than the instrument allows (error code: PRICE_PRECISION_EXCEEDED).
For JPY‑quoted pairs the maximum precision is 3 decimal places; for most
other major pairs it is 5.  This helper guarantees that every price
string we send conforms to the instrument’s requirements.

Usage:
    from backend.utils.price import format_price

    price_str = format_price("USD_JPY", 143.25099999999998)  # -> '143.251'
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Dict

# Mapping of instrument → maximum number of decimal places allowed by OANDA
# Extend this dictionary as needed when new pairs are traded.
_PRECISION_MAP: Dict[str, int] = {
    # JPY crosses (3 dp = 0.001)
    "USD_JPY": 3,
    "EUR_JPY": 3,
    "GBP_JPY": 3,
    "AUD_JPY": 3,
    "NZD_JPY": 3,
    "CAD_JPY": 3,
    "CHF_JPY": 3,
    "SGD_JPY": 3,
    # Default (major pairs, metals, etc.) → 5 dp
}

_DEFAULT_PRECISION = 5  # fallback for any instrument not explicitly listed


def _get_precision(instrument: str) -> int:
    """
    Return the permitted number of decimal places for *instrument*.
    """
    return _PRECISION_MAP.get(instrument.upper(), _DEFAULT_PRECISION)


def format_price(instrument: str, price: float | Decimal) -> str:
    """
    Round *price* to the maximum precision allowed for *instrument* and
    return it as a string suitable for the OANDA order payload.

    Parameters
    ----------
    instrument : str
        e.g. 'USD_JPY', 'EUR_USD'
    price : float | Decimal
        Numeric price

    Returns
    -------
    str
        Price rounded *half‑up* to the correct number of decimal places,
        with any trailing zeros preserved (e.g. '143.250' not '143.25').
    """
    precision = _get_precision(instrument)
    quant = Decimal("1").scaleb(-precision)  # 0.001 for 3 dp, 0.00001 for 5 dp
    dec_price = Decimal(str(price)).quantize(quant, rounding=ROUND_HALF_UP)
    # format with fixed number of decimals
    return f"{dec_price:.{precision}f}"
