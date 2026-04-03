"""
YouTube Video Fetcher using yt-dlp
Supports fetching channel videos and extracting transcripts
"""
from __future__ import annotations

import yt_dlp
import re
from typing import Optional, List, Dict


def extract_channel_id(url: str) -> Optional[str]:
    """Extract channel identifier from various YouTube URL formats."""
    patterns = [
        r'youtube\.com/channel/([^/?]+)',
        r'youtube\.com/c/([^/?]+)',
        r'youtube\.com/@([^/?]+)',
        r'youtube\.com/user/([^/?]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_channel_videos(channel_url: str, count: int = 10) -> List[Dict]:
    """
    Fetch latest videos from a YouTube channel.
    
    Args:
        channel_url: YouTube channel URL
        count: Number of videos to fetch
        
    Returns:
        List of video info dictionaries
    """
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlist_items': f'1:{count}',
        'nocheckcertificate': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
    }
    
    # Handle different URL formats
    if '@' in channel_url and '/videos' not in channel_url:
        channel_url = channel_url.rstrip('/') + '/videos'
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(channel_url, download=False)
            
            if result is None:
                return []
            
            videos = []
            entries = result.get('entries', [])
            
            for entry in entries[:count]:
                if entry:
                    videos.append({
                        'id': entry.get('id', ''),
                        'title': entry.get('title', 'Unknown'),
                        'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                        'thumbnail': entry.get('thumbnail', ''),
                        'duration': entry.get('duration', 0),
                    })
            
            return videos
    except Exception as e:
        print(f"Error fetching channel videos: {e}")
        return []


