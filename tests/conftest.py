import os
import pytest

@pytest.fixture(autouse=True, scope="session")
def set_auto_restart_false():
    os.environ["AUTO_RESTART"] = "false"
