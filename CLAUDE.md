# 让文本模型拥有多模态的技能 — AI Media Generation (Claude Code)

You have access to 让文本模型拥有多模态的技能, a zero-dependency Python CLI tool for AI media generation via Agnes AI API.

## Setup (first time only)

**⚠️ MANDATORY CHECK before any command:** verify `scripts/.env` has `AGNES_API_KEY=sk-...` set. If NOT set, STOP and ask the user for their API key first, giving them: https://platform.agnes-ai.com/settings/apiKeys (free). Save it with:
```bash
python scripts/agnes_api.py set-key sk-USER_KEY
```
Get free key: https://platform.agnes-ai.com/settings/apiKeys

## Available Commands

### Generate Image
```bash
python scripts/agnes_api.py image --prompt "description" --size 2K --download
```
Options: `--prompt` (required), `--size` (1K/2K/3K/4K or WxH), `--ratio` (16:9/9:16/1:1/...), `--download`

### Edit Image
```bash
python scripts/agnes_api.py image-edit --prompt "instruction" --image photo.jpg --download
```
Supports local files and URLs. Multiple images: comma-separated.

### Generate Video (async, 1-3 min, official agnes-video-v2.0)
```bash
# Text to video
python scripts/agnes_api.py video --prompt "description" --mode text --seconds 5 --wait --download
# Image to video
python scripts/agnes_api.py video --prompt "description" --mode text --images photo.jpg --wait --download
# Keyframe animation
python scripts/agnes_api.py video --prompt "transition" --mode keyframe --first-frame a.jpg --last-frame b.jpg --wait --download
```
Modes: `text` / `keyframe`. Always use `--wait` to auto-poll. Always use `--download` to save locally.
Docs: https://www.agnes-ai.com/zh-Hans/docs/agnes-video-v20

### Analyze Image
```bash
python scripts/agnes_api.py vision --prompt "describe this image" --image photo.jpg
```
Supports `--thinking` for complex analysis, `--model agnes-1.5-flash` for speed.

> 💡 If the user pastes an image into chat and you (text-only model) cannot see it, ask the user to provide the image's **local path** or **public URL**, then run `vision --image <path-or-url>`.

## Workflow

1. User asks to generate/edit image → construct quality prompt → run `image`/`image-edit` → extract `data[0].url` or `data[0].local_path` → show result
2. User asks to generate video → construct prompt → run `video --wait --download` → extract `local_path` → show result
3. User asks to analyze image → run `vision` → extract `choices[0].message.content`
4. User provides API key → run `set-key` immediately → confirm saved

## Response Parsing

All commands output JSON to stdout. Key fields:
- Image: `data[0].url` or `data[0].local_path`
- Video: `video_url` or `local_path`
- Vision: `choices[0].message.content`

## Error Handling & Model Fallback

- 401/400 (non-model): fail immediately, tell user to check key/params
- 429/500/503/network: auto-retry 5x with exponential backoff (2s→5s→10s→20s→30s)
- After 5 failed retries or model-related errors, **auto-switches to backup model**:
  - Image: `agnes-image-2.1-flash` → `agnes-image-2.0-flash`
  - Video: official `agnes-video-v2.0` only (v2.5 deprecated — no official docs, failed in practice)
  - Vision: `agnes-2.0-flash` → `agnes-1.5-flash`
- Only report failure after ALL models fail
- Response includes `model_used` field; use `--model` to force a model

## Notes

- Pure Python stdlib, no pip install needed
- Local images auto-converted to base64
- Video V2.0 official rules: `num_frames` ≤441 & 8n+1; image-to-video uses `image` field; keyframes use `extra_body.image` + `extra_body.mode="keyframes"`; status via `GET /agnesapi?video_id=<ID>`
- Full docs: `AGENTS.md` and `references/api-reference.md`
