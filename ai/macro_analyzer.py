"""FRED と GDELT からニュースを取得して要約するモジュール"""
from __future__ import annotations

import requests
from typing import Any

from backend.utils import env_loader
from ai.local_model import ask_model
from ai.prompt_templates import get_template


class MacroAnalyzer:
    """経済ニュース要約とセンチメント解析を行うクラス"""

    def __init__(self, fred_api_key: str | None = None):
        self.fred_api_key = fred_api_key or env_loader.get_env("FRED_API_KEY")

    # ------------------------------------------------------------
    # FRED API
    # ------------------------------------------------------------
    def fetch_fred_series(self, series_id: str, limit: int = 10) -> list[dict]:
        if not self.fred_api_key:
            raise RuntimeError("FRED_API_KEY not set")
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.fred_api_key,
            "file_type": "json",
            "limit": limit,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("observations", [])

    # ------------------------------------------------------------
    # GDELT API
    # ------------------------------------------------------------
    def fetch_gdelt_articles(self, query: str, maxrecords: int = 10) -> list[dict]:
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": maxrecords,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("articles", [])

    def summarize_articles(self, articles: list[dict]) -> str:
        headlines = [a.get("title") or a.get("semtitle") or "" for a in articles]
        text = "\n".join(headlines)
        prompt = get_template("news_summary").format(text=text)
        result = ask_model(prompt)
        if isinstance(result, dict):
            return result.get("summary") or result.get("text", "")
        return str(result)

    def get_market_summary(
        self, query: str = "economy", series_id: str = "UNRATE"
    ) -> dict[str, Any]:
        """FRED 指標とニュース要約をまとめて取得する"""
        fred = []
        try:
            fred = self.fetch_fred_series(series_id, 5)
        except Exception:
            fred = []
        articles = []
        try:
            articles = self.fetch_gdelt_articles(query, 5)
        except Exception:
            articles = []
        summary = ""
        if articles:
            try:
                summary = self.summarize_articles(articles)
            except Exception:
                summary = ""
        return {"fred": fred, "summary": summary, "articles": articles}
