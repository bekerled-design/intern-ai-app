import tempfile
import os

from utils.usage_tracker import record_transcription_usage


def transcribe_video(client, uploaded_file, user_id=None):

    uploaded_file.seek(0)

    file_bytes = uploaded_file.read()

    suffix = "." + uploaded_file.name.split(".")[-1].lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name

    try:
        with open(temp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )

        if user_id is not None:
            # TODO: extract actual duration from file for accurate cost estimate
            record_transcription_usage(user_id, "whisper-1", duration_minutes=0.0)

        return str(transcript)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)