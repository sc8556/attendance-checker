import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import seed  # noqa: E402


@pytest.fixture
def conn():
    """테스트마다 새로 만든 메모리 DB."""
    c = sqlite3.connect(":memory:")
    seed.build(c)
    yield c
    c.close()
