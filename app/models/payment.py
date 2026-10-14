from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import PaymentMethod, PaymentStatus


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tariff_id: Mapped[int] = mapped_column(
        ForeignKey("tariffs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    discount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(
            PaymentStatus,
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
    )
    method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(
            PaymentMethod,
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
    )
    installment_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String,
        unique=True,
        nullable=True,
    )
