from fastapi import APIRouter

from . import conversations, speakers

router = APIRouter(prefix="/api", tags=["API"])

router.include_router(conversations.router)
router.include_router(speakers.router)
