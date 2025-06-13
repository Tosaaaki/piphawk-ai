def test_load_config_env_override(tmp_path, monkeypatch):
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text("adx_trend_min: 30\n")
    monkeypatch.setenv("MODE_DETECTOR_CONFIG", str(cfg_file))
    import importlib.util
    import sys
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("md", Path("analysis/mode_detector.py"))
    md = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(md)
    cfg = md.load_config()
    assert cfg["adx_trend_min"] == 30
    monkeypatch.delenv("MODE_DETECTOR_CONFIG", raising=False)


def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv("MODE_DETECTOR_CONFIG", raising=False)
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("md", Path("analysis/mode_detector.py"))
    md = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(md)
    cfg = md.load_config()
    assert cfg["ema_slope_min"] == 0.1
