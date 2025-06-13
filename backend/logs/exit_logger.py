import json
import logging
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent / "exit_log.jsonl"


def append_exit_log(data: dict) -> None:
    """append JSON data to exit_log.jsonl"""
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            f.write("\n")
    except Exception as exc:
        logging.error(f"Failed to write exit log: {exc}")
