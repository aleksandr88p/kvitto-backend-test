from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Payment, PaymentStatus


def create_card_payment(test_client: TestClient) -> int:
    response = test_client.post(
        "/payments",
        json={
            "tariff_id": 1,
            "email": "webhook@example.com",
            "method": "card",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def send_webhook(
    test_client: TestClient,
    payment_id: int,
    status: PaymentStatus,
):
    return test_client.post(
        "/webhooks/bank",
        json={"payment_id": payment_id, "status": status.value},
    )


def stored_payment_status(
    session_factory: Callable[[], Session],
    payment_id: int,
) -> PaymentStatus:
    with session_factory() as session:
        payment = session.get(Payment, payment_id)
    assert payment is not None
    return payment.status


def test_allowed_webhook_transitions(
    client: tuple[TestClient, Callable[[], Session]],
) -> None:
    test_client, session_factory = client

    succeeded_payment_id = create_card_payment(test_client)
    response = send_webhook(
        test_client,
        succeeded_payment_id,
        PaymentStatus.SUCCEEDED,
    )
    assert response.status_code == 200
    assert response.json() == {"result": "ok"}
    assert stored_payment_status(session_factory, succeeded_payment_id) == PaymentStatus.SUCCEEDED

    failed_payment_id = create_card_payment(test_client)
    response = send_webhook(
        test_client,
        failed_payment_id,
        PaymentStatus.FAILED,
    )
    assert response.status_code == 200
    assert response.json() == {"result": "ok"}
    assert stored_payment_status(session_factory, failed_payment_id) == PaymentStatus.FAILED

    refunded_payment_id = create_card_payment(test_client)
    succeeded_response = send_webhook(
        test_client,
        refunded_payment_id,
        PaymentStatus.SUCCEEDED,
    )
    refunded_response = send_webhook(
        test_client,
        refunded_payment_id,
        PaymentStatus.REFUNDED,
    )
    assert succeeded_response.status_code == 200
    assert refunded_response.status_code == 200
    assert refunded_response.json() == {"result": "ok"}
    assert stored_payment_status(session_factory, refunded_payment_id) == PaymentStatus.REFUNDED


def test_forbidden_webhook_transition_does_not_change_status(
    client: tuple[TestClient, Callable[[], Session]],
) -> None:
    test_client, session_factory = client
    payment_id = create_card_payment(test_client)
    response = send_webhook(test_client, payment_id, PaymentStatus.SUCCEEDED)
    assert response.status_code == 200

    invalid_response = send_webhook(test_client, payment_id, PaymentStatus.FAILED)

    assert invalid_response.status_code == 409
    assert invalid_response.json() == {"error": "invalid_transition"}
    assert stored_payment_status(session_factory, payment_id) == PaymentStatus.SUCCEEDED


def test_repeated_webhook_transition_is_forbidden(
    client: tuple[TestClient, Callable[[], Session]],
) -> None:
    test_client, session_factory = client
    payment_id = create_card_payment(test_client)
    response = send_webhook(test_client, payment_id, PaymentStatus.SUCCEEDED)
    assert response.status_code == 200

    repeated_response = send_webhook(test_client, payment_id, PaymentStatus.SUCCEEDED)

    assert repeated_response.status_code == 409
    assert repeated_response.json() == {"error": "invalid_transition"}
    assert stored_payment_status(session_factory, payment_id) == PaymentStatus.SUCCEEDED


def test_missing_webhook_payment_returns_404(
    client: tuple[TestClient, Callable[[], Session]],
) -> None:
    test_client, _ = client

    response = send_webhook(test_client, 999, PaymentStatus.SUCCEEDED)

    assert response.status_code == 404
    assert response.json() == {"detail": "Payment not found"}
