import os
import requests
from datetime import datetime, timedelta

OANDA_API_URL = "https://api-fxtrade.oanda.com/v3/instruments/{instrument}/candles"
OANDA_API_KEY = os.getenv("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")

def fetch_candles(instrument=None, granularity="M1", count=500):
    """
    Fetch candlestick data from OANDA API.
    
    Parameters:
        instrument (str): The instrument to fetch data for (e.g. "EUR_USD").
        granularity (str): The granularity of the candles (e.g. "M1", "H1").
        count (int): Number of candles to fetch (max 5000).
        
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
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if "candles" in data:
            return data["candles"]
        else:
            print(f"No candles found in response for {instrument}")
            return []
    except requests.RequestException as e:
        print(f"Error fetching candles for {instrument}: {e}")
        return []


if __name__ == "__main__":
    instrument = os.getenv('DEFAULT_PAIR', 'USD_JPY')
    granularity = 'M5'
    candles = fetch_candles(instrument, granularity)
    print(candles)
