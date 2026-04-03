# YouTube Blog CLI

将 YouTube 视频转化为高质量博客文章的命令行工具。

支持两种使用方式：
- **配合 Claude Code** — AI 写作由 Claude Code 完成，无需配置 API Key
- **独立使用** — 配置 AI API Key 后，一条命令完成全流程

## 工作流

```
YouTube URL → 字幕提取 → AI 生成博客 → TTS 语音合成
```

## 功能特性

- **AI 博客生成**：支持 Anthropic Claude / OpenAI / 自定义 API（DeepSeek、Ollama 等）
- **字幕提取**：YouTube 字幕 API → yt-dlp → Whisper 转录，多级降级
- **TTS 语音合成**：Edge TTS（免费）/ OpenAI TTS
- **自适应篇幅**：根据视频时长自动调整博客长度
- **NotebookLM 风格**：内置双角色深度解析写作模板
- **结构化输出**：进度 → stderr，JSON → stdout，适合程序化调用

## 安装

```bash
# 1. 克隆项目
git clone https://github.com/yourname/youtube-blog-cli.git
cd youtube-blog-cli

# 2. 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate   # macOS / Linux
# venv\Scripts\activate    # Windows

# 3. 安装（基础）
pip install -e .

# 4. 安装 AI 提供商 SDK（按需选择）
pip install -e ".[anthropic]"  # 使用 Anthropic Claude
pip install -e ".[openai]"    # 使用 OpenAI 或 OpenAI TTS
pip install -e ".[all]"       # 全部可选依赖
```

### 配置 API Key

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```bash
# 方式一：使用 Anthropic Claude（推荐）
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxx

# 方式二：使用 OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=sk-xxx

# 方式三：使用自定义 OpenAI 兼容 API（DeepSeek、Ollama 等）
AI_PROVIDER=custom
CUSTOM_API_BASE=https://api.deepseek.com
CUSTOM_API_KEY=sk-xxx
CUSTOM_MODEL=deepseek-chat
```

> 如果只配合 Claude Code 使用，无需配置任何 API Key。

## 使用方法

### 一键生成博客（独立使用）

```bash
# 生成博客
youtube-blog generate "https://www.youtube.com/watch?v=VIDEO_ID"

# 生成博客 + 语音
youtube-blog generate "https://www.youtube.com/watch?v=VIDEO_ID" --tts

# 指定 AI 提供商和模型
youtube-blog generate "https://www.youtube.com/watch?v=VIDEO_ID" --provider openai --model gpt-4o

# 指定输出路径
youtube-blog generate "https://www.youtube.com/watch?v=VIDEO_ID" -o my-blog.md --tts
```

### 配合 Claude Code 使用

在项目目录下启动 Claude Code，直接说：

```
帮我把这个视频写成博客：https://www.youtube.com/watch?v=xxx
```

Claude Code 会自动读取 `CLAUDE.md`，调用 CLI 获取字幕、生成博客、合成语音。

### 其他命令

```bash
# 获取视频字幕（JSON 输出）
youtube-blog transcript "https://www.youtube.com/watch?v=VIDEO_ID"

# 获取频道视频列表
youtube-blog fetch-channel "https://www.youtube.com/@channel" --count 5

# Markdown 转语音
youtube-blog tts blog.md -o blog.mp3

# 查看写作 Prompt 模板
youtube-blog prompt --duration 600
```

## 项目结构

```
youtube-blog-cli/
├── youtube_blog_cli/        # Python 包
│   ├── cli.py               # CLI 主入口
│   ├── blog_generator.py    # AI 博客生成（Anthropic/OpenAI/自定义）
│   ├── config.py            # 配置管理
│   ├── youtube_fetcher.py   # YouTube 数据抓取 & 字幕提取
│   ├── transcriber.py       # 音频转文字（Whisper / Groq）
│   ├── tts_engine.py        # 语音合成（Edge TTS / OpenAI）
│   └── prompts/blog.md      # 博客生成 prompt 模板
├── pyproject.toml           # 包配置 & 依赖
├── .env.example             # 环境变量模板
├── CLAUDE.md                # Claude Code 项目说明
└── README.md
```

## License

[MIT](LICENSE)
