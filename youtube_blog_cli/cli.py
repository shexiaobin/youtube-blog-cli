#!/usr/bin/env python3
"""
YouTube Blog CLI — YouTube 视频转博客工具，专为 Claude Code 设计。

Usage:
    youtube-blog transcript <url>                # 获取视频信息 + 字幕
    youtube-blog generate <url> [--tts]          # 一键生成博客（需配置 API Key）
    youtube-blog fetch-channel <url> [--count N] # 获取频道视频列表
    youtube-blog tts <markdown_file> [-o out.mp3] # 将 Markdown 转语音
    youtube-blog prompt                          # 输出博客生成 prompt 模板
"""
import argparse
import builtins
import json
import re
import sys
from pathlib import Path

# Redirect all print() from imported modules to stderr,
# so only our structured output goes to stdout.
_real_print = builtins.print

def _stderr_print(*args, **kwargs):
    kwargs.setdefault("file", sys.stderr)
    _real_print(*args, **kwargs)

builtins.print = _stderr_print

from youtube_blog_cli import config
from youtube_blog_cli.youtube_fetcher import get_channel_videos, get_video_info, get_video_transcript
from youtube_blog_cli.tts_engine import generate_audio


def log(msg: str):
    """Print progress info to stderr."""
    print(msg, file=sys.stderr)


def output_json(data: dict):
    """Print result JSON to stdout."""
    _real_print(json.dumps(data, ensure_ascii=False, indent=2))


PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str = "blog") -> str:
    """Load prompt template from prompts/ directory."""
    prompt_file = PROMPTS_DIR / f"{name}.md"
    if not prompt_file.exists():
        _stderr_print(f"Prompt 文件不存在: {prompt_file}")
        sys.exit(1)
    return prompt_file.read_text(encoding="utf-8")


# ── Helpers ───────────────────────────────────────────────────


def format_duration(seconds: int) -> str:
    """Convert seconds to human-readable duration."""
    if not seconds:
        return "未知"
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    if h > 0:
        return f"{h}小时{m}分钟"
    return f"{m}分钟{s}秒"


def get_length_guide(seconds: int) -> str:
    """Return blog length guidance based on video duration."""
    if not seconds:
        return "篇幅适中，覆盖所有要点即可"
    minutes = seconds / 60
    if minutes <= 5:
        return f"视频较短（{format_duration(seconds)}），博客约 800-1200 字，精炼提取核心要点"
    elif minutes <= 15:
        return f"视频中等（{format_duration(seconds)}），博客约 1500-2500 字，充分展开每个要点"
    elif minutes <= 30:
        return f"视频较长（{format_duration(seconds)}），博客约 2500-4000 字，深入分析各个要点，可分多个章节"
    elif minutes <= 60:
        return f"视频很长（{format_duration(seconds)}），博客约 4000-6000 字，全面覆盖内容，建议使用清晰的章节结构"
    else:
        return f"超长视频（{format_duration(seconds)}），博客约 6000-8000 字，按主题分大章节，每个章节独立完整"


# ── Subcommands ──────────────────────────────────────────────


def cmd_transcript(args):
    """Fetch video info + transcript."""
    url = args.url

    log(f"[1/2] 获取视频信息: {url}")
    info = get_video_info(url)
    if not info:
        log("无法获取视频信息，请检查链接")
        sys.exit(1)
    log(f"  标题: {info.get('title')}")
    log(f"  频道: {info.get('channel')}")

    log("[2/2] 获取视频字幕...")
    transcript = get_video_transcript(url)
    if not transcript:
        log("  未找到字幕")
        transcript = ""
    else:
        log(f"  字幕长度: {len(transcript)} 字符")

    duration = info.get("duration", 0)
    result = {
        "title": info.get("title", ""),
        "channel": info.get("channel", ""),
        "video_url": url,
        "thumbnail": info.get("thumbnail", ""),
        "duration": duration,
        "duration_text": format_duration(duration),
        "length_guide": get_length_guide(duration),
        "transcript": transcript,
        "transcript_length": len(transcript),
    }

    # Optionally save transcript to file
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(transcript, encoding="utf-8")
        log(f"  字幕已保存到: {out_path}")
        result["transcript_file"] = str(out_path)

    output_json(result)


def cmd_fetch_channel(args):
    """Fetch videos from a YouTube channel."""
    log(f"正在获取频道视频: {args.url} (数量: {args.count})")
    videos = get_channel_videos(args.url, args.count)
    if not videos:
        log("未找到视频，请检查链接是否正确")
        sys.exit(1)
    log(f"找到 {len(videos)} 个视频")
    output_json({"count": len(videos), "videos": videos})


def cmd_tts(args):
    """Convert a markdown file to audio."""
    md_path = Path(args.file)
    if not md_path.exists():
        log(f"文件不存在: {md_path}")
        sys.exit(1)

    text = md_path.read_text(encoding="utf-8")
    if not text.strip():
        log("文件内容为空")
        sys.exit(1)

    if args.output:
        out_path = args.output
    else:
        out_path = str(config.AUDIO_DIR / md_path.with_suffix(".mp3").name)
    log(f"正在生成语音: {md_path.name} → {out_path}")
    log(f"  文本长度: {len(text)} 字符")

    success = generate_audio(text, out_path)
    if success:
        log(f"  语音生成成功: {out_path}")
        output_json({"success": True, "audio_file": str(Path(out_path).resolve())})
    else:
        log("  语音生成失败")
        output_json({"success": False, "error": "TTS generation failed"})
        sys.exit(1)


