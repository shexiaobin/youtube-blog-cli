"""
Minimal configuration for YouTube Blog CLI.
Only TTS and Groq (for audio transcription fallback) are needed.
AI blog generation is handled by Claude Code natively.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

# Base paths
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
BLOGS_DIR = OUTPUT_DIR / "blogs"
AUDIO_DIR = OUTPUT_DIR / "audio"

# Create directories
OUTPUT_DIR.mkdir(exist_ok=True)
BLOGS_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

# AI Blog Generation
AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")  # anthropic / openai / custom
AI_MODEL = os.getenv("AI_MODEL", "")  # Optional model override
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Custom OpenAI-compatible API (used when AI_PROVIDER=custom)
CUSTOM_API_BASE = os.getenv("CUSTOM_API_BASE", "")  # e.g. https://api.deepseek.com
CUSTOM_API_KEY = os.getenv("CUSTOM_API_KEY", "")
CUSTOM_MODEL = os.getenv("CUSTOM_MODEL", "")  # e.g. deepseek-chat

# TTS Configuration
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge")
TTS_VOICE = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")

# Groq API (only used for audio transcription fallback when no subtitles)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# OpenAI API (used for TTS and/or blog generation when AI_PROVIDER=openai)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def has_openai():
    return bool(OPENAI_API_KEY)

def has_groq():
    return bool(GROQ_API_KEY)
