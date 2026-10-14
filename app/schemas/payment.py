from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from app.models.enums import PaymentMethod, PaymentStatus

WEBHOOK_ALLOWED_STATUSES = {
    PaymentStatus.SUCCEEDED,
    PaymentStatus.FAILED,
    PaymentStatus.REFUNDED,
}


def _validate_installment_months(
    method: PaymentMethod,
    installment_months: int | None,
) -> None:
    if method == PaymentMethod.INSTALLMENT and installment_months is None:
        raise ValueError("installment_months is required for installment payments")
    if method != PaymentMethod.INSTALLMENT and installment_months is not None:
        raise ValueError("installment_months must be null for card and sbp payments")


class PaymentCreate(BaseModel):
    tariff_id: int
    email: EmailStr
    method: PaymentMethod
    installment_months: Literal[3, 6, 12] | None = None
    promo_code: str | None = None

    @model_validator(mode="after")
    def validate_installment(self) -> Self:
        _validate_installment_months(self.method, self.installment_months)
        return self


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: PaymentStatus
    tariff_id: int
    amount: int
    discount: int
    method: PaymentMethod
    installment_months: Literal[3, 6, 12] | None
    schedule: list[int] | None = None
    email: EmailStr
    created_at: datetime

    @model_validator(mode="after")
    def validate_installment(self) -> Self:
        _validate_installment_months(self.method, self.installment_months)
        return self


class BankWebhookRequest(BaseModel):
    payment_id: int
    status: PaymentStatus

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: PaymentStatus) -> PaymentStatus:
        if value not in WEBHOOK_ALLOWED_STATUSES:
            raise ValueError("status must be succeeded, failed, or refunded")
        return value
