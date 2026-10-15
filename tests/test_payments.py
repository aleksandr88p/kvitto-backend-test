from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Payment


def payment_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "tariff_id": 1,
        "email": "user@example.com",
        "method": "card",
    }
    payload.update(overrides)
    return payload


def test_create_payment_without_promo_code(
    client: tuple[TestClient, Callable[[], Session]],
) -> None:
    test_client, _ = client

    response = test_client.post("/payments", json=payment_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["amount"] == 990000
    assert body["discount"] == 0
    assert body["schedule"] is None


@pytest.mark.parametrize("promo_code", ["KVITTO10", "kvitto10"])
def test_create_payment_with_promo_code(
    client: tuple[TestClient, Callable[[], Session]],
    promo_code: str,
) -> None:
    test_client, _ = client

    response = test_client.post(
        "/payments",
        json=payment_payload(promo_code=promo_code),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["discount"] == 99000
    assert body["amount"] == 891000


@pytest.mark.parametrize("installment_months", [3, 6, 12])
def test_installment_schedule_distribution(
    client: tuple[TestClient, Callable[[], Session]],
    installment_months: int,
) -> None:
    test_client, _ = client
    tariff_price = 1990000

    response = test_client.post(
        "/payments",
        json=payment_payload(
            tariff_id=2,
            method="installment",
            installment_months=installment_months,
        ),
    )

    assert response.status_code == 201
    body = response.json()
    schedule = body["schedule"]
    base_amount, remainder = divmod(tariff_price, installment_months)
    expected_schedule = [base_amount + 1] * remainder + [base_amount] * (
        installment_months - remainder
    )

    assert len(schedule) == installment_months
    assert sum(schedule) == tariff_price
    assert schedule == expected_schedule

    get_response = test_client.get(f"/payments/{body['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["schedule"] == expected_schedule


def test_idempotency_key_returns_original_payment(
    client: tuple[TestClient, Callable[[], Session]],
) -> None:
    test_client, session_factory = client
    idempotency_key = "repeat-key"

    first_response = test_client.post(
        "/payments",
        json=payment_payload(),
        headers={"Idempotency-Key": idempotency_key},
    )
    second_response = test_client.post(
        "/payments",
        json=payment_payload(email="other@example.com"),
        headers={"Idempotency-Key": idempotency_key},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert second_response.json()["id"] == first_response.json()["id"]
    assert second_response.json()["email"] == "user@example.com"

    with session_factory() as session:
        payments_count = session.scalar(
            select(func.count())
            .select_from(Payment)
            .where(Payment.idempotency_key == idempotency_key)
        )
    assert payments_count == 1


def test_unknown_promo_code_returns_422(
    client: tuple[TestClient, Callable[[], Session]],
) -> None:
    test_client, _ = client

    response = test_client.post(
        "/payments",
        json=payment_payload(promo_code="unknown"),
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "promo_code"]
    assert response.json()["detail"][0]["msg"] == "Unknown promo code"


def test_unknown_tariff_returns_404(
    client: tuple[TestClient, Callable[[], Session]],
) -> None:
    test_client, _ = client

    response = test_client.post(
        "/payments",
        json=payment_payload(tariff_id=999),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Tariff not found"}


def test_missing_payment_returns_404(
    client: tuple[TestClient, Callable[[], Session]],
) -> None:
    test_client, _ = client

    response = test_client.get("/payments/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Payment not found"}


@pytest.mark.parametrize(
    "payload",
    [
        {"method": "installment"},
        {"method": "installment", "installment_months": 4},
        {"method": "card", "installment_months": 3},
        {"method": "sbp", "installment_months": 6},
    ],
)
def test_invalid_installment_months_return_422(
    client: tuple[TestClient, Callable[[], Session]],
    payload: dict[str, object],
) -> None:
    test_client, _ = client

    response = test_client.post("/payments", json=payment_payload(**payload))

    assert response.status_code == 422
