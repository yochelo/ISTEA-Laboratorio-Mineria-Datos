from contextlib import asynccontextmanager
from datetime import UTC, datetime
import json
import logging
from math import isfinite
import sys
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, make_asgi_app

from app.model_loader import load_model

from app.schemas import CustomerInput, PredictionResponse
from app.inference import predict_churn

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.propagate = False

PREDICTIONS = Counter(
    "ml_predictions_total", "Successful predictions", ["model_version"]
)
LATENCY = Histogram("ml_prediction_latency_seconds", "Inference duration in seconds")
HTTP_REQUESTS = Counter(
    "http_requests_total", "HTTP responses", ["route", "status"]
)
SCORE = Histogram(
    "ml_prediction_score",
    "Positive-class score for successful predictions",
    buckets=(0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1),
)


def log_event(event, *, level=logging.INFO, **fields):
    logger.log(level, json.dumps({
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "event": event,
        **fields,
    }))


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_event("startup")
    app.state.model = None
    app.state.model_version = None
    try:
        app.state.model, app.state.model_version = load_model()
    except Exception as exc:
        log_event("model_unavailable", level=logging.ERROR, phase="startup",
                  error_type=type(exc).__name__)
    else:
        log_event("model_loaded", model_version=app.state.model_version)
    try:
        yield
    finally:
        app.state.model = None
        app.state.model_version = None


app = FastAPI(
    title="ISTEA - Churn API",
    lifespan=lifespan
)
app.mount("/metrics", make_asgi_app())


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    route = getattr(request.scope.get("route"), "path", None)
    if route is None:
        route = "/metrics" if request.url.path in ("/metrics", "/metrics/") else "unmatched"
    HTTP_REQUESTS.labels(route=route, status=response.status_code).inc()
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_response(request: Request, exc: RequestValidationError):
    # JSON cannot echo a non-finite number from a rejected request.
    errors = jsonable_encoder(
        exc.errors(), custom_encoder={float: lambda value: value if isfinite(value) else str(value)}
    )
    log_event("validation_rejected", request_id=request.state.request_id,
              status=422, error_count=len(errors))
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/health")
def health(request: Request):
    if request.app.state.model is None:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok", "model_version": request.app.state.model_version}


@app.get("/live")
def live():
    return {"status": "alive"}


@app.get("/ready")
def ready(request: Request):
    if request.app.state.model is None:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}


@app.post(
    "/predict",
    response_model=PredictionResponse,
    responses={503: {"description": "Model unavailable"}, 500: {"description": "Inference failed"}},
)
def predict(customer: CustomerInput, request: Request):
    model = request.app.state.model
    request_id = request.state.request_id
    model_version = request.app.state.model_version
    if model is None:
        log_event("model_unavailable", level=logging.WARNING, phase="prediction",
                  request_id=request_id, status=503)
        raise HTTPException(status_code=503, detail="Model unavailable")

    try:
        started = perf_counter()
        try:
            prediction = predict_churn(model, customer)
        finally:
            duration = perf_counter() - started
            LATENCY.observe(duration)
        result = PredictionResponse(
            **prediction,
            model_version=model_version,
            request_id=request_id,
        )
    except Exception as exc:
        log_event("inference_failed", level=logging.ERROR, request_id=request_id,
                  model_version=model_version, status=500, error_type=type(exc).__name__)
        raise HTTPException(status_code=500, detail="Inference failed") from None

    PREDICTIONS.labels(model_version=model_version).inc()
    SCORE.observe(result.probability)
    log_event(
        "prediction_succeeded",
        **result.model_dump(),
        duration_seconds=duration,
        features={
            "tenure": customer.tenure,
            "Contract": customer.Contract,
            "MonthlyCharges": customer.MonthlyCharges,
        },
    )
    return result
