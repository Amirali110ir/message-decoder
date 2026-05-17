from __future__ import annotations

from fastapi import HTTPException

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
    authority = new_id("zarinpal")
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
        "payment_url": f"https://sandbox.zarinpal.com/pg/StartPay/{authority}",
        "amount": package["amount"],
        "credits": package["credits"],
    }


def verify_payment(user_id: str, payment_id: str, status: str) -> tuple[str, int]:
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
            return "verified", int(balance)
        if not success:
            conn.execute("UPDATE payments SET status = 'failed', verified_at = ? WHERE id = ?", (now_iso(), payment_id))
            balance = conn.execute("SELECT credit_balance FROM users WHERE id = ?", (user_id,)).fetchone()["credit_balance"]
            return "failed", int(balance)

        conn.execute(
            "UPDATE payments SET status = 'verified', verified_at = ? WHERE id = ?",
            (now_iso(), payment_id),
        )
        conn.execute(
            "UPDATE users SET credit_balance = credit_balance + ? WHERE id = ?",
            (int(payment["credits_added"]), user_id),
        )
        balance = conn.execute("SELECT credit_balance FROM users WHERE id = ?", (user_id,)).fetchone()["credit_balance"]
        return "verified", int(balance)

