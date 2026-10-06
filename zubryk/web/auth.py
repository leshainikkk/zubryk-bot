import hashlib
import hmac
import json
import time
from functools import wraps
from urllib.parse import parse_qsl

from flask import g, jsonify, request

from zubryk.config import BOT_TOKEN, INIT_DATA_MAX_AGE


def validate_init_data(raw, token=BOT_TOKEN, max_age=INIT_DATA_MAX_AGE, now=None):
    if not raw or len(raw) > 16384 or not token:
        raise ValueError("Откройте приложение из Telegram")
    pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
    if len(pairs) != len(dict(pairs)):
        raise ValueError("Некорректные данные Telegram")
    fields = dict(pairs)
    supplied_hash = fields.pop("hash", "")
    check = "\n".join(f"{key}={value}" for key,value in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, supplied_hash):
        raise ValueError("Подпись Telegram не прошла проверку")
    timestamp = int(fields.get("auth_date", "0"))
    now = time.time() if now is None else now
    if now-timestamp > max_age or timestamp > now+30:
        raise ValueError("Сессия истекла. Откройте приложение заново")
    user = json.loads(fields.get("user", "null"))
    if not isinstance(user, dict) or type(user.get("id")) is not int or not 0 < user["id"] < 2**52:
        raise ValueError("Некорректный пользователь Telegram")
    return user


def require_telegram(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        try:
            if not header.startswith("tma "):
                raise ValueError("Откройте приложение из Telegram")
            g.telegram_user = validate_init_data(header[4:])
            g.user_id = g.telegram_user["id"]
        except (ValueError, TypeError, json.JSONDecodeError):
            return jsonify(error="unauthorized", message="Откройте приложение заново через кнопку в боте"), 401
        return handler(*args, **kwargs)
    return wrapped
