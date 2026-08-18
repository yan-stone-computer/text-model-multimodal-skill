# 让文本模型拥有多模态的技能 — AI Media Generation Toolkit

> Generate images, videos, and analyze images with Agnes AI. Zero dependencies. Free API.

## What This Tool Does

让文本模型拥有多模态的技能 wraps the [Agnes AI](https://platform.agnes-ai.com) API into a single Python CLI script with three capabilities:

1. **Image Generation** (`agnes-image-2.1-flash`, fallback `agnes-image-2.0-flash`) — Text-to-image, image-to-image editing, multi-image composition
2. **Video Generation** (`agnes-video-v2.0` — official, see agnes-video-v20 docs) — Text-to-video, image-to-video, keyframe animation
3. **Image Recognition** (`agnes-2.0-flash`, fallback `agnes-1.5-flash`) — Visual understanding, OCR, chart analysis, screenshot analysis

All models are currently **free** during the Agnes AI beta.

**Automatic model fallback:** If a primary model fails, the script automatically retries with the backup model — no user action needed. The response JSON includes a `model_used` field showing which model actually served the request. Use `--model <id>` to force a specific model.

## Setup

### ⚠️ MANDATORY — Check API Key BEFORE running any command

**Before executing any `image` / `image-edit` / `video` / `video-status` / `vision` command, you MUST first check whether an API key is configured:**

1. Check if `scripts/.env` has `AGNES_API_KEY=` set to a non-empty value (starts with `sk-`)
2. **If NOT configured** → **STOP and ask the user for their API key first** — do NOT run the command:
   - Tell the user: **"Please provide your Agnes AI API key to continue (free to get)."**
   - Give them the URL: **https://platform.agnes-ai.com/settings/apiKeys**
   - Once the user provides the key, save it with `set-key`, then continue with the user's original request
3. **If configured** → proceed normally

> Never show the full saved key back to the user — only a preview (first 6 + last 4 chars).

### Step 1: Get API Key

Register at [platform.agnes-ai.com](https://platform.agnes-ai.com/settings/apiKeys) → API Keys → Create (free, no credit card).

### Step 2: Save API Key

```bash
python scripts/agnes_api.py set-key sk-your-api-key-here
```

The key is stored in `scripts/.env` and auto-loaded by all commands. Never need to pass it again.

### Step 3: Verify

```bash
python scripts/agnes_api.py image --prompt "a cute cat" --size 1K --download
```

If you get a JSON response with a URL, you're good.

---

## Command Reference

### `set-key` — Save API Key

```bash
python scripts/agnes_api.py set-key sk-xxxxxxxx
```

Stores the key in `scripts/.env`. All subsequent commands auto-read it.

### `image` — Text-to-Image

```bash
python scripts/agnes_api.py image --prompt "描述" [options]
```

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--prompt, -p` | string | Image description (required) | — |
| `--size, -s` | string | `1K`/`2K`/`3K`/`4K` or `WxH` | `1024x1024` |
| `--ratio, -r` | string | `1:1`/`16:9`/`9:16`/`4:3`/`3:4`/`2:3`/`3:2`/`21:9` | — |
| `--return-base64` | flag | Return base64 instead of URL | false |
| `--download, -d` | flag | Download to your Desktop | false |

**Size reference:**

| Ratio | 1K | 2K | 4K |
|-------|------|------|------|
| 1:1 | 1024² | 2048² | 4096² |
| 16:9 | 1312×736 | 2624×1472 | 5248×2944 |
| 9:16 | 736×1312 | 1472×2624 | 2944×5248 |

### `image-edit` — Image-to-Image

```bash
python scripts/agnes_api.py image-edit --prompt "编辑指令" --image photo.jpg [options]
```

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--prompt, -p` | string | Edit instruction (required) | — |
| `--image, -i` | string | Input image URL or local path, comma-separated (required) | — |
| `--size, -s` | string | Output size | `1024x1024` |
| `--format, -f` | string | `url` or `b64_json` | `url` |
| `--download, -d` | flag | Download result | false |

Local images are auto-converted to base64. No manual upload needed.

### `video` — Video Generation (official `agnes-video-v2.0`)

Strictly follows the official docs: https://www.agnes-ai.com/zh-Hans/docs/agnes-video-v20

Two modes: `text` (text-to-video / image-to-video), `keyframe` (keyframe animation).

```bash
# Text to video
python scripts/agnes_api.py video --prompt "描述" --mode text --seconds 5 --aspect-ratio 16:9 --wait --download

# Image to video (official `image` field)
python scripts/agnes_api.py video --prompt "描述哪些内容运动" --mode text --images photo.jpg --wait --download

# Keyframe animation (official extra_body.image + extra_body.mode="keyframes")
python scripts/agnes_api.py video --prompt "过渡描述" --mode keyframe --first-frame start.jpg --last-frame end.jpg --wait --download
```

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--prompt, -p` | string | Video description (required) | — |
| `--mode` | string | `text` / `keyframe` | `text` |
| `--seconds` | int | Target duration → `num_frames` (8n+1 rule, max ~18s) | `5` |
| `--aspect-ratio` | string | `16:9`/`9:16`/`1:1`/`4:3`/`3:4`/`21:9` → `width`/`height` | `1152x768` |
| `--seed` | int | Random seed | — |
| `--negative-prompt` | string | What to avoid in the video | — |
| `--wait, -w` | flag | Auto-poll until complete | false |
| `--download, -d` | flag | Download video when done | false |

**Mode-specific options:**

| Mode | Options | Official field |
|------|---------|----------------|
| `text` (image-to-video) | `--images` | `image` (single public URL) |
| `keyframe` | `--first-frame`, `--last-frame` | `extra_body.image` + `extra_body.mode="keyframes"` |

**Aspect ratio → pixels (`width`/`height`):**

| Ratio | Pixels | Use case |
|-------|--------|----------|
| 16:9 | 1280×720 | Landscape video |
| 9:16 | 720×1280 | Mobile short video |
| 1:1 | 1024×1024 | Social media |
| 4:3 | 1024×768 | Traditional landscape |
| 3:4 | 768×1024 | Portrait |
| 21:9 | 1680×720 | Ultrawide cinematic |

**Duration (official rule):** `seconds = num_frames / frame_rate`, `num_frames` ≤ 441 and must follow `8n+1`. Recommended: ~3s=81, ~5s=121, ~10s=241, ~18s=441 frames @24fps.

### `video-status` — Query Video Task

Uses the official recommended endpoint `GET /agnesapi?video_id=<ID>`:

```bash
python scripts/agnes_api.py video-status --video-id video_xxx [--download]
```

### `vision` — Image Recognition

```bash
python scripts/agnes_api.py vision --prompt "描述这张图片" --image photo.jpg [options]
```

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--prompt, -p` | string | Question or instruction (required) | — |
| `--image, -i` | string | Image URL or local path, comma-separated (required) | — |
| `--model, -m` | string | `agnes-2.0-flash` or `agnes-1.5-flash` | `agnes-2.0-flash` |
| `--system, -s` | string | System prompt | — |
| `--temperature` | float | Sampling temperature | — |
| `--max-tokens` | int | Max output tokens | — |
| `--thinking` | flag | Enable deep reasoning mode | false |

> **💡 User sent an image but your model can't see it?** If the user pastes or drags an image into chat and your (text-only) model says it cannot view images, ask the user to instead provide the image's **local file path** (e.g. `C:\Users\you\Desktop\photo.png`) or a **public URL** (e.g. `https://example.com/photo.png`), then run `vision --image <path-or-url> --prompt "..."` to analyze it. The same path/URL trick also works for `image-edit` and `video --images`.

---

## Auto-Retry & Model Fallback

**Layer 1 — Request retry (same model):**
- **Retryable:** 429 (rate limit), 500 (server error), 503 (service busy), network timeout
- **Not retryable:** 401 (auth failed), 400 (bad request, non-model) — fail immediately
- **Backoff:** 2s → 5s → 10s → 20s → 30s (exponential)
- **Max attempts:** 5 — only after all 5 fail does the tool report an error

**Layer 2 — Model fallback (switch to backup model):**
- After 5 failed retries, or when the error is model-related (not found/unsupported/404/500), the script automatically switches to the backup free model:
  - Image: `agnes-image-2.1-flash` → `agnes-image-2.0-flash`
  - Video: official `agnes-video-v2.0` only (v2.5 had no official docs and failed in practice)
  - Vision: `agnes-2.0-flash` → `agnes-1.5-flash` (thinking disabled on 1.5)
- Only when **all** models fail does the tool report an error
- Response JSON includes `model_used` field

---

## Response Format

All commands output JSON to stdout. Progress/status messages go to stderr. Parse stdout for results:

```json
{
  "created": 1780000000,
  "data": [
    {
      "url": "https://storage.googleapis.com/agnes-aigc/xxx.png",
      "local_path": "C:/Users/you/Desktop/agnes_img_20260818_000000.png"
    }
  ]
}
```

Key fields to extract:
- **Image:** `data[0].url` or `data[0].local_path` (if `--download`)
- **Video:** `video_url` or `local_path` (if `--download`)
- **Vision:** `choices[0].message.content`

---

## Prompt Tips

### Image Generation
```
[Subject] + [Scene/Background] + [Style] + [Lighting] + [Composition] + [Quality]
```
Example: *"A golden retriever puppy under cherry blossom trees, watercolor painting style, soft morning light, close-up portrait, ultra-detailed"*

### Video Generation
Be specific about motion, camera angle, and mood. Use reference placeholders for multi-modal inputs.

Example: *"A cat slowly walks along a sunny beach, gentle waves lapping at its paws, warm golden hour light, camera tracking shot from behind"*

---

## Important Notes

1. **API Key security:** `scripts/.env` is gitignored. Never commit it.
2. **Image URLs:** Must be publicly accessible HTTPS URLs.
3. **Local images:** Auto-converted to base64 Data URI internally.
4. **Video generation:** Async task. Use `--wait` to auto-poll (default timeout 300s).
5. **V2.5 limits:** `size` must be `"720P"`, `n` fixed at 1, `seconds` range 4-12.
6. **Python:** Requires Python 3.7+. No pip install needed — pure standard library.

---

## API Configuration

| Item | Value |
|------|-------|
| Base URL | `https://apihub.agnes-ai.com/v1` |
| Auth | `Authorization: Bearer YOUR_API_KEY` |
| Protocol | OpenAI v1 compatible |
| Get API Key | [platform.agnes-ai.com](https://platform.agnes-ai.com) |

Full API reference: [`references/api-reference.md`](references/api-reference.md)
