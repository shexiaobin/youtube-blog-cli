"""
AI Blog Generator — 调用 AI API 将视频字幕生成博客文章。
支持 Anthropic Claude / OpenAI GPT / 自定义 OpenAI 兼容 API。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from youtube_blog_cli import config


PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt_template() -> str:
    """Load and return the blog prompt template."""
    prompt_file = PROMPTS_DIR / "blog.md"
    return prompt_file.read_text(encoding="utf-8")


def _build_prompt(transcript_data: dict) -> str:
    """Fill the prompt template with transcript data."""
    template = _load_prompt_template()
    prompt = template.replace("{title}", transcript_data.get("title", ""))
    prompt = prompt.replace("{channel}", transcript_data.get("channel", ""))
    prompt = prompt.replace("{duration_text}", transcript_data.get("duration_text", ""))
    prompt = prompt.replace("{length_guide}", transcript_data.get("length_guide", ""))
    prompt = prompt.replace("{transcript}", transcript_data.get("transcript", ""))
    return prompt


def _generate_anthropic(prompt: str, model: Optional[str] = None) -> str:
    """Generate blog using Anthropic Claude API."""
    try:
        import anthropic
    except ImportError:
        print("请先安装 anthropic SDK: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    api_key = config.ANTHROPIC_API_KEY
    if not api_key:
        print("请设置 ANTHROPIC_API_KEY 环境变量", file=sys.stderr)
        sys.exit(1)

    model = model or config.AI_MODEL or "claude-sonnet-4-20250514"
    client = anthropic.Anthropic(api_key=api_key)

    print(f"  使用 Anthropic {model} 生成博客...", file=sys.stderr)
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _generate_openai(prompt: str, model: Optional[str] = None,
                     base_url: Optional[str] = None,
                     api_key: Optional[str] = None) -> str:
    """Generate blog using OpenAI or OpenAI-compatible API."""
    try:
        from openai import OpenAI
    except ImportError:
        print("请先安装 openai SDK: pip install openai", file=sys.stderr)
        sys.exit(1)

    api_key = api_key or config.OPENAI_API_KEY
    if not api_key:
        print("请设置 OPENAI_API_KEY 环境变量", file=sys.stderr)
        sys.exit(1)

    model = model or config.AI_MODEL or "gpt-4o"
    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    provider_name = base_url or "OpenAI"
    print(f"  使用 {provider_name} {model} 生成博客...", file=sys.stderr)

    client = OpenAI(**client_kwargs)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=8192,
    )
    return response.choices[0].message.content


def generate_blog(transcript_data: dict,
                  provider: Optional[str] = None,
                  model: Optional[str] = None) -> str:
    """
    Generate a blog post from transcript data using AI.

    Args:
        transcript_data: Dict with title, channel, duration_text, length_guide, transcript
        provider: AI provider — 'anthropic', 'openai', or 'custom' (default from config)
        model: Model name override (optional)

    Returns:
        Generated blog text in Markdown format
    """
    provider = provider or config.AI_PROVIDER
    prompt = _build_prompt(transcript_data)

    if provider == "anthropic":
        return _generate_anthropic(prompt, model)
    elif provider == "openai":
        return _generate_openai(prompt, model)
    elif provider == "custom":
        base_url = config.CUSTOM_API_BASE
        api_key = config.CUSTOM_API_KEY
        custom_model = model or config.CUSTOM_MODEL
        if not base_url:
            print("请设置 CUSTOM_API_BASE 环境变量（如 https://api.deepseek.com）", file=sys.stderr)
            sys.exit(1)
        if not api_key:
            print("请设置 CUSTOM_API_KEY 环境变量", file=sys.stderr)
            sys.exit(1)
        if not custom_model:
            print("请设置 CUSTOM_MODEL 环境变量（如 deepseek-chat）", file=sys.stderr)
            sys.exit(1)
        return _generate_openai(prompt, model=custom_model, base_url=base_url, api_key=api_key)
    else:
        print(f"不支持的 AI 提供商: {provider}，可选: anthropic / openai / custom", file=sys.stderr)
        sys.exit(1)
