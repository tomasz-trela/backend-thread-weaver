import pytest
from src.data.process_data import (
    seconds_to_time,
    simplify_whisper_segments,
    calculate_overlap,
    calculate_overlap_score,
    estimate_duration_from_text,
    combine_segments,
    change_speaker_name,
    numerate_speakers,
    get_segments,
)


@pytest.mark.parametrize(
    "seconds, expected_str",
    [
        (0, "00:00:00.000"),
        (59.1234, "00:00:59.123"),
        (60, "00:01:00.000"),
        (125.5, "00:02:05.500"),
        (3600, "01:00:00.000"),
        (3723.4567, "01:02:03.457"),
    ],
)
def test_seconds_to_time(seconds, expected_str):
    assert seconds_to_time(seconds) == expected_str


def test_simplify_whisper_segments():
    whisper_data = {
        "segments": [
            {"start": 0.0, "end": 1.0, "text": "  Hello world.  "},
            {"start": 1.5, "end": 2.5, "text": ""},
            {"start": 3.0, "end": 4.0, "text": "   "},
            {"start": 4.5, "end": 5.5, "text": "Another segment."},
        ]
    }
    expected = [
        {"start": 0.0, "end": 1.0, "text": "Hello world."},
        {"start": 4.5, "end": 5.5, "text": "Another segment."},
    ]
    assert simplify_whisper_segments(whisper_data) == expected


@pytest.mark.parametrize(
    "s1, e1, s2, e2, expected_overlap",
    [
        (0, 5, 6, 10, 0),
        (0, 5, 5, 10, 0),
        (0, 5, 3, 8, 2),
        (0, 10, 2, 5, 3),
        (2, 5, 0, 10, 3),
        (0, 5, 0, 5, 5),
    ],
)
def test_calculate_overlap(s1, e1, s2, e2, expected_overlap):
    assert calculate_overlap(s1, e1, s2, e2) == expected_overlap


@pytest.mark.parametrize(
    "w_start, w_end, s_start, s_end, expected_score",
    [
        (0, 10, 0, 10, 1.0),
        (0, 5, 6, 10, 0.0),
        (2, 5, 0, 10, 0.3),
        (0, 10, 2, 5, 0.3),
        (0, 5, 3, 8, 0.16),
    ],
)
def test_calculate_overlap_score(w_start, w_end, s_start, s_end, expected_score):
    assert calculate_overlap_score(w_start, w_end, s_start, s_end) == pytest.approx(
        expected_score
    )


def test_estimate_duration_from_text():
    assert estimate_duration_from_text(
        "Hello world", method="words", wpm=150
    ) == pytest.approx(0.8)

    assert estimate_duration_from_text(
        "Hello world",
        method="chars",
    ) == pytest.approx(0.7333333333333333)
    assert estimate_duration_from_text(
        "This is a test sentence.", method="words", wpm=120
    ) == pytest.approx(2.5)
    with pytest.raises(ValueError):
        estimate_duration_from_text("test", method="invalid")


@pytest.fixture
def sample_speaker_data():
    return [
        (0.0, 4.0, "SPEAKER_00"),
        (4.5, 8.0, "SPEAKER_01"),
        (8.5, 12.0, "SPEAKER_00"),
        (12.5, 13.5, "SPEAKER_01"),
    ]


@pytest.fixture
def sample_whisper_data():
    return {
        "segments": [
            {"start": 1.0, "end": 3.0, "text": "This is a test."},
            {"start": 4.1, "end": 4.4, "text": "No match."},
            {"start": 3.8, "end": 5.2, "text": "Multiple matches here."},
            {"start": 8.0, "end": 9.0, "text": "Low overlap"},
            {
                "start": 12.0,
                "end": 14.0,
                "text": "This is a very very very long sentence for testing duration filter.",
            },
        ]
    }


@pytest.fixture
def combined_result(sample_speaker_data, sample_whisper_data):
    return combine_segments(
        sample_speaker_data, sample_whisper_data, min_overlap_ratio=0.25
    )


def test_combine_segments_summary(combined_result):
    combined_segments, no_speaker_count = combined_result
    assert len(combined_segments) == 5
    assert no_speaker_count == 3


def test_combine_segments_cases(combined_result):
    combined_segments, _ = combined_result

    assert combined_segments[0]["speaker"] == "SPEAKER_00"
    assert combined_segments[0]["method"] == "exact"

    assert combined_segments[1]["speaker"] == "UNKNOWN"
    assert combined_segments[1]["method"] == "none"


def test_change_speaker_name():
    segments = [
        {"speaker": "SPEAKER_00"},
        {"speaker": "SPEAKER_01"},
        {"speaker": "SPEAKER_00"},
    ]
    expected = [{"speaker": "Alice"}, {"speaker": "SPEAKER_01"}, {"speaker": "Alice"}]
    assert change_speaker_name(segments, "SPEAKER_00", "Alice") == expected
    assert change_speaker_name(segments, "SPEAKER_99", "Bob") == expected


def test_numerate_speakers():
    segments = [
        {"speaker": "SPEAKER_01"},
        {"speaker": "UNKNOWN"},
        {"speaker": "SPEAKER_00"},
    ]
    numerate_speakers(segments)
    expected = [{"speaker": 1}, {"speaker": -1}, {"speaker": 0}]
    assert segments == expected


def test_get_segments_integration():
    speaker_data = [(0, 5, "SPEAKER_00")]
    whisper_data = {"segments": [{"start": 1, "end": 4, "text": "Hello"}]}

    combined = get_segments(speaker_data, whisper_data)

    assert len(combined) == 1
    segment = combined[0]
    assert segment["speaker"] == 0
    assert segment["text"] == "Hello"
    assert segment["method"] == "exact"
