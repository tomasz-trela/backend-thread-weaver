from fastapi import APIRouter, HTTPException
from sqlmodel import select

from src.data.entities import Utterance
from src.models.dto import UtteranceUpdateRequest
from src.typedefs import SessionDep


router = APIRouter(prefix="/utterances", tags=["Utterances"])


@router.get("/{id}")
async def get_utterances_by_id(
    session: SessionDep,
):
    utterances = session.exec(select(Utterance).where(Utterance.id == id)).all()

    if not utterances:
        raise HTTPException(
            status_code=404, detail="No utterances found for this conversation"
        )

    return utterances


@router.put("/{id}")
async def update_utterances(
    session: SessionDep,
    utterance_data: UtteranceUpdateRequest,
):
    utterances = session.exec(select(Utterance).where(Utterance.id == id)).all()

    if not utterances:
        raise HTTPException(
            status_code=404, detail="No utterances found for this conversation"
        )

    for utterance in utterances:
        for key, value in utterance_data.model_dump().items():
            if value is not None:
                setattr(utterance, key, value)

    session.commit()

    return {"message": "Utterances updated successfully"}


@router.put("/{id}/speaker/{speaker_id}")
async def update_speaker_in_utterances(
    conversation_id: int,
    session: SessionDep,
    speaker_id: int,
):
    utterances = session.exec(
        select(Utterance).where(Utterance.conversation_id == conversation_id)
    ).all()

    if not utterances:
        raise HTTPException(
            status_code=404, detail="No utterances found for this conversation"
        )

    for utterance in utterances:
        utterance.speaker_id = speaker_id

    session.commit()

    return {"message": "Speaker updated in all utterances"}
