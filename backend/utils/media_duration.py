"""
Helper for extracting audio/video file duration in minutes.
Supported via mutagen: mp3, m4a, wav, ogg, flac.
mp4/webm: returns 0.0 (TODO: add moviepy/ffprobe support).
Never raises — returns 0.0 and logs a warning on any error.
"""
import logging

logger = logging.getLogger(__name__)

_MUTAGEN_FORMATS = {".mp3", ".m4a", ".wav", ".ogg", ".flac"}
_TODO_FORMATS = {".mp4", ".webm"}


def get_media_duration_minutes(file_path: str) -> float:
    """Return duration of audio/video file in minutes. Returns 0.0 if unknown."""
    import os
    ext = os.path.splitext(file_path)[1].lower()

    if ext in _TODO_FORMATS:
        # TODO: add moviepy/ffprobe support for video files
        logger.warning("[media_duration] mp4/webm duration not supported yet, returning 0.0")
        return 0.0

    if ext not in _MUTAGEN_FORMATS:
        logger.warning("[media_duration] unsupported format %s, returning 0.0", ext)
        return 0.0

    try:
        from mutagen import File as MutagenFile
        audio = MutagenFile(file_path)
        if audio is None or not hasattr(audio, "info") or audio.info is None:
            logger.warning("[media_duration] mutagen could not parse %s", file_path)
            return 0.0
        seconds = getattr(audio.info, "length", None)
        if seconds is None or seconds <= 0:
            logger.warning("[media_duration] no length in %s", file_path)
            return 0.0
        return round(seconds / 60.0, 4)
    except Exception as e:
        logger.warning("[media_duration] failed to read duration from %s: %s", file_path, e)
        return 0.0
