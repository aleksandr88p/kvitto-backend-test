from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import BankWebhookRequest
from app.services import InvalidPaymentTransition, process_bank_webhook

router = APIRouter()


@router.post("/webhooks/bank", response_model=None)
def bank_webhook(
    webhook: BankWebhookRequest,
    db: Session = Depends(get_db),
) -> dict[str, str] | JSONResponse:
    try:
        process_bank_webhook(db, webhook)
    except InvalidPaymentTransition:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "invalid_transition"},
        )
    return {"result": "ok"}
