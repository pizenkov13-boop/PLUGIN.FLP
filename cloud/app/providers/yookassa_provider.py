"""ЮKassa checkout + webhook (CIS — 899 ₽/mo MVP)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import HTTPException
from supabase import Client

from cloud.app.billing import activate_subscription, claim_idempotency, enter_grace_period, expire_subscription
from cloud.app.config import BILLING_RETURN_URL, PRICE_CIS_RUB, YOOKASSA_SECRET_KEY, YOOKASSA_SHOP_ID

logger = logging.getLogger("plg.billing.yookassa")


def _configured() -> bool:
    return bool(YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY)


def create_checkout(user_id: str, price_tier: str = "cis") -> dict[str, Any]:
    if not _configured():
        raise HTTPException(503, "ЮKassa credentials missing (YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY).")
    if price_tier != "cis":
        raise HTTPException(400, "ЮKassa supports CIS tier only. Use Stripe/Paddle for international.")

    try:
        from yookassa import Configuration, Payment
    except ImportError as exc:
        raise HTTPException(503, "yookassa package not installed.") from exc

    Configuration.configure(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
    idempotence_key = str(uuid.uuid4())
    amount = f"{PRICE_CIS_RUB:.2f}"

    payment = Payment.create(
        {
            "amount": {"value": amount, "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": BILLING_RETURN_URL},
            "capture": True,
            "description": "PLUGIN.FLP — 1 month",
            "metadata": {"user_id": user_id, "price_tier": price_tier},
        },
        idempotence_key,
    )

    confirmation = payment.confirmation
    url = getattr(confirmation, "confirmation_url", None) if confirmation else None
    if not url:
        raise HTTPException(502, "ЮKassa did not return a payment URL.")

    return {
        "provider": "yookassa",
        "payment_id": payment.id,
        "confirmation_url": url,
        "amount_rub": PRICE_CIS_RUB,
        "price_tier": price_tier,
    }


def _fetch_payment(payment_id: str) -> Any:
    from yookassa import Configuration, Payment

    Configuration.configure(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
    return Payment.find_one(payment_id)


def handle_webhook(client: Client, body: dict[str, Any]) -> dict[str, str]:
    if not _configured():
        raise HTTPException(503, "ЮKassa not configured.")

    event = str(body.get("event") or "")
    obj = body.get("object") or {}
    payment_id = str(obj.get("id") or "")
    if not payment_id:
        raise HTTPException(400, "Missing payment id in webhook.")

    payment = _fetch_payment(payment_id)
    status = str(getattr(payment, "status", "") or "")
    metadata = getattr(payment, "metadata", None) or {}
    user_id = str(metadata.get("user_id") or "")
    price_tier = str(metadata.get("price_tier") or "cis")

    idem_key = f"{event}:{payment_id}"
    if claim_idempotency(
        client,
        provider="yookassa",
        idempotency_key=idem_key,
        event_type=event,
        user_id=user_id or None,
        external_id=payment_id,
        payload=body,
    ):
        return {"ok": "duplicate"}

    if event == "payment.succeeded" and status == "succeeded":
        if not user_id:
            logger.error("yookassa payment %s missing user_id metadata", payment_id)
            raise HTTPException(400, "Payment missing user_id metadata.")
        activate_subscription(
            client,
            user_id,
            provider="yookassa",
            external_id=payment_id,
            price_tier=price_tier,
        )
        try:
            from cloud.app.analytics_ops import track_event
            from cloud.app.email import notify_payment_success
            from cloud.app.legal import _user_email

            track_event(client, "payment_completed", user_id=user_id)
            email = _user_email(client, user_id)
            if email:
                notify_payment_success(client, user_id, email)
        except Exception:  # noqa: BLE001
            logger.exception("post-payment notify failed")
        return {"ok": "activated"}

    if event in ("payment.canceled", "payment.waiting_for_capture") and status == "canceled":
        if user_id:
            profile = client.table("profiles").select("status").eq("id", user_id).maybe_single().execute()
            if profile.data and profile.data.get("status") == "active":
                enter_grace_period(client, user_id)
        return {"ok": "grace"}

    if event == "refund.succeeded":
        if user_id:
            expire_subscription(client, user_id)
        return {"ok": "refunded"}

    logger.info("yookassa webhook ignored event=%s status=%s", event, status)
    return {"ok": "ignored"}
