import os
import sys
import types

import pytest

if 'pandas' not in sys.modules or not hasattr(sys.modules.get('pandas'), 'DataFrame'):
    try:
        sys.modules.pop('pandas', None)
        import pandas as pd
    except Exception:  # pragma: no cover - fallback when pandas isn't installed
        pd = types.ModuleType('pandas')
        pd.DataFrame = object
    sys.modules['pandas'] = pd


@pytest.fixture(autouse=True, scope="session")
def set_auto_restart_false():
    os.environ["AUTO_RESTART"] = "false"
