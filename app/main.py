from contextlib import asynccontextmanager
from math import isfinite

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.model_loader import load_model

from app.schemas import CustomerInput, PredictionResponse
from app.inference import predict_churn


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = load_model()
    yield


app = FastAPI(
    title="ISTEA - Churn API",
    lifespan=lifespan
)


@app.exception_handler(RequestValidationError)
async def validation_error_response(request: Request, exc: RequestValidationError):
    # JSON cannot echo a non-finite number from a rejected request.
    errors = jsonable_encoder(
        exc.errors(), custom_encoder={float: lambda value: value if isfinite(value) else str(value)}
    )
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict", response_model=PredictionResponse)
def predict(customer: CustomerInput, request: Request):
    model = request.app.state.model
    return predict_churn(model, customer)
