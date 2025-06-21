from pprint import pprint

import torch
import whisper
from pyannote.audio import Pipeline

from config import settings

file = "braun_10.mp3"
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token=settings.SPEAKER_DIARIZATION_TOKEN,
)

# send pipeline to GPU (when available)

pipeline.to(torch.device("cuda"))

# apply pretrained pipeline
diarization = pipeline(file)


speaker_data = []

# print the result
for turn, _, speaker in diarization.itertracks(yield_label=True):
    speaker_data.append((turn.start, turn.end, speaker))


# merge consecutive segments of the same speaker
# for i in range(len(speaker_data) - 1, 0, -1):
#     if speaker_data[i][2] == speaker_data[i - 1][2]:
#         # Merge segments
#         speaker_data[i - 1] = (
#             speaker_data[i - 1][0],
#             speaker_data[i][1],
#             speaker_data[i][2]
#         )
#         # Remove the current segment
#         del speaker_data[i]

pprint("Speaker segments:")
pprint(speaker_data)

model = whisper.load_model("turbo")
result = model.transcribe(file)
seg_delta = 0.3

for segment in result["segments"]:
    segment_start = segment["start"]
    segment_end = segment["end"]
    segment_text = segment["text"].strip()

    # Find the speaker for this segment
    speaker = None
    matches = []

    for start, end, spk in speaker_data:
        if start - seg_delta <= segment_start and segment_end <= end + seg_delta:
            matches.append((start, end, spk))

    if len(matches) > 0:
        speaker = matches[0][2]  # Take the first matching speaker
        if len(matches) > 1:
            print(
                f"Warning: Multiple speakers found for segment [{segment_start:.2f}s - {segment_end:.2f}s]. Using the first one: {speaker}"
            )

    if speaker:
        print(
            f"[{segment_start:.2f}s - {segment_end:.2f}s] Speaker: {speaker}, Text: {segment_text}"
        )
    else:
        print(
            f"[{segment_start:.2f}s - {segment_end:.2f}s] No speaker found, Text: {segment_text}"
        )
