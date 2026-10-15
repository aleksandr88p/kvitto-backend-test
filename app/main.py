from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from app import models
from app.core.database import Base, SessionLocal, engine
from app.routers import payments, tariffs, webhooks

INITIAL_TARIFFS = (
    ("basic", 990000),
    ("standard", 1990000),
    ("premium", 2990000),
)


def seed_tariffs() -> None:
    with SessionLocal() as session:
        existing_titles = set(
            session.scalars(
                select(models.Tariff.title).where(
                    models.Tariff.title.in_(
                        [title for title, _ in INITIAL_TARIFFS]
                    )
                )
            )
        )
        missing_tariffs = [
            models.Tariff(title=title, price=price)
            for title, price in INITIAL_TARIFFS
            if title not in existing_titles
        ]
        if missing_tariffs:
            session.add_all(missing_tariffs)
            session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    seed_tariffs()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(tariffs.router)
app.include_router(payments.router)
app.include_router(webhooks.router)
