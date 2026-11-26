from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


YesNo = Literal["Yes", "No"]
InternetAddOn = Literal["Yes", "No", "No internet service"]


class CustomerInput(BaseModel):
    """Use 'No phone service' in MultipleLines exactly when PhoneService is 'No'.

    Use 'No internet service' in all six internet add-ons exactly when
    InternetService is 'No'.
    """

    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)

    gender: Literal["Female", "Male"]
    SeniorCitizen: int = Field(ge=0, le=1)
    Partner: YesNo
    Dependents: YesNo
    tenure: int = Field(ge=0, le=72)
    PhoneService: YesNo
    MultipleLines: Literal["Yes", "No", "No phone service"]
    InternetService: Literal["DSL", "Fiber optic", "No"]
    OnlineSecurity: InternetAddOn
    OnlineBackup: InternetAddOn
    DeviceProtection: InternetAddOn
    TechSupport: InternetAddOn
    StreamingTV: InternetAddOn
    StreamingMovies: InternetAddOn
    Contract: Literal["Month-to-month", "One year", "Two year"]
    PaperlessBilling: YesNo
    PaymentMethod: Literal[
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ]
    MonthlyCharges: float = Field(gt=0, description="Finite monetary amount.")
    TotalCharges: float | None = Field(
        default=None, ge=0, description="Finite monetary amount, or null if unavailable."
    )

    @model_validator(mode="after")
    def validate_service_consistency(self) -> Self:
        if (self.PhoneService == "No") != (self.MultipleLines == "No phone service"):
            raise ValueError("MultipleLines must agree with PhoneService")

        no_internet = self.InternetService == "No"
        internet_fields = (
            "OnlineSecurity", "OnlineBackup", "DeviceProtection",
            "TechSupport", "StreamingTV", "StreamingMovies",
        )
        inconsistent_fields = [
            field for field in internet_fields
            if (getattr(self, field) == "No internet service") != no_internet
        ]
        if inconsistent_fields:
            raise ValueError(f"Fields must agree with InternetService: {', '.join(inconsistent_fields)}")
        return self


class PredictionResponse(BaseModel):
    prediction: Literal["Yes", "No"]
    probability: float = Field(ge=0, le=1)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    model_version: str
