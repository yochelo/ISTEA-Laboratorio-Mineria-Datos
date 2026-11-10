from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.model_loader import load_model

from fastapi import Request
from app.schemas import CustomerInput
from app.inference import predict_churn


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = load_model()
    yield


app = FastAPI(
    title="ISTEA - Churn API",
    lifespan=lifespan
)


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
def predict(customer: CustomerInput, request: Request):
    model = request.app.state.model
    return predict_churn(model, customer)