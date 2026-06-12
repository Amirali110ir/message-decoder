import pytest

from app.database import db


@pytest.fixture(autouse=True)
def clear_auth_otps_before_each_test():
    """Clear OTP state before every test to prevent cooldown bleed-through."""
    with db() as conn:
        conn.execute("DELETE FROM auth_otps")
        conn.execute("DELETE FROM sms_send_logs")
    yield
