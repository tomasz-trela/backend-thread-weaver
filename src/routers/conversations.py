from typing import Any

from fastapi import APIRouter
from sqlmodel import select

from googleapi import get_embeddings
from process_data import get_segments

from db import (
    Conversation,
    Speaker,
    Utterance,
    full_text_search,
    similarity_search,
)
from typedefs import SessionDep

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("")
async def create_conversation(
    title: str,
    session: SessionDep,
    description: str | None = None,
    youtube_id: str | None = None,
) -> Conversation:
    conversation = Conversation(
        title=title.strip(),
        description=description.strip() if description else None,
        youtube_id=youtube_id.strip() if youtube_id else None,
    )
    session.add(conversation)
    session.commit()
    return conversation


@router.get("/similarity-search")
async def similarity_search_endpoint(query: str, session: SessionDep) -> Any:
    query_embedding = get_embeddings([query]).embeddings[0].values
    results = similarity_search(query_embedding, session)
    dto = []

    for utterance in results:
        dto.append(
            {
                "id": utterance.id,
                "start_time": utterance.start_time,
                "end_time": utterance.end_time,
                "text": utterance.text,
                "speaker_id": utterance.speaker_id,
                "conversation_id": utterance.conversation_id,
                "speaker": utterance.speaker.surname if utterance.speaker else None,
            }
        )

    return dto


@router.get("/full-text")
async def get_full_text(query: str, session: SessionDep) -> Any:
    results = full_text_search(query, session)
    dto = []

    for utterance in results:
        dto.append(
            {
                "id": utterance.id,
                "start_time": utterance.start_time,
                "end_time": utterance.end_time,
                "text": utterance.text,
                "speaker_id": utterance.speaker_id,
                "conversation_id": utterance.conversation_id,
                "speaker": utterance.speaker.surname if utterance.speaker else None,
            }
        )

    return dto


@router.get("/{conversation_id}/speakers")
async def get_speakers(conversation_id: int, session: SessionDep) -> Any:
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        return {"error": "Conversation not found"}

    speakers = session.exec(
        select(Speaker).where(
            Speaker.id.in_(
                select(Utterance.speaker_id)
                .where(Utterance.speaker_id != None)
                .where(Utterance.conversation_id == conversation.id)
                .distinct()
            )
        )
    ).all()

    return speakers


@router.post("/process")
async def process_conversation(
    conversation_id: int,
    filename: str,
    segment: int,
    speakers: list[int],
    session: SessionDep,
) -> Utterance:
    conversation = session.get(Conversation, conversation_id)
    if not conversation:
        return {"error": "Conversation not found"}

    speakers_list = session.exec(select(Speaker).where(Speaker.id.in_(speakers))).all()
    if not speakers_list:
        return {"error": "No valid speakers found for the conversation"}

    speakers_dict = {speaker.id: speaker for speaker in speakers_list}

    segments = get_segments(filename)

    segment = segments[segment]
    embedding = get_embeddings([segment["text"]])

    speaker_id = None
    if segment["speaker"] != -1:
        speaker_id = speakers_dict[speakers[segment["speaker"]]].id

    utterance = Utterance(
        start_time=segment["start"],
        end_time=segment["end"],
        text=segment["text"],
        embedding=embedding.embeddings[0].values,
        conversation_id=conversation.id,
        speaker_id=speaker_id,
    )

    session.add(utterance)
    session.commit()

    return utterance
