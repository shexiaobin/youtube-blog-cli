"""
Text-to-Speech Engine
Converts blog text to audio using OpenAI TTS or Edge TTS
"""
import asyncio
import re
from pathlib import Path
from typing import Optional
from youtube_blog_cli import config


def clean_text_for_tts(text: str) -> str:
    """Clean markdown text for TTS conversion."""
    # Remove markdown headers
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    
    # Remove markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Italic
    text = re.sub(r'`([^`]+)`', r'\1', text)  # Code
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Links
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove blockquotes marker
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    
    # Remove horizontal rules
    text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
    
    # Remove details/summary blocks
    text = re.sub(r'<details>.*?</details>', '', text, flags=re.DOTALL)
    
    # Clean up extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    return text


async def generate_audio_edge(text: str, output_path: Path, voice: str = None) -> bool:
    """Generate audio using Edge TTS (free)."""
    try:
        import edge_tts
        
        voice = voice or config.TTS_VOICE
        clean_text = clean_text_for_tts(text)
        
        communicate = edge_tts.Communicate(clean_text, voice)
        await communicate.save(str(output_path))
        
        return True
        
    except Exception as e:
        print(f"Edge TTS error: {e}")
        return False


def generate_audio_openai(text: str, output_path: Path, voice: str = "nova") -> bool:
    """Generate audio using OpenAI TTS."""
    if not config.has_openai():
        return False
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        clean_text = clean_text_for_tts(text)
        
        # OpenAI TTS has a 4096 character limit per request
        # For longer texts, we need to split and concatenate
        if len(clean_text) <= 4096:
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=clean_text
            )
            response.stream_to_file(str(output_path))
            return True
        else:
            # For long texts, use Edge TTS as fallback
            print("Text too long for OpenAI TTS, using Edge TTS")
            return asyncio.run(generate_audio_edge(text, output_path))
            
    except Exception as e:
        print(f"OpenAI TTS error: {e}")
        return False


def generate_audio(text: str, output_path: str, engine: str = None) -> bool:
    """
    Generate audio from text.
    
    Args:
        text: Text content to convert
        output_path: Output file path (mp3)
        engine: 'openai' or 'edge' (default from config)
        
    Returns:
        True if successful
    """
    engine = engine or config.TTS_ENGINE
    path = Path(output_path)
    
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if engine == "openai" and config.has_openai():
        if generate_audio_openai(text, path):
            return True
        # Fallback to edge
        print("Falling back to Edge TTS")
    
    # Use Edge TTS
    return asyncio.run(generate_audio_edge(text, path))


def get_available_voices() -> dict:
    """Get available TTS voices."""
    return {
        "edge": {
            "zh-CN-XiaoxiaoNeural": "晓晓 (女声)",
            "zh-CN-YunxiNeural": "云希 (男声)",
            "zh-CN-XiaoyiNeural": "晓伊 (女声)",
            "zh-CN-YunjianNeural": "云健 (男声)",
            "en-US-JennyNeural": "Jenny (English Female)",
            "en-US-GuyNeural": "Guy (English Male)",
        },
        "openai": {
            "alloy": "Alloy (中性)",
            "echo": "Echo (男声)",
            "fable": "Fable (男声)",
            "onyx": "Onyx (男声)",
            "nova": "Nova (女声)",
            "shimmer": "Shimmer (女声)",
        }
    }


if __name__ == "__main__":
    # Test
    test_text = """
    # 测试博客
    
    这是一段测试文本，用于验证语音合成功能。
    
    ## 主要内容
    
    1. 第一点：测试中文语音合成
    2. 第二点：验证音频生成
    """
    
    output_file = config.AUDIO_DIR / "test_audio.mp3"
    success = generate_audio(test_text, str(output_file))
    print(f"Audio generation {'successful' if success else 'failed'}: {output_file}")
