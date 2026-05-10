import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from meme_router import MemeCommandError, generate_from_text


FEISHU_API = "https://open.feishu.cn/open-apis"
PROCESSED_EVENTS: Dict[str, float] = {}
DEDUP_TTL_SECONDS = 3600
BOT_OPEN_ID: Optional[str] = None
CONFIG_LOGGED = False


class FeishuConfigError(Exception):
    pass


class FeishuApiError(Exception):
    pass


@dataclass(frozen=True)
class FeishuConfig:
    app_id: str
    app_secret: str
    verification_token: Optional[str] = None
    bot_open_id: Optional[str] = None


def load_config() -> FeishuConfig:
    app_id = os.getenv("FEISHU_APP_ID", "").strip()
    app_secret = os.getenv("FEISHU_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        raise FeishuConfigError("缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET")
    return FeishuConfig(
        app_id=app_id,
        app_secret=app_secret,
        verification_token=os.getenv("FEISHU_VERIFICATION_TOKEN", "").strip() or None,
        bot_open_id=os.getenv("FEISHU_BOT_OPEN_ID", "").strip() or None,
    )


def mask_id(value: Optional[str]) -> str:
    if not value:
        return "unset"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def log_config_once(config: FeishuConfig) -> None:
    global CONFIG_LOGGED
    if CONFIG_LOGGED:
        return
    print(f"FEISHU_BOT_OPEN_ID={mask_id(config.bot_open_id)}")
    CONFIG_LOGGED = True


def verify_token(payload: Dict[str, Any], config: FeishuConfig) -> None:
    if not config.verification_token:
        return
    token = payload.get("token") or payload.get("header", {}).get("token")
    if token and token != config.verification_token:
        raise FeishuApiError("飞书事件 token 校验失败")


def post_json(path: str, data: Dict[str, Any], token: Optional[str] = None) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = httpx.post(f"{FEISHU_API}{path}", headers=headers, json=data, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    if body.get("code", 0) != 0:
        raise FeishuApiError(f"飞书接口错误：{body}")
    return body


def get_json(path: str, token: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    resp = httpx.get(f"{FEISHU_API}{path}", headers=headers, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    if body.get("code", 0) != 0:
        raise FeishuApiError(f"飞书接口错误：{body}")
    return body


def get_tenant_access_token(config: FeishuConfig) -> str:
    body = post_json(
        "/auth/v3/tenant_access_token/internal",
        {"app_id": config.app_id, "app_secret": config.app_secret},
    )
    token = body.get("tenant_access_token")
    if not token:
        raise FeishuApiError(f"tenant_access_token 缺失：{body}")
    return token


def get_bot_open_id(token: str) -> str:
    global BOT_OPEN_ID
    if BOT_OPEN_ID:
        return BOT_OPEN_ID

    body = get_json("/bot/v3/info", token)
    data = body.get("data", {})
    open_id = data.get("open_id") or data.get("bot", {}).get("open_id")
    if not open_id:
        raise FeishuApiError(f"bot open_id 缺失：{body}")
    BOT_OPEN_ID = open_id
    return open_id


def upload_image(token: str, image_bytes: bytes, filename: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    files = {"image": (filename, image_bytes)}
    data = {"image_type": "message"}
    resp = httpx.post(
        f"{FEISHU_API}/im/v1/images",
        headers=headers,
        data=data,
        files=files,
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("code", 0) != 0:
        raise FeishuApiError(f"飞书图片上传失败：{body}")
    image_key = body.get("data", {}).get("image_key")
    if not image_key:
        raise FeishuApiError(f"image_key 缺失：{body}")
    return image_key


def cleanup_processed_events(now: float) -> None:
    expired = [
        key for key, created_at in PROCESSED_EVENTS.items()
        if now - created_at > DEDUP_TTL_SECONDS
    ]
    for key in expired:
        PROCESSED_EVENTS.pop(key, None)


def event_dedup_key(payload: Dict[str, Any]) -> Optional[str]:
    header = payload.get("header", {})
    event = payload.get("event", {})
    message = event.get("message", {})
    return (
        header.get("event_id")
        or event.get("event_id")
        or message.get("message_id")
        or None
    )


def already_processed(payload: Dict[str, Any]) -> bool:
    key = event_dedup_key(payload)
    if not key:
        return False
    now = time.time()
    cleanup_processed_events(now)
    if key in PROCESSED_EVENTS:
        return True
    PROCESSED_EVENTS[key] = now
    return False


def send_message(
    token: str,
    receive_id: str,
    msg_type: str,
    content: Dict[str, Any],
    uuid: Optional[str] = None,
) -> None:
    body = {
        "receive_id": receive_id,
        "msg_type": msg_type,
        "content": json.dumps(content, ensure_ascii=False),
    }
    if uuid:
        body["uuid"] = uuid[:64]
    post_json(
        "/im/v1/messages?receive_id_type=chat_id",
        body,
        token=token,
    )


def send_text(token: str, chat_id: str, text: str, uuid: Optional[str] = None) -> None:
    send_message(token, chat_id, "text", {"text": text}, uuid=uuid)


def send_image(token: str, chat_id: str, image_key: str, uuid: Optional[str] = None) -> None:
    send_message(token, chat_id, "image", {"image_key": image_key}, uuid=uuid)


def extract_text_message(event: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    message = event.get("message", {})
    chat_id = message.get("chat_id")
    if message.get("message_type") != "text":
        return chat_id, None

    raw_content = message.get("content") or "{}"
    try:
        content = json.loads(raw_content)
    except json.JSONDecodeError:
        content = {}
    text = (content.get("text") or "").strip()
    return chat_id, text


def has_bot_mention(text: str) -> bool:
    text = text.lstrip()
    return text.startswith("<at") or text.startswith("@")


def leading_mention_key(text: str) -> Optional[str]:
    text = text.lstrip()
    if text.startswith("<at"):
        match = re.match(r"(<at[^>]*>.*?</at>)", text)
        return match.group(1) if match else None
    if text.startswith("@"):
        return text.split(maxsplit=1)[0]
    return None


def message_mentions_open_id(message: Dict[str, Any], open_id: str) -> bool:
    for mention in message.get("mentions") or []:
        mention_id = mention.get("id") or {}
        if mention_id.get("open_id") == open_id:
            return True
    return False


def message_has_leading_mention(message: Dict[str, Any], text: str) -> bool:
    key = leading_mention_key(text)
    if not key:
        return False
    mentions = message.get("mentions") or []
    if not mentions:
        return True
    return any(mention.get("key") == key for mention in mentions)


def is_private_chat(message: Dict[str, Any]) -> bool:
    return message.get("chat_type") == "p2p"


def handle_feishu_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    if "challenge" in payload:
        return {"challenge": payload["challenge"]}
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge", "")}
    if "encrypt" in payload:
        return {"ok": False, "error": "暂未启用飞书加密事件解析，请关闭 Encrypt Key 或补充解密逻辑"}

    config = load_config()
    log_config_once(config)
    verify_token(payload, config)

    header = payload.get("header", {})
    if header.get("event_type") != "im.message.receive_v1":
        return {"ok": True, "ignored": "unsupported event"}

    dedup_key = event_dedup_key(payload)
    if already_processed(payload):
        return {"ok": True, "ignored": "duplicate event", "dedup_key": dedup_key}

    event = payload.get("event", {})
    message = event.get("message", {})
    sender_type = event.get("sender", {}).get("sender_type")
    if sender_type == "app":
        return {"ok": True, "ignored": "bot message"}

    chat_id, text = extract_text_message(event)
    if not chat_id or not text:
        return {"ok": True, "ignored": "non-text message"}
    if not is_private_chat(message):
        if not has_bot_mention(text):
            return {"ok": True, "ignored": "not mentioned"}
        if config.bot_open_id and not message_mentions_open_id(message, config.bot_open_id):
            return {"ok": True, "ignored": "not mentioned"}
        if not config.bot_open_id and not message_has_leading_mention(message, text):
            return {"ok": True, "ignored": "not mentioned"}

    token = get_tenant_access_token(config)
    try:
        meme = generate_from_text(text)
        filename = f"{meme.command}.{meme.extension}"
        image_key = upload_image(token, meme.buffer.getvalue(), filename)
        send_image(token, chat_id, image_key, uuid=dedup_key)
    except MemeCommandError as exc:
        send_text(token, chat_id, str(exc), uuid=dedup_key)

    return {"ok": True}
