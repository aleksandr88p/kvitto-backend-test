from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main
from app.core.database import get_db


@pytest.fixture()
def client() -> Generator[tuple[TestClient, Callable[[], Session]], None, None]:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    original_engine = main.engine
    original_session_local = main.SessionLocal

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    main.engine = test_engine
    main.SessionLocal = testing_session_local
    main.app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(main.app) as test_client:
            yield test_client, testing_session_local
    finally:
        main.app.dependency_overrides.pop(get_db, None)
        main.engine = original_engine
        main.SessionLocal = original_session_local
        test_engine.dispose()
