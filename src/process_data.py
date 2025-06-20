import json

def load_json(file_path):
    with open(file_path, "r", encoding='utf8') as f:
        return json.load(f)

def seconds_to_time(seconds):
    """Convert seconds to a formatted time string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:06.3f}"

def simplify_whisper_segments(whisper_data):
    simplified_segments = []

    for segment in whisper_data["segments"]:
        start = segment["start"]
        end = segment["end"]
        text = segment["text"].strip()

        if text:  # Only include segments with non-empty text
            simplified_segments.append({
                "start": start,
                "end": end,
                "text": text
            })

    return simplified_segments

def calculate_overlap(start1, end1, start2, end2):
    return max(0, min(end1, end2) - max(start1, start2))

def calculate_overlap_score(w_start, w_end, s_start, s_end):
    """
    Oblicza score jako iloczyn overlap_ratio_w (Whisper) i overlap_ratio_s (speaker),
    ale dba o to, żeby żadna wartość nie przekroczyła 1.0
    """
    overlap = max(0, min(w_end, s_end) - max(w_start, s_start))
    w_duration = max(w_end - w_start, 1e-6)  # zapobiega dzieleniu przez 0
    s_duration = max(s_end - s_start, 1e-6)

    ratio_w = min(1.0, overlap / w_duration)
    ratio_s = min(1.0, overlap / s_duration)

    return ratio_w * ratio_s

def estimate_duration_from_text(text, method="words", wpm=150):
    """
    Szacuje czas trwania wypowiedzi na podstawie tekstu
    method = "words" lub "chars"
    """
    if method == "words":
        word_count = len(text.split())
        return word_count / (wpm / 60)
    elif method == "chars":
        char_count = len(text)
        return char_count / 15  # ~15 znaków na sekundę
    else:
        raise ValueError("Method must be 'words' or 'chars'")

def combine_segments(speaker_data, whisper_data, min_overlap_ratio=0.25, verbose=False):
    combined_segments = []
    no_speaker = 0
    filtered_by_duration = 0

    for segment in whisper_data["segments"]:
        w_start = segment["start"]
        w_end = segment["end"]
        w_text = segment["text"].strip()

        segment_data = {
            "start": w_start,
            "end": w_end,
            "text": w_text
        }

        matches = []
        estimated_duration = estimate_duration_from_text(w_text)
        for s_start, s_end, speaker in speaker_data:
            if estimated_duration / 2 > (s_end - s_start):
                filtered_by_duration += 1
                continue
            overlap = calculate_overlap(w_start, w_end, s_start, s_end)
            if overlap > 0:
                matches.append((s_start, s_end, speaker, overlap))

        if len(matches) == 1:
            segment_data["speaker"] = matches[0][2]
            segment_data["method"] = "exact"
        elif len(matches) > 1:
            segment_data["method"] = "multiple"
            best_overlap = 0
            best_speaker = "UNKNOWN"

            for spk_start, spk_end, spk, overlap in matches:
                overlap = calculate_overlap_score(w_start, w_end, spk_start, spk_end)
                duration = w_end - w_start
                if duration > 0:
                    overlap_ratio = overlap / duration
                    if overlap_ratio > best_overlap:
                        best_overlap = overlap_ratio
                        best_speaker = spk

            if best_overlap >= min_overlap_ratio:
                segment_data["speaker"] = best_speaker
            else:
                if verbose:
                    print(f"Warning: Low overlap ({best_overlap:.2f}) for segment [{w_start:.2f} - {w_end:.2f}].")
                segment_data["speaker"] = "UNKNOWN"
        else:
            segment_data["method"] = "none"
            segment_data["speaker"] = "UNKNOWN"

        combined_segments.append(segment_data)

        if segment_data["speaker"] == "UNKNOWN":
            no_speaker += 1

    # print(f"Filtered {filtered_by_duration} segments based on estimated duration.")
    return combined_segments, no_speaker

def print_combined_segments(segments):
    for segment in segments:
        start = segment["start"]
        end = segment["end"]
        text = segment["text"]
        speaker = segment.get("speaker", "UNKNOWN")
        print(f"[{start:.2f}s - {end:.2f}s] Speaker: {speaker} - {text}")

def save_combined_segments_as_srt(segments, file_path):
    with open(file_path, "w", encoding='utf8') as f:
        for i, segment in enumerate(segments):
            start = seconds_to_time(segment["start"])
            end = seconds_to_time(segment["end"])
            text = segment["text"]
            speaker = segment.get("speaker", "UNKNOWN")
            f.write(f"{i + 1}\n{start} --> {end}\n{segment.get('method')} {speaker} - {text}\n\n")

def test_different_settings(speaker_data, whisper_data):
    min_overlap_ratio = 0.0
    while min_overlap_ratio <= 0.5:
        combined_segments, no_speaker = combine_segments(
            speaker_data, whisper_data, min_overlap_ratio=min_overlap_ratio, verbose=False
        )
        min_overlap_ratio += 0.01
        print(f"\nStatistics for min overlap ratio {min_overlap_ratio:.2f}s:")
        print(f"Percentage of segments with no speaker: {no_speaker / len(whisper_data['segments']) * 100:.2f}%")

def change_speaker_name(segments, old_name, new_name):
    for segment in segments:
        if segment.get("speaker") == old_name:
            segment["speaker"] = new_name
    return segments

def numerate_speakers(segments):
    for i, segment in enumerate(segments):
        if segment['speaker'] == "UNKNOWN":
            segment['speaker'] = -1
        else:
            segment['speaker'] = int(segment['speaker'].split('_')[-1])

def get_segments(dataset_filename):
    speaker_file = f"../dataset/{dataset_filename}_speaker_segments.json"
    whisper_file = f"../dataset/{dataset_filename}_whisper_segments.json"

    speaker_data = load_json(speaker_file)
    whisper_data = load_json(whisper_file)


    combined_segments, no_speaker = combine_segments(
        speaker_data, whisper_data, min_overlap_ratio=0.05, verbose=False)

    numerate_speakers(combined_segments)

    return combined_segments


if __name__ == "__main__":
    speaker_file = "../dataset/mentzen-trzask_speaker_segments.json"
    whisper_file = "../dataset/mentzen-trzask_whisper_segments.json"

    speaker_data = load_json(speaker_file)
    whisper_data = load_json(whisper_file)

    test_different_settings(speaker_data, whisper_data)


    # combined_segments, no_speaker = combine_segments(
    #     speaker_data, whisper_data, min_overlap_ratio=0.05, verbose=False)
    # # print_combined_segments(combined_segments)
    # combined_segments = change_speaker_name(combined_segments, "SPEAKER_00", "MENTZEN")
    # combined_segments = change_speaker_name(combined_segments, "SPEAKER_01", "TRZASKOWSKI")
    # save_combined_segments_as_srt(combined_segments, "../srt/mentzen-trzask_combined_segments.srt")


    # simplified_whisper_data = simplify_whisper_segments(whisper_data)
    # with open("../dataset/mentzen-trzask_simplified_whisper_segments.json", "w") as f:
    #     json.dump(simplified_whisper_data, f, indent=4)