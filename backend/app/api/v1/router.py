"""聚合所有 v1 路由。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, events, learning, me, news, programs, tasks, tts

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(tts.router)
api_router.include_router(learning.router)
api_router.include_router(tasks.router)
api_router.include_router(programs.router)
api_router.include_router(events.router)
api_router.include_router(news.router)
