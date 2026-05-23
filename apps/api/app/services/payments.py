from __future__ import annotations

import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

from app.config import get_settings
from app.database import db
from app.utils import new_id, now_iso


PACKAGES = {
    "credits_5": {"credits": 5, "amount": 49000},
    "credits_20": {"credits": 20, "amount": 169000},
    "credits_50": {"credits": 50, "amount": 349000},
}


def create_payment(user_id: str, package_id: str) -> dict:
    package = PACKAGES.get(package_id)
    if not package:
        raise HTTPException(status_code=400, detail="Unknown package")
    payment_id = new_id("pay")
    if _use_sandbox():
        authority = new_id("zarinpal")
        payment_url = f"https://sandbox.zarinpal.com/pg/StartPay/{authority}"
    else:
        authority, payment_url = _zarinpal_request_payment(package_id, int(package["amount"]), payment_id)
    with db() as conn:
        conn.execute(
            """
            INSERT INTO payments (id, user_id, package_id, amount, credits_added, status, provider, authority, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', 'zarinpal', ?, ?)
            """,
            (payment_id, user_id, package_id, package["amount"], package["credits"], authority, now_iso()),
        )
    return {
        "payment_id": payment_id,
        "payment_url": payment_url,
        "amount": package["amount"],
        "credits": package["credits"],
        "authority": authority,
    }


def verify_payment(user_id: str, payment_id: str, status: str, authority: str | None = None) -> tuple[str, int, str | None]:
    normalized = status.lower()
    success = normalized in ("ok", "success", "sandbox_success")
    with db() as conn:
        payment = conn.execute(
            "SELECT * FROM payments WHERE id = ? AND user_id = ?",
            (payment_id, user_id),
        ).fetchone()
        if payment is None:
            raise HTTPException(status_code=404, detail="Payment not found")
        if payment["status"] == "verified":
            balance = conn.execute("SELECT credit_balance FROM users WHERE id = ?", (user_id,)).fetchone()["credit_balance"]
            return "verified", int(balance), payment["ref_id"] if "ref_id" in payment.keys() else None
        if not success:
            conn.execute("UPDATE payments SET status = 'failed', verified_at = ? WHERE id = ?", (now_iso(), payment_id))
            balance = conn.execute("SELECT credit_balance FROM users WHERE id = ?", (user_id,)).fetchone()["credit_balance"]
            return "failed", int(balance), None

        ref_id = "sandbox"
        if not _use_sandbox() and normalized != "sandbox_success":
            stored_authority = str(payment["authority"])
            if authority and authority != stored_authority:
                raise HTTPException(status_code=400, detail="Payment authority does not match")
            ref_id = _zarinpal_verify_payment(stored_authority, int(payment["amount"]))

        conn.execute(
            "UPDATE payments SET status = 'verified', ref_id = ?, verified_at = ? WHERE id = ?",
            (ref_id, now_iso(), payment_id),
        )
        conn.execute(
            "UPDATE users SET credit_balance = credit_balance + ? WHERE id = ?",
            (int(payment["credits_added"]), user_id),
        )
        balance = conn.execute("SELECT credit_balance FROM users WHERE id = ?", (user_id,)).fetchone()["credit_balance"]
        return "verified", int(balance), ref_id


def _use_sandbox() -> bool:
    settings = get_settings()
    return settings.zarinpal_merchant_id.strip().lower() in ("", "sandbox")


def _zarinpal_request_payment(package_id: str, amount: int, payment_id: str) -> tuple[str, str]:
    settings = get_settings()
    response = _post_zarinpal(
        "/pg/v4/payment/request.json",
        {
            "merchant_id": settings.zarinpal_merchant_id,
            "amount": amount,
            "callback_url": _callback_url(payment_id),
            "description": f"Message Decoder credit package: {package_id}",
        },
    )
    data = response.get("data") or {}
    code = int(data.get("code") or 0)
    authority = data.get("authority")
    if code != 100 or not authority:
        raise HTTPException(status_code=502, detail=_zarinpal_error(response, "Zarinpal payment request failed"))
    return str(authority), f"{settings.zarinpal_start_pay_url.rstrip('/')}/{authority}"


def _zarinpal_verify_payment(authority: str, amount: int) -> str:
    settings = get_settings()
    response = _post_zarinpal(
        "/pg/v4/payment/verify.json",
        {
            "merchant_id": settings.zarinpal_merchant_id,
            "amount": amount,
            "authority": authority,
        },
    )
    data = response.get("data") or {}
    code = int(data.get("code") or 0)
    ref_id = data.get("ref_id")
    if code not in (100, 101) or not ref_id:
        raise HTTPException(status_code=402, detail=_zarinpal_error(response, "Zarinpal payment verification failed"))
    return str(ref_id)


def _post_zarinpal(path: str, payload: dict) -> dict:
    settings = get_settings()
    url = f"{settings.zarinpal_api_base_url.rstrip('/')}{path}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
    except HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"Zarinpal HTTP error {err.code}: {body[:200]}") from err
    except URLError as err:
        raise HTTPException(status_code=502, detail=f"Zarinpal connection failed: {err.reason}") from err
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as err:
        raise HTTPException(status_code=502, detail="Zarinpal returned an invalid JSON response") from err
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=502, detail="Zarinpal returned an invalid response shape")
    return parsed


def _callback_url(payment_id: str) -> str:
    settings = get_settings()
    parts = urlsplit(settings.zarinpal_callback_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["payment_id"] = payment_id
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _zarinpal_error(response: dict, fallback: str) -> str:
    errors = response.get("errors")
    if isinstance(errors, dict):
        message = errors.get("message")
        if message:
            return str(message)
    return fallback
