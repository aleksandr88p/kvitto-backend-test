from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Tariff
from app.schemas import TariffResponse

router = APIRouter()


@router.get("/tariffs", response_model=list[TariffResponse])
def list_tariffs(db: Session = Depends(get_db)) -> list[Tariff]:
    return list(db.scalars(select(Tariff).order_by(Tariff.id)))
