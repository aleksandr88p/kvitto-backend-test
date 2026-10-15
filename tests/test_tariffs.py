from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_get_tariffs_returns_seeded_tariffs(
    client: tuple[TestClient, Callable[[], Session]],
) -> None:
    test_client, _ = client

    response = test_client.get("/tariffs")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "title": "basic", "price": 990000},
        {"id": 2, "title": "standard", "price": 1990000},
        {"id": 3, "title": "premium", "price": 2990000},
    ]
