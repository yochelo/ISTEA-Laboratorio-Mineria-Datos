import json
from datetime import datetime

import pytest
from prometheus_client.parser import text_string_to_metric_families

import app.main as api


def scrape(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/plain")
    return {
        (sample.name, frozenset(sample.labels.items())): sample.value
        for family in text_string_to_metric_families(response.text)
        for sample in family.samples
    }


def delta(before, after, name, **labels):
    key = name, frozenset(labels.items())
    return after.get(key, 0) - before.get(key, 0)


@pytest.mark.dvc
def test_success_updates_metrics_and_correlates_log(client, sample_customer, caplog):
    before = scrape(client)
    response = client.post("/predict", json=sample_customer)
    assert response.status_code == 200
    prediction = response.json()
    version = prediction["model_version"]
    assert version == "ISTEA_Churn/1"
    after = scrape(client)
    assert delta(before, after, "http_requests_total", route="/predict", status="200") == 1
    assert delta(before, after, "ml_predictions_total", model_version=version) == 1
    assert delta(before, after, "ml_prediction_latency_seconds_count") == 1
    assert delta(before, after, "ml_prediction_score_count") == 1
    assert delta(before, after, "ml_prediction_score_sum") == pytest.approx(prediction["probability"])

    event, = [
        json.loads(record.getMessage()) for record in caplog.records
        if record.name == api.logger.name
    ]
    assert event["event"] == "prediction_succeeded"
    assert event["request_id"] == response.headers["X-Request-ID"] == prediction["request_id"]
    assert all(event[key] == value for key, value in prediction.items())
    assert datetime.fromisoformat(event["timestamp"]).utcoffset().total_seconds() == 0
    assert event["duration_seconds"] == pytest.approx(
        delta(before, after, "ml_prediction_latency_seconds_sum")
    )
    assert event["features"] == {
        key: sample_customer[key] for key in ("tenure", "Contract", "MonthlyCharges")
    }


@pytest.mark.parametrize(("status", "event_name"), [
    (422, "validation_rejected"), (503, "model_unavailable"), (500, "inference_failed"),
])
def test_errors_count_http_responses_without_counting_success(
    contract_client, sample_customer, caplog, monkeypatch, status, event_name
):
    def fail(*args):
        raise RuntimeError("internal error detail")

    before = scrape(contract_client)
    with monkeypatch.context() as patch:
        if status == 503:
            patch.setattr(api.app.state, "model", None)
        elif status == 500:
            patch.setattr(api.app.state.model, "predict", fail)
        response = contract_client.post("/predict", json={} if status == 422 else sample_customer)
    assert response.status_code == status
    after = scrape(contract_client)
    assert delta(before, after, "http_requests_total", route="/predict", status=str(status)) == 1
    assert delta(before, after, "ml_predictions_total", model_version="test/1") == 0
    assert delta(before, after, "ml_prediction_score_count") == 0
    assert delta(before, after, "ml_prediction_latency_seconds_count") == (status == 500)
    event, = [
        json.loads(record.getMessage()) for record in caplog.records
        if record.name == api.logger.name
    ]
    assert event["event"] == event_name
    assert event["status"] == status
    assert event["request_id"] == response.headers["X-Request-ID"]
    assert "features" not in event
    assert "internal error detail" not in json.dumps(event)
