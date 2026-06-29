
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from atguigu.domain.messages import (
    BotMessage,
    FocusedObject,
    MessageType,
    UserMessage,
)
from atguigu.infrastructure import db
from atguigu.repository.dialogue_repository import DialogueRepository
from atguigu.services.dialogue_service import DialogueService
from atguigu.api.dependencies import get_engine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/avatar/chat")
async def avatar_chat_ws(ws: WebSocket) -> None:
    await ws.accept()
    current_turn: asyncio.Task | None = None

    async def cancel_current(reason: str) -> None:
        nonlocal current_turn
        if current_turn is None or current_turn.done():
            current_turn = None
            return
        current_turn.cancel()
        try:
            await current_turn
        except (asyncio.CancelledError, Exception):
            pass
        finally:
            current_turn = None
        logger.info("WS turn 被取消: %s", reason)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await _safe_send_json(ws, {"type": "error", "message": "invalid json"})
                continue

            msg_type = payload.get("type")
            if msg_type == "user_text":
                # 新消息到达, 强制打断上一轮(若仍在播报)
                await cancel_current("新 user_text 到达")
                await _safe_send_json(ws, {"type": "interrupt"})
                current_turn = asyncio.create_task(_run_turn(ws, payload))
            else:
                await _safe_send_json(
                    ws, {"type": "error", "message": f"unknown type: {msg_type}"}
                )
    except WebSocketDisconnect:
        logger.info("WS client 断开")
    except Exception:
        logger.exception("WS handler 出错")
    finally:
        await cancel_current("ws 关闭")


async def _run_turn(ws: WebSocket, payload: dict[str, Any]) -> None:
    """处理一次用户输入: 调对话引擎拿回复, 再把回复文本推给前端。"""
    sender_id = payload.get("sender_id")
    if not sender_id:
        await _safe_send_json(ws, {"type": "error", "message": "missing sender_id"})
        return

    text = payload.get("text")
    if not text.strip():
        await _safe_send_json(ws, {"type": "error", "message": "empty text"})
        return

    message_id = payload.get("message_id") or str(uuid.uuid4())
    user_message = UserMessage(
        sender_id=sender_id,
        message_id=message_id,
        type=MessageType.TEXT,
        text=text,
    )

    await _safe_send_json(ws, {"type": "user_ack", "message_id": message_id})

    # 复用现有对话引擎: 自带 DB session 生命周期
    try:
        engine =  get_engine()

        async with db.session_factory() as session:
            repository = DialogueRepository(session=session)
            service = DialogueService(
                repository=repository,
                engine=engine,
            )
            result = await service.hand_dialogue(user_message)
        messages: list[BotMessage] = result.messages
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("dialogue handle_message 失败")
        await _safe_send_json(
            ws, {"type": "error", "message": f"dialogue failed: {e}"}
        )
        return

    for index, bot_msg in enumerate(messages):
        await _safe_send_json(
            ws,
            {
                "type": "bot_text",
                "message_id": message_id,
                "index": index,
                "text": bot_msg.text,
                "object": _focused_object_to_dict(bot_msg.object),
            },
        )

    await _safe_send_json(ws, {"type": "turn_end", "message_id": message_id})


def _focused_object_to_dict(obj: FocusedObject | None) -> dict | None:
    if obj is None:
        return None
    return obj.to_dict()


async def _safe_send_json(ws: WebSocket, data: dict) -> None:
    try:
        await ws.send_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        logger.debug("WS 发送数据失败", exc_info=True)
