import os
import speech_recognition as sr
from pydub import AudioSegment
import imageio_ffmpeg as ffmpeg

# Configure ffmpeg for pydub
AudioSegment.converter = ffmpeg.get_ffmpeg_exe()


def transcribe_audio(audio_path: str, language: str = "en-IN", chunk_duration: int = 60) -> dict:
    """
    Transcribe audio file into text using Google STT via SpeechRecognition.
    Splits audio into chunks for better accuracy.

    Args:
        audio_path (str): Path to audio file.
        language (str): Language code (default: en-IN).
        chunk_duration (int): Duration of each chunk in seconds.

    Returns:
        dict: {"transcript": str, "segments": list}
    """
    if not os.path.exists(audio_path):
        return {"transcript": "", "segments": ["[Error] Audio file not found."]}

    # Convert to WAV for compatibility
    try:
        audio = AudioSegment.from_file(audio_path)
    except Exception as e:
        return {"transcript": "", "segments": [f"[Error] Could not read audio file: {e}"]}

    wav_path = audio_path + ".wav"
    try:
        audio.export(wav_path, format="wav")
    except Exception as e:
        return {"transcript": "", "segments": [f"[Error] Could not convert audio to WAV: {e}"]}

    recognizer = sr.Recognizer()
    segments = []
    transcript_parts = []

    total_duration_ms = len(audio)
    chunk_ms = chunk_duration * 1000

    try:
        with sr.AudioFile(wav_path) as source:
            offset_ms = 0
            chunk_index = 0

            while offset_ms < total_duration_ms:
                # Calculate the actual duration for this chunk (don't go past the end)
                remaining_ms = total_duration_ms - offset_ms
                actual_chunk_s = min(chunk_duration, remaining_ms / 1000)

                if actual_chunk_s < 0.5:
                    break  # Remaining audio too short to process

                try:
                    audio_data = recognizer.record(source, duration=actual_chunk_s)
                except Exception:
                    break  # Source exhausted

                # Skip if no audio data was captured
                if not audio_data.frame_data:
                    break

                start_s = offset_ms // 1000
                end_s = start_s + int(actual_chunk_s)

                try:
                    text = recognizer.recognize_google(audio_data, language=language)
                    segments.append(f"[Chunk {chunk_index + 1} | {start_s}-{end_s}s] {text}")
                    transcript_parts.append(text)
                except sr.UnknownValueError:
                    segments.append(f"[Chunk {chunk_index + 1} | {start_s}-{end_s}s] [Unrecognized speech]")
                except sr.RequestError as e:
                    segments.append(f"[Chunk {chunk_index + 1} | {start_s}-{end_s}s] [API error: {e}]")

                chunk_index += 1
                offset_ms += chunk_ms

    except Exception as e:
        segments.append(f"[Error] Transcription failed: {e}")

    return {
        "transcript": " ".join(transcript_parts),
        "segments": segments
    }
