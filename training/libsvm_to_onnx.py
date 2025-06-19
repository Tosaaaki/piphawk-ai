from __future__ import annotations

"""LIBSVMモデルをONNXへ変換するスクリプト."""

import argparse
from pathlib import Path

import joblib
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType


def convert_model(model_path: str | Path, n_features: int, out_path: str | Path) -> None:
    """LIBSVM形式で保存されたモデルをONNXファイルへ変換する."""
    model = joblib.load(model_path)
    initial_type = [("input", FloatTensorType([None, n_features]))]
    onx = convert_sklearn(model, initial_types=initial_type)
    Path(out_path).write_bytes(onx.SerializeToString())


def main() -> None:
    """CLIエントリポイント."""
    parser = argparse.ArgumentParser(description="Convert LIBSVM model to ONNX")
    parser.add_argument("model", help="Path to LIBSVM binary model")
    parser.add_argument("--n-features", type=int, required=True, help="Number of input features")
    parser.add_argument("--output", required=True, help="Output ONNX file path")
    args = parser.parse_args()

    convert_model(args.model, args.n_features, args.output)


if __name__ == "__main__":
    main()
