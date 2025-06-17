from pprint import pprint
import numpy as np

file = "braun_full.mp3"
file_without_ext = file.rsplit('.', 1)[0]

from pyannote.audio import Pipeline
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token="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")

# send pipeline to GPU (when available)
import torch
pipeline.to(torch.device("cuda"))

# apply pretrained pipeline
diarization = pipeline(file)


speaker_data = []

# print the result
for turn, _, speaker in diarization.itertracks(yield_label=True):
    speaker_data.append((turn.start, turn.end, speaker))

with open(file_without_ext + "_speaker_segments.json", "w", encoding="utf8") as f:
    import json
    json.dump(speaker_data, f, indent=4)


import whisper

model = whisper.load_model("turbo")
result = model.transcribe(file)

with open(file_without_ext + "_whisper_segments.json", "w", encoding="utf8") as f:
    import json
    json.dump(result, f, indent=4)
