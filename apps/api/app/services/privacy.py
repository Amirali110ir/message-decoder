from __future__ import annotations

import sqlite3


def delete_messages_with_decodes(conn: sqlite3.Connection, message_ids: list[str]) -> tuple[int, int]:
    if not message_ids:
        return 0, 0

    message_placeholders = ",".join("?" for _ in message_ids)
    decode_rows = conn.execute(
        f"SELECT id FROM decodes WHERE message_id IN ({message_placeholders})",
        message_ids,
    ).fetchall()
    decode_ids = [str(row["id"]) for row in decode_rows]
    if decode_ids:
        decode_placeholders = ",".join("?" for _ in decode_ids)
        conn.execute(f"DELETE FROM quality_signals WHERE decode_id IN ({decode_placeholders})", decode_ids)
        conn.execute(f"DELETE FROM feedback WHERE decode_id IN ({decode_placeholders})", decode_ids)
        conn.execute(f"DELETE FROM copy_events WHERE decode_id IN ({decode_placeholders})", decode_ids)
        conn.execute(f"DELETE FROM decodes WHERE id IN ({decode_placeholders})", decode_ids)
    conn.execute(f"DELETE FROM messages WHERE id IN ({message_placeholders})", message_ids)
    return len(decode_ids), len(message_ids)
