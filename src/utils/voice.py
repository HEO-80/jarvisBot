import logging
import os
import re
import subprocess
import tempfile

logger = logging.getLogger("jarvis.voice")

_whisper_model = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        size = os.getenv("WHISPER_MODEL_SIZE", "small")
        _whisper_model = WhisperModel(size, device="cpu", compute_type="int8")
        logger.info(f"Whisper '{size}' cargado")
    return _whisper_model


def clean_for_tts(text: str) -> str:
    text = re.sub(r'\*+([^*]+)\*+', r'\1', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'`+([^`]*)`+', r'\1', text)
    text = re.sub(r'^\s*[-•]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def transcribe(audio_path: str, language: str = "es") -> str:
    try:
        whisper = _get_whisper()
        segments, _ = whisper.transcribe(audio_path, language=language)
        result = " ".join(s.text.strip() for s in segments).strip()
        logger.info(f"Transcripción: {result[:100]}")
        return result
    except Exception as e:
        logger.error(f"Error whisper: {e}")
        return ""


def text_to_speech(text: str, output_path: str, voice_model: str) -> bool:
    try:
        proc = subprocess.run(
            ["piper-tts", "--model", voice_model, "--output_file", output_path],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=60,
        )
        if proc.returncode != 0:
            logger.error(f"Piper stderr: {proc.stderr.decode()}")
        return proc.returncode == 0
    except Exception as e:
        logger.error(f"Error piper-tts: {e}")
        return False


def ogg_to_wav(ogg_path: str, wav_path: str) -> bool:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", wav_path],
        capture_output=True,
    )
    return proc.returncode == 0
