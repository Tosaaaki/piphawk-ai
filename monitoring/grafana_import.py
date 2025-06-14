"""Grafana ダッシュボードをインポートするスクリプト."""

from __future__ import annotations

import os

import requests

GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN", "")
DASHBOARD_ID = 12011


def import_dashboard(dashboard_id: int = DASHBOARD_ID) -> dict:
    """指定 ID のダッシュボードをダウンロードしてインポートする."""
    download_url = f"https://grafana.com/api/dashboards/{dashboard_id}/revisions/latest/download"
    response = requests.get(download_url, timeout=10)
    response.raise_for_status()
    dashboard_json = response.json()

    import_url = f"{GRAFANA_URL}/api/dashboards/db"
    headers = {
        "Authorization": f"Bearer {GRAFANA_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"dashboard": dashboard_json["dashboard"], "overwrite": True}
    r = requests.post(import_url, json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    import_dashboard()
