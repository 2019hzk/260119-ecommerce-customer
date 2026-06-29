"""数字人云渲染相关 HTTP 路由。"""
from fastapi import APIRouter, Query

from atguigu.api.schemas import AvatarSessionResponse
from atguigu.infrastructure import avatar

router = APIRouter()


@router.get("/api/avatar/session")
async def create_avatar_session(
) -> AvatarSessionResponse:
    """创建数字人云渲染会话, 给前端 SDK 初始化。"""
    data = await avatar.create_chat_session()
    return AvatarSessionResponse(**data)


@router.delete("/api/avatar/session")
async def release_avatar_session() -> dict:
    """释放当前数字人会话, 归还并发位。"""
    released = await avatar.stop_chat_session()
    return {"released": released}
