import pytest

from run_record_helpers import Repo


@pytest.fixture
def repo(tmp_path):
    return Repo(tmp_path)


@pytest.fixture
def make_repo(tmp_path):
    return lambda **cfg: Repo(tmp_path, **cfg)
