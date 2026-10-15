from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Payment
from app.schemas import PaymentCreate, PaymentResponse
from app.services import build_payment_response, create_payment

router = APIRouter()


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_payment_endpoint(
    payment_in: PaymentCreate,
    response: Response,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),
) -> PaymentResponse:
    payment, created = create_payment(db, payment_in, idempotency_key)
    if not created:
        response.status_code = status.HTTP_200_OK
    return build_payment_response(payment)


@router.get("/payments/{id}", response_model=PaymentResponse)
def get_payment(
    id: int,
    db: Session = Depends(get_db),
) -> PaymentResponse:
    payment = db.get(Payment, id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return build_payment_response(payment)
