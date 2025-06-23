from fastapi import APIRouter, HTTPException
from sqlmodel import select

from ..models.dto import SpeakerCreateRequest, SpeakerUpdateRequest

from ..data.db import Speaker
from ..typedefs import SessionDep


router = APIRouter(prefix="/speakers", tags=["Speakers"])


@router.get("/")
async def get_speakers(session: SessionDep) -> list[Speaker]:
    stmt = select(Speaker)
    speakers = session.exec(stmt).all()
    return speakers


@router.post("/")
async def create_speaker(data: SpeakerCreateRequest, session: SessionDep) -> Speaker:
    speaker = Speaker(name=data.name.strip(), surname=data.surname.strip())
    session.add(speaker)
    session.commit()
    return speaker


@router.put("/{speaker_id}")
async def update_speaker(
    speaker_id: int, speaker_data: SpeakerUpdateRequest, session: SessionDep
) -> Speaker:
    db_speaker = session.get(Speaker, speaker_id)
    for key, value in speaker_data.model_dump().items():
        if value is not None:
            setattr(db_speaker, key, value)

    session.commit()
    session.refresh(db_speaker)
    return db_speaker


@router.delete("/{speaker_id}", status_code=204)
async def delete_speaker(speaker_id: int, session: SessionDep):
    db_speaker = session.get(Speaker, speaker_id)

    if not db_speaker:
        raise HTTPException(status_code=404, detail="Speaker not found")

    session.delete(db_speaker)
    session.commit()

    return None
