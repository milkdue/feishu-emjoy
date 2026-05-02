import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from meme_router import MemeCommandError, generate_from_text


FEISHU_API = "https://open.feishu.cn/open-apis"


class FeishuConfigError(Exception):
    pass


class FeishuApiError(Exception):
    pass


@dataclass(frozen=True)
class FeishuConfig:
    app_id: str
    app_secret: str
    verification_token: Optional[str] = None


def load_config() -> FeishuConfig:
    app_id = os.getenv("FEISHU_APP_ID", "").strip()
    app_secret = os.getenv("FEISHU_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        raise FeishuConfigError("缺少 FEISHU_APP_ID 或 FEISHU_APP_SECRET")
    return FeishuConfig(
        app_id=app_id,
        app_secret=app_secret,
        verification_token=os.getenv("FEISHU_VERIFICATION_TOKEN", "").strip() or None,
    )


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


def get_tenant_access_token(config: FeishuConfig) -> str:
    body = post_json(
        "/auth/v3/tenant_access_token/internal",
        {"app_id": config.app_id, "app_secret": config.app_secret},
    )
    token = body.get("tenant_access_token")
    if not token:
        raise FeishuApiError(f"tenant_access_token 缺失：{body}")
    return token


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


def send_message(token: str, receive_id: str, msg_type: str, content: Dict[str, Any]) -> None:
    post_json(
        "/im/v1/messages?receive_id_type=chat_id",
        {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": json.dumps(content, ensure_ascii=False),
        },
        token=token,
    )


def send_text(token: str, chat_id: str, text: str) -> None:
    send_message(token, chat_id, "text", {"text": text})


def send_image(token: str, chat_id: str, image_key: str) -> None:
    send_message(token, chat_id, "image", {"image_key": image_key})


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


def handle_feishu_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    if "challenge" in payload:
        return {"challenge": payload["challenge"]}
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge", "")}
    if "encrypt" in payload:
        return {"ok": False, "error": "暂未启用飞书加密事件解析，请关闭 Encrypt Key 或补充解密逻辑"}

    config = load_config()
    verify_token(payload, config)

    header = payload.get("header", {})
    if header.get("event_type") != "im.message.receive_v1":
        return {"ok": True, "ignored": "unsupported event"}

    event = payload.get("event", {})
    sender_type = event.get("sender", {}).get("sender_type")
    if sender_type == "app":
        return {"ok": True, "ignored": "bot message"}

    chat_id, text = extract_text_message(event)
    if not chat_id or not text:
        return {"ok": True, "ignored": "non-text message"}

    token = get_tenant_access_token(config)
    try:
        meme = generate_from_text(text)
        filename = f"{meme.command}.{meme.extension}"
        image_key = upload_image(token, meme.buffer.getvalue(), filename)
        send_image(token, chat_id, image_key)
    except MemeCommandError as exc:
        send_text(token, chat_id, str(exc))

    return {"ok": True}

