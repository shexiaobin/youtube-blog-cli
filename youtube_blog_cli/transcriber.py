"""
Audio Transcription Module
Priority: local Whisper → Groq Whisper API (fallback)
"""
import os


def transcribe_with_whisper(audio_path: str, language: str = "zh") -> str:
    """Transcribe using local Whisper model (no API key needed)."""
    try:
        import whisper
    except ImportError:
        print("whisper not installed, skipping local transcription")
        return None

    try:
        file_size = os.path.getsize(audio_path)
        print(f"Local Whisper: transcribing {audio_path} ({file_size / 1024 / 1024:.1f}MB)...")
        print("  Loading model (base)...")

        model = whisper.load_model("base")
        result = model.transcribe(audio_path, language=language)
        text = result.get("text", "")

        if text:
            print(f"  Local Whisper succeeded: {len(text)} chars")
        return text

    except Exception as e:
        print(f"  Local Whisper error: {e}")
        return None


def transcribe_with_groq(audio_path: str, language: str = "zh") -> str:
    """Transcribe using Groq Whisper API (requires API key)."""
    from youtube_blog_cli import config

    if not config.has_groq():
        print("Groq API key not found, skipping")
        return None

    import requests

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}

    try:
        file_size = os.path.getsize(audio_path)
        print(f"Groq Whisper: transcribing {audio_path} ({file_size / 1024 / 1024:.1f}MB)...")

        session = requests.Session()
        session.trust_env = False  # Bypass proxy for large uploads

        with open(audio_path, "rb") as file:
            files = {
                "file": (os.path.basename(audio_path), file, "audio/mpeg"),
                "model": (None, "whisper-large-v3"),
                "response_format": (None, "json"),
                "language": (None, language),
            }
            response = session.post(url, headers=headers, files=files, timeout=300)

            if response.status_code != 200:
                print(f"  Groq Whisper failed: {response.text}")
                return None

            result = response.json()
            text = result.get("text", "")
            if text:
                print(f"  Groq Whisper succeeded: {len(text)} chars")
            return text

    except Exception as e:
        print(f"  Groq Whisper error: {e}")
        return None


def transcribe_audio(audio_path: str, language: str = "zh") -> str:
    """
    Transcribe audio file.
    Priority: local Whisper → Groq API fallback.
    """
    # 1. Try local Whisper first (no API key needed)
    text = transcribe_with_whisper(audio_path, language)
    if text:
        return text

    # 2. Fallback to Groq API
    text = transcribe_with_groq(audio_path, language)
    if text:
        return text

    print("All transcription methods failed")
    return None
