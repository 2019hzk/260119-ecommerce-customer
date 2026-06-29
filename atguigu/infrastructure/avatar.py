"""阿里云万相数字人(灵眸)会话客户端: 封装 CreateChatSession。

供前端 `lm-avatar-chat-sdk` 初始化云渲染数字人使用。
SDK 调用是阻塞的, 通过 `asyncio.to_thread` 包装成异步接口供 FastAPI 使用。

"""
from __future__ import annotations

import logging
import asyncio
import threading
from typing import Any

from alibabacloud_lingmou20250527.client import Client as LingMouClient
from alibabacloud_lingmou20250527 import models as lm_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

from atguigu.config.settings import settings

logger = logging.getLogger(__name__)

_client: LingMouClient | None = None

# 当前进程复用同一个数字人会话。业务用户身份由聊天接口的 sender_id 区分。
_session: dict[str, Any] | None = None
_session_lock = threading.Lock()


def init_avatar_client() -> None:
    """在 FastAPI lifespan 中调用, 提前完成客户端初始化。"""
    global _client
    if _client is not None:
        return
    _client = _build_client()
    logger.info("Avatar client 初始化. endpoint=%s", settings.avatar_endpoint)


def _build_client() -> LingMouClient:
    config = open_api_models.Config(
        access_key_id=settings.avatar_access_key_id,
        access_key_secret=settings.avatar_access_key_secret,
    )
    config.endpoint = settings.avatar_endpoint
    return LingMouClient(config)


def _get_client() -> LingMouClient:
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def _rtc_params_to_dict(rtc) -> dict[str, Any]:
    if rtc is None:
        return {}
    return {
        "appId": rtc.app_id,
        "channel": rtc.channel,
        "nonce": rtc.nonce,
        "timestamp": rtc.timestamp,
        "token": rtc.token,
        "gslb": rtc.gslb,
        "clientUserId": rtc.client_user_id,
        "serverUserId": rtc.server_user_id,
        "avatarUserId": rtc.avatar_user_id,
    }


def _do_create() -> dict[str, Any]:
    """对应官方 demo:
    client.create_chat_session_with_options(project_id, request, headers, runtime)
    project_id 是控制台项目主键(如 'C1rRS1KmS3WurHor8HXYlSkQ');
    request 里通常只填 instance_id, 其余 device_id 由调用方按需补。
    """
    client = _get_client()
    project_id = settings.avatar_project_id

    req = lm_models.CreateChatSessionRequest(instance_id= settings.avatar_instance_id)

    resp = client.create_chat_session_with_options(
        project_id, req, {}, util_models.RuntimeOptions()
    )
    data = getattr(resp.body, "data", None)
    if data is None:
       return {}
    return {
        "sessionId": data.session_id,
        "rtcParams": _rtc_params_to_dict(data.rtc_params),
    }


def _create_chat_session_sync() -> dict[str, Any]:
    global _session
    with _session_lock:
        if _session is not None:
            return _session
        _session = _do_create()
        return _session


async def create_chat_session() -> dict[str, Any]:
    return await asyncio.to_thread(_create_chat_session_sync)


def _close_session_ids(session_ids: list[str]) -> int:
    """调用灵眸 CloseChatInstanceSessions 关闭一批会话, 返回成功提交的数量。"""
    if not session_ids:
        return 0
    instance_id = settings.avatar_instance_id

    client = _get_client()

    req = lm_models.CloseChatInstanceSessionsRequest(session_ids=session_ids)
    client.close_chat_instance_sessions_with_options(
        instance_id, req, {}, util_models.RuntimeOptions()
    )
    return len(session_ids)


def _stop_chat_session_sync() -> bool:
    """释放当前进程缓存的数字人会话。返回是否找到并关闭。"""
    global _session
    with _session_lock:
        session = _session
        _session = None
    session_id = session and session.get("sessionId")
    if not session_id:
        return False
    try:
        _close_session_ids([session_id])
        return True
    except Exception:
        with _session_lock:
            if _session is None:
                _session = session
        raise


async def stop_chat_session() -> bool:
    return await asyncio.to_thread(_stop_chat_session_sync)
