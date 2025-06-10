import os
import logging
import requests
from datetime import datetime, timedelta, timezone

OANDA_API_URL = "https://api-fxtrade.oanda.com/v3/instruments/{instrument}/candles"
OANDA_API_KEY = os.getenv("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")

logger = logging.getLogger(__name__)

def fetch_candles(
    instrument=None,
    granularity="M1",
    count=500,
    timeout=10,
    *,
    allow_incomplete: bool = False,
):
    """
    Fetch candlestick data from OANDA API.
    
    Parameters:
        instrument (str): The instrument to fetch data for (e.g. "USD_JPY").
        granularity (str): The granularity of the candles (e.g. "M1", "H1").
        count (int): Number of candles to fetch (max 5000).
        timeout (int | float): Timeout in seconds for the HTTP request.
        allow_incomplete (bool): If True, include the most recent incomplete candle.
        
    Returns:
        list: List of candle data dictionaries.
    """
    if instrument is None:
        instrument = os.getenv("DEFAULT_PAIR")
        if not instrument:
            raise ValueError("Instrument not specified and DEFAULT_PAIR environment variable is not set.")
    headers = {
        "Authorization": f"Bearer {OANDA_API_KEY}"
    }
    params = {
        "granularity": granularity,
        "count": count,
        "price": "M"  # Midpoint prices
    }
    url = OANDA_API_URL.format(instrument=instrument)
    try:
        response = requests.get(
            url, headers=headers, params=params, timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        if "candles" in data:
            candles = data["candles"]
            if not allow_incomplete:
                if candles and not candles[-1].get("complete"):
                    logger.debug(
                        "M%s incomplete; using last complete bar T-1", granularity
                    )
                candles = [c for c in candles if c.get("complete")]
            return candles
        else:
            logger.warning("No candles found in response for %s", instrument)
            return []
    except requests.Timeout:
        logger.warning("Request timed out while fetching candles for %s", instrument)
        return []
    except requests.RequestException as e:
        logger.error("Error fetching candles for %s: %s", instrument, e)
        return []


# New function to fetch multiple timeframes
def _parse_env_timeframes() -> dict:
    """環境変数 ``TRADE_TIMEFRAMES`` を解析して辞書を返す。"""
    tf_env = os.getenv("TRADE_TIMEFRAMES")
    if not tf_env:
        return {}
    result: dict[str, int] = {}
    for item in tf_env.split(","):
        if ":" not in item:
            continue
        tf, cnt = item.split(":", 1)
        tf = tf.strip().upper()
        try:
            result[tf] = int(cnt)
        except ValueError:
            continue
    return result


def fetch_multiple_timeframes(instrument=None, timeframes=None):
    """複数の時間足のローソク足をまとめて取得する。"""
    if timeframes is None:
        timeframes = _parse_env_timeframes()
    if not timeframes:
        timeframes = {
            "M1": 20,   # 短期エントリ分析
            "M5": 50,   # 中期トレンド分析
            "M15": 50,  # 15分足
            "H1": 120,  # 1時間足
            "H4": 90,   # 4時間足
            "D": 90,    # 日足
        }

    scalp_tf = os.getenv("SCALP_COND_TF", "").upper()
    if scalp_tf and scalp_tf not in timeframes:
        default_count = 60
        timeframes[scalp_tf] = default_count

    candles_by_timeframe = {}
    for granularity, count in timeframes.items():
        fetch_gran = "D" if granularity == "D1" else granularity
        candles = fetch_candles(
            instrument,
            fetch_gran,
            count,
            allow_incomplete=True,
        )
        incomplete = bool(candles and not candles[-1].get("complete"))
        logger.debug(
            "%s bars fetched: %d (incomplete=%s)", granularity, len(candles), incomplete
        )
        candles_by_timeframe[granularity] = candles
    
    return candles_by_timeframe


if __name__ == "__main__":
    instrument = os.getenv('DEFAULT_PAIR', 'USD_JPY')
    candles = fetch_multiple_timeframes(instrument)
    for tf, data in candles.items():
        logger.info("%s candles (%d):", tf, len(data))
        logger.info("%s", data[:3])  # Print first 3 candles as a sample
