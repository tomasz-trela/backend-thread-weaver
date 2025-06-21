import asyncio
import json
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from sqlmodel import select

from ..dto import UtteranceDTO
from ..googleapi import get_embeddings
from ..process_data import get_segments

from ..db import (
    Conversation,
    Speaker,
    Utterance,
    full_text_search,
    similarity_search,
)
from ..typedefs import SessionDep

router = APIRouter(prefix="/conversations", tags=["Conversations"])


async def load_json(upload_file: UploadFile):
    content = await upload_file.read()
    return json.loads(content.decode("utf8"))


@router.post("/text")
async def create_conversation_from_text(
    session: SessionDep,
    speaker_file: UploadFile,
    whisper_file: UploadFile,
    name: str = Form(...),
    speakers: List[int] = Form(...),
    description: Optional[str] = Form(None),
    youtube_id: Optional[str] = Form(None),
) -> Conversation:
    conversation = Conversation(
        title=name.strip(),
        description=description.strip() if description else None,
        youtube_id=youtube_id.strip() if youtube_id else None,
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    speakers_list = session.exec(select(Speaker).where(Speaker.id.in_(speakers))).all()
    if not speakers_list:
        return {"error": "No valid speakers found for the conversation"}

    speakers_dict = {
        speaker_id: speaker for speaker_id, speaker in zip(speakers, speakers_list)
    }

    speaker_data = await load_json(speaker_file)
    whisper_data = await load_json(whisper_file)
    segments = get_segments(speaker_data, whisper_data)

    semaphore = asyncio.Semaphore(20)
    # Limit concurrent embedding requests, due to resource exhaustion exception
    # if you get an error try to chanege it

    async def process_segment(segment):
        async with semaphore:
            embedding = await asyncio.to_thread(get_embeddings, [segment["text"]])

            speaker_id = None
            if segment["speaker"] != -1:
                speaker_index = segment["speaker"]
                speaker_id = speakers_dict.get(speakers[speaker_index]).id

            return Utterance(
                start_time=segment["start"],
                end_time=segment["end"],
                text=segment["text"],
                embedding=embedding.embeddings[0].values,
                conversation_id=conversation.id,
                speaker_id=speaker_id,
            )

    tasks = [process_segment(segment) for segment in segments[:50]]
    utterances = await asyncio.gather(*tasks)

    session.add_all(utterances)
    session.commit()
    return conversation


@router.get("/similarity-search", response_model=list[UtteranceDTO])
async def get_similarity_search(
    query: str,
    session: SessionDep,
    limit: Optional[int] = None,
    speaker_id: Optional[int] = None,
):
    query_embedding = get_embeddings([query]).embeddings[0].values
    results = similarity_search(query_embedding, limit, speaker_id, session)

    return [
        UtteranceDTO(
            id=u.id,
            start_time=u.start_time,
            end_time=u.end_time,
            text=u.text,
            speaker_id=u.speaker_id,
            conversation_id=u.conversation_id,
            speaker=u.speaker.surname if u.speaker else None,
        )
        for u in results
    ]


@router.get("/full-text", response_model=list[UtteranceDTO])
async def get_full_text(
    query: str,
    session: SessionDep,
    limit: Optional[int] = None,
    language: Optional[str] = "polish",
    speaker_id: Optional[int] = None,
):
    results = full_text_search(query, limit, language, speaker_id, session)

    return [
        UtteranceDTO(
            id=u.id,
            start_time=u.start_time,
            end_time=u.end_time,
            text=u.text,
            speaker_id=u.speaker_id,
            conversation_id=u.conversation_id,
            speaker=u.speaker.surname if u.speaker else None,
        )
        for u in results
    ]


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
