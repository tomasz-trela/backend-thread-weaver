from pathlib import Path

from yt_dlp import YoutubeDL


downloads_dir = Path(__file__).resolve().parent.parent.parent / "downloads"
downloads_dir.mkdir(parents=True, exist_ok=True)


def get_yt_dlp():
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(downloads_dir / "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": False,
        "verbose": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        yield ydl
