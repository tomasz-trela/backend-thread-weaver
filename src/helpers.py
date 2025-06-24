import asyncio
from datetime import date
import json
from typing import List, Optional
from fastapi import HTTPException, UploadFile
from sqlmodel import select

from src.data.db import Conversation, Speaker, Utterance
from src.data.entities import ConversationStatus
from src.data.googleapi import get_embeddings
from src.data.process_data import get_segments
from src.services.transcription import TranscriptionService
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
    status: Optional[ConversationStatus] = None,
    youtube_url: Optional[str] = None,
) -> Conversation:
    if youtube_url:
        status = ConversationStatus.pending

    conversation = Conversation(
        title=name.strip(),
        description=description.strip() if description else None,
        youtube_id=youtube_id.strip() if youtube_id else None,
        conversation_date=conversation_date,
        youtube_url=youtube_url.strip() if youtube_url else None,
        status=status,
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
    utterances = await asyncio.gather(*tasks, return_exceptions=True)
    for utterance in utterances:
        if isinstance(utterance, Utterance):
            session.add(utterance)
        else:
            # Handle exceptions that occurred during processing
            print(f"Error processing segment: {utterance}")

    session.commit()


async def create_conversation_from_audio(
    session: SessionDep,
    audio_file: UploadFile,
    name: str,
    speakers: List[int],
    transcriptionService: TranscriptionService,
    description: Optional[str] = None,
    youtube_id: Optional[str] = None,
    conversation_date: Optional[date] = None,
):
    conversation = create_conversation(
        session=session,
        name=name,
        description=description,
        youtube_id=youtube_id,
        conversation_date=conversation_date,
    )

    contents = await audio_file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="File is empty")
    speaker_data, whisper_data = transcriptionService.process_audio(contents)

    await process_and_save_utterances(
        session=session,
        conversation=conversation,
        speakers=speakers,
        speaker_data=speaker_data,
        whisper_data=whisper_data,
    )


async def create_conversation_from_text(
    session: SessionDep,
    speaker_data_bytes: bytes,
    whisper_data_bytes: bytes,
    name: str,
    speakers: List[int],
    description: Optional[str] = None,
    youtube_id: Optional[str] = None,
    conversation_date: Optional[date] = None,
):
    conversation = create_conversation(
        session=session,
        name=name,
        description=description,
        youtube_id=youtube_id,
        conversation_date=conversation_date,
    )

    speaker_data = json.loads(speaker_data_bytes.decode("utf8"))
    whisper_data = json.loads(whisper_data_bytes.decode("utf8"))

    await process_and_save_utterances(
        session=session,
        conversation=conversation,
        speakers=speakers,
        speaker_data=speaker_data,
        whisper_data=whisper_data,
        limit=50,
    )

    return conversation


def run_async_task(fn, *args, **kwargs):
    asyncio.run(fn(*args, **kwargs))
