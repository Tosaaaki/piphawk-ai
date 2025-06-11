"""FRED と GDELT からニュースを取得して要約するモジュール"""
from __future__ import annotations

import asyncio
import requests
from typing import Any
import httpx

from backend.utils import env_loader, run_async
from piphawk_ai.ai.local_model import ask_model, ask_model_async
from piphawk_ai.ai.prompt_templates import get_template


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

    async def fetch_fred_series_async(self, series_id: str, limit: int = 10) -> list[dict]:
        """非同期で FRED データを取得する"""
        if not self.fred_api_key:
            raise RuntimeError("FRED_API_KEY not set")
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.fred_api_key,
            "file_type": "json",
            "limit": limit,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
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

    async def fetch_gdelt_articles_async(self, query: str, maxrecords: int = 10) -> list[dict]:
        """非同期で GDELT ニュースを取得する"""
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": maxrecords,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
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

    async def analyze_sentiment_async(self, summary: str) -> str:
        """ニュース要約からリスクオン/オフを判定する"""
        prompt = (
            "Classify the following news summary as 'risk_on' or 'risk_off' only.\n" + summary
        )
        result = await ask_model_async(prompt)
        if isinstance(result, dict):
            return result.get("sentiment") or result.get("text", "")
        return str(result)

    async def summarize_articles_async(self, articles: list[dict]) -> str:
        """LLM を用いてニュースの要約を非同期に取得する"""
        headlines = [a.get("title") or a.get("semtitle") or "" for a in articles]
        text = "\n".join(headlines)
        prompt = get_template("news_summary").format(text=text)
        result = await ask_model_async(prompt)
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
        sentiment = None
        if articles:
            try:
                summary = self.summarize_articles(articles)
                sentiment = run_async(self.analyze_sentiment_async(summary))
            except Exception:
                summary = ""
                sentiment = None
        return {"fred": fred, "summary": summary, "articles": articles, "sentiment": sentiment}

    async def get_market_summary_async(
        self, query: str = "economy", series_id: str = "UNRATE"
    ) -> dict[str, Any]:
        """非同期版 ``get_market_summary``"""
        try:
            fred_task = self.fetch_fred_series_async(series_id, 5)
            news_task = self.fetch_gdelt_articles_async(query, 5)
            fred, articles = await asyncio.gather(fred_task, news_task)
        except Exception:
            fred, articles = [], []
        summary = ""
        sentiment = None
        if articles:
            try:
                summary = await self.summarize_articles_async(articles)
                sentiment = await self.analyze_sentiment_async(summary)
            except Exception:
                summary = ""
                sentiment = None
        return {"fred": fred, "summary": summary, "articles": articles, "sentiment": sentiment}
