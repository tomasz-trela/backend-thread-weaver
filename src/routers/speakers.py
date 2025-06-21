from fastapi import APIRouter

from db import Speaker
from typedefs import SessionDep


router = APIRouter(prefix="/speakers", tags=["speakers"])


@router.get("/")
async def get_speakers(session: SessionDep) -> list[Speaker]:
    speakers = session.query(Speaker).all()
    return speakers


@router.post("/")
async def create_speaker(name: str, surname: str, session: SessionDep) -> Speaker:
    speaker = Speaker(name=name.strip(), surname=surname.strip())
    session.add(speaker)
    session.commit()
    return speaker
