import os
import speech_recognition as sr
from pydub import AudioSegment
import imageio_ffmpeg as ffmpeg

# Configure ffmpeg for pydub
AudioSegment.converter = ffmpeg.get_ffmpeg_exe()

def transcribe_audio(audio_path, language="en-IN", chunk_duration=60):
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
        return {"transcript": "", "segments": []}

    # Convert to WAV for compatibility
    audio = AudioSegment.from_file(audio_path)
    wav_path = audio_path + ".wav"
    audio.export(wav_path, format="wav")

    recognizer = sr.Recognizer()
    segments = []
    transcript_parts = []

    with sr.AudioFile(wav_path) as source:
        chunk_index = 0
        start_ms = 0
        while True:
            audio_data = recognizer.record(source, duration=chunk_duration)
            if not audio_data.frame_data:
                break
            try:
                text = recognizer.recognize_google(audio_data, language=language)
                end_ms = start_ms + chunk_duration * 1000
                segments.append(f"[Chunk {chunk_index+1} | {start_ms//1000}-{end_ms//1000}s] {text}")
                transcript_parts.append(text)
            except sr.UnknownValueError:
                segments.append(f"[Chunk {chunk_index+1}] [Unrecognized speech]")
            except sr.RequestError as e:
                segments.append(f"[Chunk {chunk_index+1}] [API error: {e}]")
            chunk_index += 1
            start_ms += chunk_duration * 1000

    return {
        "transcript": " ".join(transcript_parts),
        "segments": segments
    }