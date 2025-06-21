import importlib
import os


def test_trend_adx_default():
    if 'TREND_ADX_THRESH' in os.environ:
        os.environ.pop('TREND_ADX_THRESH')
    import backend.strategy.openai_prompt as prompt
    importlib.reload(prompt)
    assert prompt.TREND_ADX_THRESH == 15.0

def test_trend_adx_env_override():
    os.environ['TREND_ADX_THRESH'] = '30'
    os.environ.setdefault('OPENAI_API_KEY', 'dummy')
    import backend.strategy.openai_prompt as prompt
    importlib.reload(prompt)
    import sys
    import types
    openai_stub = types.ModuleType('openai')
    class DummyClient:
        def __init__(self, *a, **k):
            pass
    openai_stub.OpenAI = DummyClient
    openai_stub.APIError = Exception
    sys.modules.setdefault('openai', openai_stub)
    sys.modules.setdefault('pandas', types.ModuleType('pandas'))
    from backend.strategy import openai_analysis
    importlib.reload(openai_analysis)
    assert prompt.TREND_ADX_THRESH == 30.0
    assert openai_analysis.TREND_ADX_THRESH == 30.0
    os.environ.pop('TREND_ADX_THRESH')
    sys.modules.pop('openai', None)
    sys.modules.pop('pandas', None)
