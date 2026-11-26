from contextlib import asynccontextmanager
import logging
from math import isfinite
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.model_loader import load_model

from app.schemas import CustomerInput, PredictionResponse
from app.inference import predict_churn

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = None
    app.state.model_version = None
    try:
        app.state.model, app.state.model_version = load_model()
    except Exception:
        logger.exception("Model unavailable at startup")
    try:
        yield
    finally:
        app.state.model = None
        app.state.model_version = None


app = FastAPI(
    title="ISTEA - Churn API",
    lifespan=lifespan
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_response(request: Request, exc: RequestValidationError):
    # JSON cannot echo a non-finite number from a rejected request.
    errors = jsonable_encoder(
        exc.errors(), custom_encoder={float: lambda value: value if isfinite(value) else str(value)}
    )
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
    if model is None:
        raise HTTPException(status_code=503, detail="Model unavailable")

    request_id = request.state.request_id
    try:
        return PredictionResponse(
            **predict_churn(model, customer),
            model_version=request.app.state.model_version,
            request_id=request_id,
        )
    except Exception:
        logger.exception("Inference failed for request_id=%s", request_id)
        raise HTTPException(status_code=500, detail="Inference failed") from None
