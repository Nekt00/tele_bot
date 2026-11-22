import base64
import hashlib
import hmac


def _signature(user_id: int, group_chat_id: int, secret: str) -> str:
    message = f"{user_id}:{group_chat_id}".encode("ascii")
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()[:12]
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def create_quiz_payload(user_id: int, group_chat_id: int, secret: str) -> str:
    return f"q_{user_id}_{group_chat_id}_{_signature(user_id, group_chat_id, secret)}"


def parse_quiz_payload(payload: str, secret: str) -> tuple[int, int] | None:
    parts = payload.split("_", 3)
    if len(parts) != 4 or parts[0] != "q":
        return None

    try:
        user_id = int(parts[1])
        group_chat_id = int(parts[2])
    except ValueError:
        return None

    expected = _signature(user_id, group_chat_id, secret)
    if not hmac.compare_digest(parts[3], expected):
        return None
    return user_id, group_chat_id
