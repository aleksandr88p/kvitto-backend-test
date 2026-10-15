from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Payment, PaymentMethod, PaymentStatus, Tariff
from app.schemas import PaymentCreate, PaymentResponse

KVITTO_PROMO_CODE = "KVITTO10"
KVITTO_PROMO_DISCOUNT_PERCENT = 10
INSTALLMENT_MONTHS = (3, 6, 12)


def calculate_discount(price: int, promo_code: str | None) -> int:
    if promo_code is None:
        return 0

    normalized_code = promo_code.strip().upper()
    if not normalized_code:
        return 0
    if normalized_code == KVITTO_PROMO_CODE:
        return price * KVITTO_PROMO_DISCOUNT_PERCENT // 100

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=[
            {
                "type": "value_error",
                "loc": ["body", "promo_code"],
                "msg": "Unknown promo code",
                "input": promo_code,
            }
        ],
    )


def calculate_installment_schedule(
    amount: int,
    installment_months: int | None,
) -> list[int] | None:
    if installment_months is None:
        return None
    if installment_months not in INSTALLMENT_MONTHS:
        raise ValueError("installment_months must be 3, 6, or 12")

    base_amount, remainder = divmod(amount, installment_months)
    return [
        base_amount + (1 if index < remainder else 0)
        for index in range(installment_months)
    ]


def get_payment_by_idempotency_key(
    session: Session,
    idempotency_key: str,
) -> Payment | None:
    return session.scalar(
        select(Payment).where(Payment.idempotency_key == idempotency_key)
    )


def is_idempotency_key_conflict(exc: IntegrityError) -> bool:
    return "idempotency_key" in str(exc.orig or exc)


def create_payment(
    session: Session,
    payment_in: PaymentCreate,
    idempotency_key: str | None = None,
) -> tuple[Payment, bool]:
    if idempotency_key is not None:
        existing_payment = get_payment_by_idempotency_key(
            session,
            idempotency_key,
        )
        if existing_payment is not None:
            return existing_payment, False

    tariff = session.get(Tariff, payment_in.tariff_id)
    if tariff is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tariff not found",
        )

    discount = calculate_discount(tariff.price, payment_in.promo_code)
    amount = tariff.price - discount
    payment = Payment(
        tariff_id=payment_in.tariff_id,
        amount=amount,
        discount=discount,
        status=PaymentStatus.PENDING,
        method=payment_in.method,
        installment_months=payment_in.installment_months,
        email=str(payment_in.email),
        idempotency_key=idempotency_key,
    )
    session.add(payment)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if idempotency_key is None or not is_idempotency_key_conflict(exc):
            raise

        existing_payment = get_payment_by_idempotency_key(
            session,
            idempotency_key,
        )
        if existing_payment is None:
            raise
        return existing_payment, False

    session.refresh(payment)
    return payment, True


def build_payment_response(payment: Payment) -> PaymentResponse:
    schedule = None
    if payment.method == PaymentMethod.INSTALLMENT:
        schedule = calculate_installment_schedule(
            payment.amount,
            payment.installment_months,
        )

    return PaymentResponse(
        id=payment.id,
        status=payment.status,
        tariff_id=payment.tariff_id,
        amount=payment.amount,
        discount=payment.discount,
        method=payment.method,
        installment_months=payment.installment_months,
        schedule=schedule,
        email=payment.email,
        created_at=payment.created_at,
    )
