# YouTube Blog CLI — Claude Code 使用说明

这是一个配合 Claude Code 使用的 YouTube 视频转博客工具。你（Claude Code）负责 AI 写作，CLI 负责数据抓取和语音合成。

## 快速工作流

当用户给你一个 YouTube 链接并要求生成博客时：

### 第 1 步：获取字幕
```bash
youtube-blog transcript "VIDEO_URL" 2>/dev/null
```
返回 JSON，包含 `title`、`channel`、`duration_text`、`length_guide`、`transcript`。

### 第 2 步：获取 Prompt 模板
```bash
youtube-blog prompt --duration SECONDS 2>/dev/null
```
返回博客写作模板，其中 `{title}`、`{channel}`、`{transcript}` 等占位符需要用第 1 步的数据填充。

### 第 3 步：生成博客
用你的 AI 能力，将字幕内容按 prompt 模板撰写博客文章。保存到 `output/blogs/` 目录。

### 第 4 步：生成语音（可选）
```bash
youtube-blog tts output/blogs/FILENAME.md
```
音频输出到 `output/audio/`。

## 命令参考

| 命令 | 用途 | 输出 |
|------|------|------|
| `transcript <url>` | 获取视频信息 + 字幕 | JSON (stdout) |
| `generate <url> [--tts]` | 一键 AI 生成博客（需 API Key） | JSON (stdout) |
| `fetch-channel <url> [--count N]` | 获取频道视频列表 | JSON (stdout) |
| `tts <file> [-o path]` | Markdown 转语音 | JSON (stdout) |
| `prompt [--duration N]` | 输出 prompt 模板 | 文本 (stdout) |

## 注意事项

- 所有命令的进度信息输出到 stderr，结构化结果输出到 stdout
- 使用 `2>/dev/null` 过滤进度信息，只获取 JSON 结果
- 需先安装：`pip install -e .`（安装后可用 `youtube-blog` 命令）
- 无字幕视频会自动下载音频并用 Whisper 转录，耗时较长
