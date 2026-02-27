from fastapi import APIRouter

from .routers import context_router, metadata_router, sessions_router, stream_router, optimizer_router

router = APIRouter()
router.include_router(sessions_router)
router.include_router(metadata_router)
router.include_router(context_router)
router.include_router(stream_router)
router.include_router(optimizer_router)
