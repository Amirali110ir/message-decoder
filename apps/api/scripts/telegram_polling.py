from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import init_db
from app.routers.telegram import _handle_callback, _handle_message


async def get_updates(client: httpx.AsyncClient, token: str, offset: int | None) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {"timeout": 30, "allowed_updates": ["message", "callback_query"]}
    if offset is not None:
        payload["offset"] = offset
    response = await client.post(f"https://api.telegram.org/bot{token}/getUpdates", json=payload)
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram getUpdates failed: {body}")
    return list(body.get("result") or [])


async def run() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN before running polling.")

    init_db()
    offset: int | None = None
    print("Telegram polling started. Press Ctrl+C to stop.")
    async with httpx.AsyncClient(timeout=40) as client:
        while True:
            try:
                updates = await get_updates(client, token, offset)
                for update in updates:
                    offset = int(update["update_id"]) + 1
                    if "message" in update:
                        await _handle_message(update["message"])
                    elif "callback_query" in update:
                        await _handle_callback(update["callback_query"])
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"Polling error: {exc}", file=sys.stderr)
                await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nTelegram polling stopped.")
