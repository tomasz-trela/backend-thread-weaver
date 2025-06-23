import asyncio
import os
from pathlib import Path
from threading import Event
from typing import Optional

from sqlmodel import Session, select

from src.data.googleapi import get_embeddings
from src.data.process_data import get_segments


from .data.entities import Conversation, ConversationStatus, Speaker, Utterance

from yt_dlp import YoutubeDL
from .services.transcription import transcriptionService


def download_and_rename(ydl: YoutubeDL, url: str, new_name: str) -> Path:
    info = ydl.extract_info(url, download=True)
    original_filepath = Path(ydl.prepare_filename(info)).with_suffix(".mp3")

    new_filepath = original_filepath.with_name(new_name + original_filepath.suffix)

    os.rename(original_filepath, new_filepath)

    return new_filepath


async def process_and_save_utterances_without_speakers(
    session: Session,
    conversation: Conversation,
    speaker_data: dict,
    whisper_data: dict,
    limit: Optional[int] = None,
) -> None:
    speakers = sorted(set(entry[2] for entry in speaker_data))

    speakers = map(lambda entry: Speaker(name=entry, surname="don't know"), speakers)

    session.add_all(speakers)
    session.commit()
    session.refresh(speakers)

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


def periodic_worker(session: Session, yt_dlp: YoutubeDL, stop_event: Event):
    while not stop_event.is_set():
        print("Running periodic task...")

        stmt = (
            select(Conversation)
            .where(Conversation.status == ConversationStatus.pending)
            .limit(1)
        )
        conversation = session.exec(stmt).first()

        if conversation and conversation.youtube_url:
            print(
                f"Processing conversation: {conversation.id} - {conversation.youtube_url}"
            )

            filePath = download_and_rename(
                yt_dlp, conversation.youtube_url, f"conversation_{conversation.id}"
            )

            print(
                f"Finished processing conversation: {conversation.id} - {conversation.youtube_url}"
            )

            speaker_data, whisper_data = transcriptionService.process_audio(filePath)

            process_and_save_utterances_without_speakers(
                session=session,
                conversation=conversation,
                speaker_data=speaker_data,
                whisper_data=whisper_data,
                limit=10,
            )

            conversation.status = ConversationStatus.completed
            session.add(conversation)
            session.commit()

        stop_event.wait(timeout=60)
