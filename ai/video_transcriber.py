import tempfile
import os


def transcribe_video(client, uploaded_file):

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

        return str(transcript)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)