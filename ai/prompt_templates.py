"""プロンプトテンプレート管理モジュール"""

PROMPT_TEMPLATES = {
    "news_summary": (
        "Summarize the following news headlines and infer market sentiment in three sentences.\n{text}"
    ),
    "technical_entry": (
        "Based on the given technical indicators, decide entry side and risk levels." 
    ),
}


def get_template(name: str) -> str:
    """テンプレート名から文字列を取得する。"""
    return PROMPT_TEMPLATES.get(name, "")