def _get_video_info_oembed(video_url: str) -> Optional[dict]:
    """
    Get video info using YouTube's public oEmbed API.
    This endpoint is lightweight and NOT blocked by YouTube on cloud IPs.
    """
    import requests
    
    video_id = extract_video_id(video_url)
    if not video_id:
        return None
    
    try:
        canonical_url = f"https://www.youtube.com/watch?v={video_id}"
        oembed_url = f"https://www.youtube.com/oembed?url={canonical_url}&format=json"
        
        resp = requests.get(oembed_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ oEmbed API success: {data.get('title', '')[:50]}")
            return {
                'id': video_id,
                'title': data.get('title', 'Unknown'),
                'description': '',  # oEmbed doesn't provide description
                'url': canonical_url,
                'thumbnail': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                'duration': 0,
                'channel': data.get('author_name', 'Unknown'),
                'upload_date': '',
            }
        else:
            print(f"⚠️ oEmbed API returned {resp.status_code}")
    except Exception as e:
        print(f"⚠️ oEmbed API error: {e}")
    
    return None


def _get_video_info_ytdlp(video_url: str) -> Optional[dict]:
    """Get video info using yt-dlp (may fail on cloud IPs)."""
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'nocheckcertificate': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(video_url, download=False)
            
            if result:
                return {
                    'id': result.get('id', ''),
                    'title': result.get('title', 'Unknown'),
                    'description': result.get('description', ''),
                    'url': video_url,
                    'thumbnail': result.get('thumbnail', ''),
                    'duration': result.get('duration', 0),
                    'channel': result.get('uploader', 'Unknown'),
                    'upload_date': result.get('upload_date', ''),
                }
    except Exception as e:
        print(f"⚠️ yt-dlp error: {e}")
    
    return None


def get_video_info(video_url: str) -> Optional[dict]:
    """
    Get detailed information about a single video.
    Strategy: yt-dlp first (more complete data), oEmbed API fallback (cloud-safe).
    
    Args:
        video_url: YouTube video URL
        
    Returns:
        Video info dictionary or None
    """
    # 1. Try yt-dlp first (returns more complete data)
    print(f"📡 Fetching video info: {video_url}")
    result = _get_video_info_ytdlp(video_url)
    if result:
        return result
    
    # 2. Fallback to oEmbed API (lightweight, works on cloud IPs like Render)
    print(f"🔄 yt-dlp failed, trying oEmbed API...")
    result = _get_video_info_oembed(video_url)
    if result:
        return result
    
    print(f"❌ All methods failed for: {video_url}")
    return None


def get_video_transcript(video_url: str, language: str = 'zh') -> Optional[str]:
    """
    Extract transcript/subtitles from a YouTube video using youtube_transcript_api.
    
    Args:
        video_url: YouTube video URL
        language: Preferred language for subtitles (default: 'zh')
        
    Returns:
        Transcript text or None
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        return None
        
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api.formatters import TextFormatter
        
        # Try to retrieve transcript
        # First try preferred language, then English, then auto-generated
        try:
            # Instantiate API (v1.2.3 requires instantiation)
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
            
            # Try to find manually created transcript
            transcript = None
            
            # 1. Try target language (manual)
            try:
                transcript = transcript_list.find_transcript([language])
            except:
                # 2. Try Chinese variants (manual)
                try:
                    transcript = transcript_list.find_transcript(['zh-Hans', 'zh-Hant', 'zh-CN', 'zh-TW'])
                except:
                    # 3. Try English (manual)
                    try:
                        transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
                    except:
                        # 4. Fallback to any available original transcript
                         for t in transcript_list:
                             transcript = t
                             break
            
            # Translate if needed
            if transcript:
                if language == 'zh' and not transcript.language_code.startswith('zh'):
                    try:
                        transcript = transcript.translate('zh-Hans')
                    except Exception as e:
                        print(f"Translation failed: {e}")
                
                # Fetch the actual transcript data
                transcript_data = transcript.fetch()
                
                # Format to text
                formatter = TextFormatter()
                text = formatter.format_transcript(transcript_data)
                return text
                
        except Exception as e:
            print(f"YouTubeTranscriptApi error: {e}")
            # Fall through to yt-dlp fallback
            
    except ImportError:
        print("youtube_transcript_api not installed")

    # Fallback to yt-dlp (original implementation)
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': [language, 'en', 'zh-Hans', 'zh-Hant'],
        'subtitlesformat': 'vtt',
        'nocheckcertificate': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(video_url, download=False)
            
            if not result:
                return None
            
            # Try to get subtitles
            subtitles = result.get('subtitles', {})
            auto_subs = result.get('automatic_captions', {})
            
            # Priority: manual subs > auto subs
            all_subs = {**auto_subs, **subtitles}
            
            # Find best matching language
            for lang in [language, 'zh-Hans', 'zh-Hant', 'en']:
                if lang in all_subs:
                    # Get the subtitle data
                    sub_info = all_subs[lang]
                    if sub_info and len(sub_info) > 0:
                        # Try to get the URL for vtt or srv3 format
                        for fmt in sub_info:
                            if fmt.get('ext') in ['vtt', 'srv3', 'json3']:
                                sub_url = fmt.get('url')
                                if sub_url:
                                    return _fetch_and_parse_subtitles(sub_url, fmt.get('ext'))
            
            # If no subtitles found, try audio transcription fallback
            print("No subtitles found, attempting audio transcription fallback...")
            transcript = _download_and_transcribe(video_url)
            if transcript:
                return transcript
            
            # If transcription fails, return description as fallback
            description = result.get('description', '')
            if description:
                print("WARNING: Transcription failed, falling back to video description")
                return f"[视频描述]\n{description}"
            
            return None
            
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None


def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from URL."""
    # Match both standard and short URLs
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if match:
        return match.group(1)
    return None


def _fetch_and_parse_subtitles(url: str, ext: str) -> Optional[str]:
    """Fetch and parse subtitle content from URL."""
    import urllib.request
    import json
    
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read().decode('utf-8')
            
            if ext == 'json3':
                # Parse JSON3 format
                data = json.loads(content)
                texts = []
                for event in data.get('events', []):
                    segs = event.get('segs', [])
                    for seg in segs:
                        text = seg.get('utf8', '').strip()
                        if text and text != '\n':
                            texts.append(text)
                return ' '.join(texts)
            
            elif ext == 'vtt':
                # Parse VTT format
                lines = content.split('\n')
                texts = []
                for line in lines:
                    line = line.strip()
                    # Skip timestamps, headers, and empty lines
                    if not line or line.startswith('WEBVTT') or '-->' in line:
                        continue
                    # Skip numeric cue identifiers
                    if line.isdigit():
                        continue
                    # Remove VTT tags
                    clean = re.sub(r'<[^>]+>', '', line)
                    if clean:
                        texts.append(clean)
                return ' '.join(texts)
            
            else:
                # For srv3 or other formats, try basic text extraction
                clean = re.sub(r'<[^>]+>', '', content)
                return clean
                
    except Exception as e:
        print(f"Error parsing subtitles: {e}")
        return None


def _download_and_transcribe(video_url: str) -> Optional[str]:
    """Download audio and transcribe it as a fallback."""
    from youtube_blog_cli import transcriber
    import uuid
    import os

    temp_filename = f"temp_audio_{uuid.uuid4().hex}"
    
    # Download params - try to get m4a directly to avoid ffmpeg dependency
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': temp_filename,
        'quiet': True,
        'extractor_args': {'youtube': {'player_client': ['android']}},
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }
    
    # yt-dlp might append extension to filename
    expected_filename = f"{temp_filename}.m4a"
    fallback_filename = temp_filename # Sometimes it doesn't add extension if we don't specify
    
    try:
        print(f"Downloading audio for transcription (this may take a moment)...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
        # Find the actual file (yt-dlp might add extension)
        final_filename = None
        if os.path.exists(expected_filename):
            final_filename = expected_filename
        elif os.path.exists(f"{temp_filename}.webm"):
            final_filename = f"{temp_filename}.webm"
        elif os.path.exists(temp_filename):
            final_filename = temp_filename
            
        if final_filename and os.path.exists(final_filename):
            # Ensure file has extension for Groq API
            if not final_filename.endswith('.m4a') and not final_filename.endswith('.mp3') and not final_filename.endswith('.webm'):
                new_filename = f"{final_filename}.m4a"
                try:
                    os.rename(final_filename, new_filename)
                    final_filename = new_filename
                except Exception as e:
                    print(f"Failed to rename file: {e}")

            print(f"Transcribing audio ({final_filename})...")
            text = transcriber.transcribe_audio(final_filename)
            
            # Cleanup
            try:
                os.remove(final_filename)
            except:
                pass
            
            if text:
                print(f"Transcription successful: {len(text)} chars")
                return text
            else:
                print("Transcription returned empty result")
        else:
            print(f"Audio file not found after download. Expected: {expected_filename}")
                
    except Exception as e:
        print(f"Audio transcription fallback failed: {e}")
        # Cleanup on error
        for f in [expected_filename, f"{temp_filename}.webm", temp_filename]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass
            
    return None


if __name__ == "__main__":
    # Test with a sample video
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    info = get_video_info(test_url)
    print(f"Video info: {info}")
