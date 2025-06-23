import asyncio
from datetime import date
import json
from typing import List, Optional
from fastapi import HTTPException, UploadFile
from sqlmodel import select

from src.data.db import Conversation, Speaker, Utterance
from src.data.googleapi import get_embeddings
from src.data.process_data import get_segments
from .typedefs import SessionDep


async def load_json(upload_file: UploadFile):
    content = await upload_file.read()
    return json.loads(content.decode("utf8"))


def create_conversation(
    session: SessionDep,
    name: str,
    description: Optional[str],
    youtube_id: Optional[str],
    conversation_date: Optional[date],
) -> Conversation:
    conversation = Conversation(
        title=name.strip(),
        description=description.strip() if description else None,
        youtube_id=youtube_id.strip() if youtube_id else None,
        conversation_date=conversation_date,
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


async def process_and_save_utterances(
    session: SessionDep,
    conversation: Conversation,
    speakers: List[int],
    speaker_data: dict,
    whisper_data: dict,
    limit: Optional[int] = None,
) -> None:
    speakers_in_db = session.exec(select(Speaker).where(Speaker.id.in_(speakers))).all()
    if len(speakers_in_db) != len(set(speakers)):
        found_ids = {s.id for s in speakers_in_db}
        missing_ids = [sid for sid in speakers if sid not in found_ids]
        raise HTTPException(
            status_code=404,
            detail=f"Speaker(s) with the following ID(s) were not found: {missing_ids}",
        )

    segments = get_segments(speaker_data, whisper_data)
    if limit:
        segments = segments[:limit]

    semaphore = asyncio.Semaphore(20)

    async def process_segment(segment):
        async with semaphore:
            embedding = await asyncio.to_thread(get_embeddings, [segment["text"]])

            speaker_id = None
            speaker_index = segment.get("speaker", -1)
            if speaker_index != -1 and speaker_index < len(speakers):
                speaker_id = speakers[speaker_index]

            return Utterance(
                start_time=segment["start"],
                end_time=segment["end"],
                text=segment["text"],
                embedding=embedding.embeddings[0].values,
                conversation_id=conversation.id,
                speaker_id=speaker_id,
            )

    tasks = [process_segment(segment) for segment in segments]
    utterances = await asyncio.gather(*tasks)

    if utterances:
        session.add_all(utterances)
        session.commit()
