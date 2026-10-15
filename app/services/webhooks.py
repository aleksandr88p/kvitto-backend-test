from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Payment, PaymentStatus
from app.schemas import BankWebhookRequest

ALLOWED_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.PENDING: {PaymentStatus.SUCCEEDED, PaymentStatus.FAILED},
    PaymentStatus.SUCCEEDED: {PaymentStatus.REFUNDED},
}


class InvalidPaymentTransition(Exception):
    pass


def process_bank_webhook(
    session: Session,
    webhook: BankWebhookRequest,
) -> None:
    payment = session.get(Payment, webhook.payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    allowed_statuses = ALLOWED_TRANSITIONS.get(payment.status, set())
    if webhook.status not in allowed_statuses:
        raise InvalidPaymentTransition

    payment.status = webhook.status
    session.commit()