def cmd_generate(args):
    """Fetch transcript + generate blog with AI + optional TTS."""
    from youtube_blog_cli.blog_generator import generate_blog

    url = args.url

    # Step 1: Fetch transcript
    log(f"[1/3] 获取视频信息: {url}")
    info = get_video_info(url)
    if not info:
        log("无法获取视频信息，请检查链接")
        sys.exit(1)
    log(f"  标题: {info.get('title')}")
    log(f"  频道: {info.get('channel')}")

    log("[2/3] 获取视频字幕...")
    transcript = get_video_transcript(url)
    if not transcript:
        log("  未找到字幕，无法生成博客")
        sys.exit(1)
    log(f"  字幕长度: {len(transcript)} 字符")

    duration = info.get("duration", 0)
    transcript_data = {
        "title": info.get("title", ""),
        "channel": info.get("channel", ""),
        "duration_text": format_duration(duration),
        "length_guide": get_length_guide(duration),
        "transcript": transcript,
    }

    # Step 2: Generate blog
    log("[3/3] AI 生成博客...")
    blog_text = generate_blog(
        transcript_data,
        provider=args.provider,
        model=args.model,
    )

    if not blog_text:
        log("  博客生成失败")
        sys.exit(1)

    # Save blog
    if args.output:
        out_path = Path(args.output)
    else:
        safe_title = re.sub(r'[\\/*?:"<>|]', "", info.get("title", "blog"))[:80]
        out_path = config.BLOGS_DIR / f"{safe_title}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(blog_text, encoding="utf-8")
    log(f"  博客已保存: {out_path}")

    result = {
        "success": True,
        "blog_file": str(out_path.resolve()),
        "title": info.get("title", ""),
        "blog_length": len(blog_text),
    }

    # Step 3: Optional TTS
    if args.tts:
        audio_path = str(config.AUDIO_DIR / out_path.with_suffix(".mp3").name)
        log(f"  正在生成语音: {audio_path}")
        success = generate_audio(blog_text, audio_path)
        if success:
            log(f"  语音生成成功: {audio_path}")
            result["audio_file"] = str(Path(audio_path).resolve())
        else:
            log("  语音生成失败")

    output_json(result)


def cmd_prompt(args):
    """Output the blog generation prompt template, with length guide filled if --duration given."""
    duration = args.duration or 0
    template = load_prompt("blog")
    rendered = template.replace("{duration_text}", format_duration(duration))
    rendered = rendered.replace("{length_guide}", get_length_guide(duration))
    _real_print(rendered.strip())


# ── Main ─────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="youtube-blog",
        description="YouTube Blog CLI — YouTube 视频转博客工具，专为 Claude Code 设计",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
工作流 (配合 Claude Code):
  1. youtube-blog transcript <url>   → 获取字幕 (JSON)
  2. Claude Code 根据字幕生成博客文章，保存为 .md
  3. youtube-blog tts blog.md        → 将博客转为语音

工作流 (独立使用，需配置 API Key):
  youtube-blog generate <url> --tts  → 一键完成全流程
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # transcript
    p_trans = subparsers.add_parser("transcript", help="获取视频信息和字幕")
    p_trans.add_argument("url", help="YouTube 视频链接")
    p_trans.add_argument("--output", "-o", help="保存字幕到文件")

    # generate
    p_gen = subparsers.add_parser("generate", help="一键生成博客（需配置 AI API Key）")
    p_gen.add_argument("url", help="YouTube 视频链接")
    p_gen.add_argument("--output", "-o", help="博客输出路径 (默认 output/blogs/)")
    p_gen.add_argument("--provider", choices=["anthropic", "openai", "custom"],
                       help="AI 提供商 (默认从 .env 读取)")
    p_gen.add_argument("--model", help="模型名称 (可选，覆盖默认)")
    p_gen.add_argument("--tts", action="store_true", help="生成博客后自动转语音")

    # fetch-channel
    p_fetch = subparsers.add_parser("fetch-channel", help="获取频道视频列表")
    p_fetch.add_argument("url", help="YouTube 频道链接")
    p_fetch.add_argument("--count", type=int, default=5, help="获取数量 (默认 5)")

    # tts
    p_tts = subparsers.add_parser("tts", help="将 Markdown 文件转为语音")
    p_tts.add_argument("file", help="Markdown 文件路径")
    p_tts.add_argument("--output", "-o", help="输出音频路径 (默认同名 .mp3)")

    # prompt
    p_prompt = subparsers.add_parser("prompt", help="输出博客生成 prompt 模板")
    p_prompt.add_argument("--duration", type=int, default=0, help="视频时长(秒)，用于自适应篇幅建议")

    args = parser.parse_args()

    commands = {
        "transcript": cmd_transcript,
        "generate": cmd_generate,
        "fetch-channel": cmd_fetch_channel,
        "tts": cmd_tts,
        "prompt": cmd_prompt,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
