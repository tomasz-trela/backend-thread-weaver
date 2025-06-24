import asyncio
import os
from pathlib import Path
from threading import Event

from sqlmodel import Session, select

from src.data.process_data import get_segments
from src.data.db import get_raw_session


from ..data.entities import Conversation, ConversationStatus, Speaker, Utterance

from yt_dlp import YoutubeDL
from ..services.transcription import transcriptionService


def download_and_rename(ydl: YoutubeDL, url: str, new_name: str) -> Path:
    info = ydl.extract_info(url, download=True)
    original_filepath = Path(ydl.prepare_filename(info)).with_suffix(".mp3")

    new_filepath = original_filepath.with_name(new_name + original_filepath.suffix)

    if os.path.exists(new_filepath):
        os.remove(original_filepath)
    else:
        os.rename(original_filepath, new_filepath)

    return new_filepath


async def process_and_save_utterances_without_speakers(
    session: Session,
    conversation: Conversation,
    speaker_data: dict,
    whisper_data: dict,
) -> None:
    speakers = sorted(set(entry[2] for entry in speaker_data))

    speakers = list(map(lambda entry: Speaker(name=entry, surname="don't know"), speakers))

    session.add_all(speakers)
    session.commit()

    segments = get_segments(speaker_data, whisper_data)

    utterances: list[Utterance] = []
    for segment in segments:
        speaker_id = None
        speaker_index = segment.get("speaker", -1)
        if speaker_index != -1 and speaker_index < len(speakers):
            speaker_id = speakers[speaker_index].id

        utterances.append(
            Utterance(
                start_time=segment["start"],
                end_time=segment["end"],
                text=segment["text"],
                conversation_id=conversation.id,
                speaker_id=speaker_id,
            )
        )

    session.add_all(utterances)
    session.commit()


def periodic_worker(yt_dlp: YoutubeDL, stop_event: Event):
    while not stop_event.is_set():
        session: Session = get_raw_session()
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

            print(
                f"Transcription completed for conversation: {conversation.id} - {conversation.youtube_url}"
            )

            asyncio.run(
                process_and_save_utterances_without_speakers(
                    session=session,
                    conversation=conversation,
                    speaker_data=speaker_data,
                    whisper_data=whisper_data,
                )
            )
            print(
                f"Utterances saved for conversation: {conversation.id} - {conversation.youtube_url}"
            )

            conversation.status = ConversationStatus.completed
            session.add(conversation)
            session.commit()
        
        session.close()
        stop_event.wait(timeout=60)
