import torch
import whisper
from pyannote.audio import Pipeline
from .config import settings
import tempfile
import os
# Zrobiłem leniwe ładowanie modeli aby nie czekać przy kadym urchmieniu api


class TranscriptionService:
    def __init__(self, whisper_model_name: str = "turbo"):
        self._whisper_model = None
        self._whisper_model_name = whisper_model_name

        self._diarization_pipeline = None

    def _load_whisper_model(self):
        if self._whisper_model is None:
            self._whisper_model = whisper.load_model(self._whisper_model_name)

    def _load_diarization_pipeline(self):
        if self._diarization_pipeline is None:
            self._diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=settings.SPEAKER_DIARIZATION_TOKEN,
            )
            self._diarization_pipeline.to(
                torch.device("cuda" if torch.cuda.is_available() else "cpu")
            )

    def process_audio(self, audio_bytes: bytes) -> tuple[list, dict]:
        self._load_whisper_model()
        self._load_diarization_pipeline()

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            diarization = self._diarization_pipeline(tmp_path)

            speaker_data = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speaker_data.append(
                    {
                        "start": turn.start,
                        "end": turn.end,
                        "speaker": speaker,
                    }
                )

            transcription_result = self._whisper_model.transcribe(tmp_path)

        finally:
            if "tmp_path" in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)

        return (speaker_data, transcription_result)
