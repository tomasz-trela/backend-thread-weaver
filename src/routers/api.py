from fastapi import APIRouter

from . import conversations, speakers, utterances

router = APIRouter(prefix="/api", tags=["API"])

router.include_router(conversations.router)
router.include_router(speakers.router)
router.include_router(utterances.router)
