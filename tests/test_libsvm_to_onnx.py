from pathlib import Path

import joblib
import pytest
from sklearn.datasets import make_classification
from sklearn.svm import SVC

try:
    from training.libsvm_to_onnx import convert_model
except Exception as e:  # pragma: no cover - 環境依存
    pytest.skip(f"onnx conversion not supported: {e}", allow_module_level=True)


def test_libsvm_to_onnx(tmp_path: Path) -> None:
    X, y = make_classification(n_samples=20, n_features=4, random_state=42)
    model = SVC(probability=True)
    model.fit(X, y)
    model_file = tmp_path / "model.pkl"
    joblib.dump(model, model_file)

    out_file = tmp_path / "model.onnx"
    convert_model(model_file, 4, out_file)
    assert out_file.exists()
    assert out_file.stat().st_size > 0
