from enum import StrEnum


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(StrEnum):
    CARD = "card"
    SBP = "sbp"
    INSTALLMENT = "installment"
