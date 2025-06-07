import csv
import pickle
from pathlib import Path
import sys

from regime.features import RegimeFeatureExtractor
from regime.gmm_detector import GMMRegimeDetector


def load_data(path: Path) -> list[dict]:
    data = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                item = {
                    "high": float(row.get("high", row.get("h", 0)) or 0),
                    "low": float(row.get("low", row.get("l", 0)) or 0),
                    "close": float(row.get("close", row.get("c", 0)) or 0),
                    "volume": float(row.get("volume", row.get("v", 0)) or 0),
                }
            except Exception:
                continue
            data.append(item)
    return data


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/data/range_sample.csv")
    model_path = Path("models/regime_gmm.pkl")
    rows = load_data(csv_path)
    if not rows:
        print("No data loaded")
        return
    extractor = RegimeFeatureExtractor()
    feats = extractor.process_all(rows)
    detector = GMMRegimeDetector(n_components=3, random_state=42)
    detector.fit(feats)
    model_path.parent.mkdir(exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump(detector.model, f)
    print(f"Model saved to {model_path}")


if __name__ == "__main__":
    main()
