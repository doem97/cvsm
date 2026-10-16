import os

import pytest

from run_record_helpers import Repo


@pytest.fixture(scope="session")
def mlflow_template(tmp_path_factory):
    """A migrated SQLite backend; each test copies it, since migrating takes a few seconds."""
    from mlflow import MlflowClient

    os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
    path = tmp_path_factory.mktemp("template") / "mlflow.db"
    MlflowClient(f"sqlite:///{path}").search_experiments()
    return path


@pytest.fixture
def repo(tmp_path, mlflow_template):
    return Repo(tmp_path, mlflow_template)


@pytest.fixture
def make_repo(tmp_path, mlflow_template):
    return lambda **cfg: Repo(tmp_path, mlflow_template, **cfg)
