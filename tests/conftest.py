import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.main as api


@pytest.fixture
def sample_customer():
    example = Path(__file__).with_name("fixtures") / "predict_request_valid.json"
    return json.loads(example.read_text(encoding="utf-8"))


@pytest.fixture
def client():
    with TestClient(api.app) as test_client:
        yield test_client
    assert api.app.state.model is None
    assert api.app.state.model_version is None


@pytest.fixture
def contract_client(monkeypatch):
    model = SimpleNamespace(
        classes_=["No", "Yes"],
        predict=lambda _: ["Yes"],
        predict_proba=lambda _: [[0.2, 0.8]],
    )
    monkeypatch.setattr(api, "load_model", lambda: (model, "test/1"))
    with TestClient(api.app) as test_client:
        yield test_client
