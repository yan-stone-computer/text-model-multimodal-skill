#!/usr/bin/env python3
"""
让文本模型拥有多模态的技能 — Agnes AI Media API Client
======================================
Unified CLI tool for Agnes AI API with automatic model fallback:
  - Image generation: agnes-image-2.1-flash (primary) -> agnes-image-2.0-flash (backup)
  - Video generation: agnes-video-v2.0 (official, https://www.agnes-ai.com/zh-Hans/docs/agnes-video-v20)
  - Vision: agnes-2.0-flash (primary) -> agnes-1.5-flash (backup)

If the primary model fails, the next free model is tried automatically.

Usage:
  python agnes_api.py <command> [options]

Commands:
  set-key       Save your Agnes AI API key to .env
  image         Generate image from text prompt (text-to-image)
  image-edit    Edit/transform existing image (image-to-image)
  video         Create video generation task (auto fallback v2.5 -> v2.0)
  video-status  Query video task status
  vision        Analyze/recognize image content (auto fallback 2.0 -> 1.5)

Config:
  API key is stored in {SKILL_ROOT}/.env file.
  Use 'set-key' command to save your key, then all other commands auto-read it.
"""

import sys
import os
import json
import time
import urllib.request
import urllib.error
import argparse
import base64
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://apihub.agnes-ai.com/v1"

# Model identifiers (primary -> backup order, all free during Agnes AI beta)
MODEL_IMAGE = "agnes-image-2.1-flash"
MODEL_IMAGE_ALT = "agnes-image-2.0-flash"
# Official video model per https://www.agnes-ai.com/zh-Hans/docs/agnes-video-v20
MODEL_VIDEO = "agnes-video-v2.0"
MODEL_VIDEO_ALT = "agnes-video-2.5"  # unofficial/experimental, only via --model
MODEL_VISION = "agnes-2.0-flash"
MODEL_VISION_ALT = "agnes-1.5-flash"

# Fallback lists (primary first; used when a model fails)
MODELS_IMAGE = [MODEL_IMAGE, MODEL_IMAGE_ALT]
# Video: only the officially documented v2.0 model (v2.5 has no official docs and failed in practice)
MODELS_VIDEO = [MODEL_VIDEO]
MODELS_VISION = [MODEL_VISION, MODEL_VISION_ALT]

# .env file location: same directory as this script
SCRIPT_DIR = Path(__file__).parent.resolve()
ENV_FILE = SCRIPT_DIR / ".env"


def _get_desktop_dir():
    """Get the real Desktop path (handles OneDrive redirection on Windows)."""
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "Desktop")
                expanded = os.path.expandvars(value)
                if expanded:
                    return Path(expanded)
        except Exception:
            pass
        profile = os.environ.get("USERPROFILE", str(Path.home()))
        return Path(profile) / "Desktop"
    return Path.home() / "Desktop"


def _get_output_dir():
    """Output directory: Desktop by default. Override with AGNES_OUTPUT_DIR."""
    env = os.environ.get("AGNES_OUTPUT_DIR")
    if env:
        return Path(env)
    return _get_desktop_dir()


# Output directory for downloaded media (default: Desktop)
OUTPUT_DIR = _get_output_dir()

# Retry settings
MAX_RETRIES = 5
RETRY_BACKOFF = [2, 5, 10, 20, 30]  # seconds to wait between retries


class APIError(Exception):
    """API request failed with a non-retryable error after all attempts."""
    def __init__(self, status, body, message=""):
        self.status = status          # HTTP status code, or "network"/"timeout"
        self.body = body              # parsed error dict (may contain _http_status)
        self.message = message or str(body)
        super().__init__(self.message)


def _read_env_file():
    """Read .env file and return dict of key=value pairs."""
    env = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    env[key.strip()] = val.strip()
    return env


def get_api_key():
    """Get API key from .env file, then env var, then ~/.agnes/config.json."""
    # 1. .env file (preferred)
    env = _read_env_file()
    key = env.get("AGNES_API_KEY", "")

    # 2. Environment variable
    if not key:
        key = os.environ.get("AGNES_API_KEY", "")

    # 3. Legacy config file
    if not key:
        config_path = Path.home() / ".agnes" / "config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    key = config.get("api_key", "")
            except Exception:
                pass

    if not key:
        print(json.dumps({
            "error": "API key not found. Please run: python agnes_api.py set-key sk-xxx",
            "hint": "Get a free API key at: https://platform.agnes-ai.com/settings/apiKeys",
            "get_key_url": "https://platform.agnes-ai.com/settings/apiKeys",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)
    return key


def get_base_url():
    env = _read_env_file()
    return env.get("AGNES_BASE_URL", os.environ.get("AGNES_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")


# ---------------------------------------------------------------------------
# .env management
# ---------------------------------------------------------------------------

def cmd_set_key(args):
    """Save API key to .env file."""
    key = args.api_key.strip()

    # Validate format (basic check)
    if not key:
        print(json.dumps({"error": "API key cannot be empty"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    # Read existing .env content
    existing = {}
    if ENV_FILE.exists():
        existing = _read_env_file()

    # Update / add key
    existing["AGNES_API_KEY"] = key

    # Write .env file
    lines = []
    lines.append("# Agnes AI API Configuration")
    lines.append("# This file is auto-generated by agnes_api.py set-key")
    lines.append("")
    for k, v in existing.items():
        lines.append(f"{k}={v}")

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(json.dumps({
        "success": True,
        "message": f"API key saved to {ENV_FILE}",
        "key_preview": key[:6] + "..." + key[-4:] if len(key) > 10 else "***",
    }, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# HTTP helpers with retry + model fallback
# ---------------------------------------------------------------------------

def _make_request(url, method="GET", headers=None, payload=None, timeout=300):
    """Make HTTP request with automatic retry (up to 5 attempts).

    Raises APIError on failure (instead of exiting), so callers can
    decide whether to fall back to another model.
    """
    if headers is None:
        headers = {}
    headers["Authorization"] = f"Bearer {get_api_key()}"
    if payload is not None and "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(body)
            except Exception:
                err_json = {"error": body}
            err_json["_http_status"] = e.code

            # 401 = auth error, no point retrying or switching models
            if e.code == 401:
                raise APIError(401, err_json)

            # 400 = bad request. Could be invalid params OR model-specific issue.
            # We retry it like transient errors so the caller can decide on fallback.
            if e.code == 400:
                # No point hammering; fail fast but let caller evaluate fallback.
                raise APIError(400, err_json)

            # 429 / 500 / 503 = retryable
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
                print(f"  [retry {attempt}/{MAX_RETRIES}] HTTP {e.code}, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                raise APIError(e.code, err_json)

        except urllib.error.URLError as e:
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
                print(f"  [retry {attempt}/{MAX_RETRIES}] Network error: {e.reason}, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                raise APIError("network", {"error": f"Network error: {e.reason}"})

        except Exception as e:
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
                print(f"  [retry {attempt}/{MAX_RETRIES}] Error: {e}, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                raise APIError("unknown", {"error": str(e)})

    # Should not reach here
    raise APIError("unknown", {"error": "Unknown error after retries"})


def _is_model_error(err):
    """Check if an API error suggests the model itself is unavailable (switch models)."""
    if err.status in ("network", "timeout", "unknown"):
        return True
    if err.status in (500, 502, 503, 429):
        return True
    if err.status == 404:
        return True
    if err.status == 400:
        # Model-related keywords in error message -> fall back to another model
        text = json.dumps(err.body, ensure_ascii=False).lower()
        model_hints = ("model", "not found", "does not exist", "unsupported",
                       "not supported", "no such", "invalid model", "unknown model",
                       "模型", "不存在", "不支持", "未找到")
        return any(h in text for h in model_hints)
    return False


def _try_models(model_list, build_payload, url_fn, method="POST", timeout=300):
    """Try models in order; fall back to the next one when a model fails.

    - 401 (auth): always fail immediately (switching models won't help).
    - 400 (param error, not model-related): fail immediately.
    - Other errors (429/500/503/network/model-not-found): try next model.
    """
    last_err = None
    total_models = len(model_list)

    for idx, model in enumerate(model_list):
        payload = build_payload(model)
        label = model_list[idx] if idx == 0 else f"{model} (fallback {idx})"
        try:
            result = _make_request(url_fn(), method=method, payload=payload, timeout=timeout)
            if isinstance(result, dict):
                result["model_used"] = model
            return result
        except APIError as e:
            last_err = e

            # Auth errors: never fall back
            if e.status == 401:
                print(json.dumps(e.body, ensure_ascii=False, indent=2))
                sys.exit(1)

            # Parameter errors that are NOT model-related: never fall back
            if e.status == 400 and not _is_model_error(e):
                print(json.dumps(e.body, ensure_ascii=False, indent=2))
                sys.exit(1)

            # Otherwise: try the next model
            print(f"  [model fallback {idx}/{total_models - 1}] {label} failed (HTTP {e.status}), trying next model...",
                  file=sys.stderr)
            # Small delay before switching models to be polite
            if idx < total_models - 1:
                time.sleep(1)

    # All models failed
    print(json.dumps({
        "error": "All models failed after fallback",
        "tried_models": model_list,
        "last_error": last_err.body if last_err else None,
    }, ensure_ascii=False, indent=2))
    sys.exit(1)


def _download_file(url, filepath):
    """Download a file from URL to local path (with retry)."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(filepath, "wb") as f:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
            return filepath
        except Exception as e:
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
                print(f"  [download retry {attempt}/{MAX_RETRIES}] {e}, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                raise


def _ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def _timestamp_str():
    return time.strftime("%Y%m%d_%H%M%S")


def _file_to_data_uri(filepath):
    """Convert a local file to a base64 data URI."""
    ext = Path(filepath).suffix.lower().lstrip(".")
    mime_map = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}
    mime = mime_map.get(ext, "image/png")
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


# ---------------------------------------------------------------------------
# Image generation (agnes-image-2.1-flash -> agnes-image-2.0-flash)
# ---------------------------------------------------------------------------

def _build_image_payload(args, model):
    """Build text-to-image payload for the given model."""
    payload = {
        "model": model,
        "prompt": args.prompt,
        "size": args.size,
    }
    if args.ratio:
        payload["ratio"] = args.ratio

    if args.return_base64:
        payload["return_base64"] = True
    else:
        payload["extra_body"] = {"response_format": "url"}

    return payload


def cmd_image(args):
    """Text-to-image generation with model fallback."""
    models = [args.model] if args.model else MODELS_IMAGE
    result = _try_models(
        models,
        lambda m: _build_image_payload(args, m),
        lambda: f"{get_base_url()}/images/generations",
        timeout=360,
    )

    if result.get("data") and len(result["data"]) > 0:
        item = result["data"][0]
        if item.get("url") and args.download:
            out_dir = _ensure_output_dir()
            filename = f"agnes_img_{_timestamp_str()}.png"
            filepath = out_dir / filename
            _download_file(item["url"], str(filepath))
            result["data"][0]["local_path"] = str(filepath)

    print(json.dumps(result, ensure_ascii=False, indent=2))


def _build_image_edit_payload(args, model):
    """Build image-to-image payload for the given model."""
    images = args.image.split(",") if isinstance(args.image, str) else args.image
    images = [img.strip() for img in images if img.strip()]

    processed_images = []
    for img in images:
        if os.path.isfile(img):
            processed_images.append(_file_to_data_uri(img))
        else:
            processed_images.append(img)

    payload = {
        "model": model,
        "prompt": args.prompt,
        "size": args.size,
        "extra_body": {
            "image": processed_images,
            "response_format": args.format,
        },
    }
    if args.ratio:
        payload["ratio"] = args.ratio

    return payload


def cmd_image_edit(args):
    """Image-to-image editing with model fallback."""
    models = [args.model] if args.model else MODELS_IMAGE
    result = _try_models(
        models,
        lambda m: _build_image_edit_payload(args, m),
        lambda: f"{get_base_url()}/images/generations",
        timeout=360,
    )

    if result.get("data") and len(result["data"]) > 0:
        item = result["data"][0]
        if item.get("url") and args.download:
            out_dir = _ensure_output_dir()
            filename = f"agnes_edit_{_timestamp_str()}.png"
            filepath = out_dir / filename
            _download_file(item["url"], str(filepath))
            result["data"][0]["local_path"] = str(filepath)
        elif item.get("b64_json") and args.download:
            out_dir = _ensure_output_dir()
            filename = f"agnes_edit_{_timestamp_str()}.png"
            filepath = out_dir / filename
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(item["b64_json"]))
            result["data"][0]["local_path"] = str(filepath)

    print(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Video generation (official agnes-video-v2.0)
# Docs: https://www.agnes-ai.com/zh-Hans/docs/agnes-video-v20
# ---------------------------------------------------------------------------

def _aspect_to_wh(aspect_ratio):
    """Map aspect ratio string to width/height (V2.0 uses width/height)."""
    default = (1152, 768)  # official recommended default
    mapping = {
        "16:9": (1280, 720),
        "9:16": (720, 1280),
        "1:1": (1024, 1024),
        "4:3": (1024, 768),
        "3:4": (768, 1024),
        "21:9": (1680, 720),
    }
    return mapping.get(aspect_ratio, default)


def _num_frames_for_seconds(seconds, frame_rate=24):
    """Official rule: num_frames must be <= 441 and follow 8n+1. Round up."""
    target = int(seconds) * frame_rate
    n = (target - 1 + 7) // 8
    nf = n * 8 + 1
    if nf > 441:
        nf = 441
    if nf < 9:
        nf = 9
    return nf


def _build_video_payload(args, model=MODEL_VIDEO):
    """Build agnes-video-v2.0 payload strictly per official docs.

    - Text-to-video: model + prompt + width + height + num_frames + frame_rate
    - Image-to-video: + image (single URL)
    - Keyframes: extra_body.image (array) + extra_body.mode = "keyframes"
    """
    payload = {
        "model": model,
        "prompt": args.prompt,
    }

    mode = args.mode or "text"

    if mode == "keyframe":
        # Official keyframes mode: extra_body.image array + extra_body.mode
        imgs = []
        if args.first_frame:
            imgs.append(args.first_frame)
        if args.last_frame:
            imgs.append(args.last_frame)
        if not imgs and args.images:
            imgs = [img.strip() for img in args.images.split(",") if img.strip()]
        payload["extra_body"] = {"image": imgs, "mode": "keyframes"}
    else:
        # text / image-to-video
        if args.images:
            # image-to-video: official field is `image` (single public URL)
            first_img = args.images.split(",")[0].strip()
            payload["image"] = first_img

    # Size: official width/height (aspect_ratio mapped to standard sizes)
    if args.aspect_ratio:
        w, h = _aspect_to_wh(args.aspect_ratio)
        payload["width"] = w
        payload["height"] = h
    else:
        payload["width"] = 1152
        payload["height"] = 768

    # Duration: official num_frames (8n+1) + frame_rate
    seconds = args.seconds or 5
    payload["num_frames"] = _num_frames_for_seconds(seconds)
    payload["frame_rate"] = 24

    if args.seed is not None:
        payload["seed"] = args.seed
    if args.negative_prompt:
        payload["negative_prompt"] = args.negative_prompt

    return payload


def _get_video_id(result):
    """Extract video_id from create-task response (official recommended ID)."""
    if result.get("video_id"):
        return result["video_id"]
    if result.get("id"):
        return result["id"]
    if result.get("task_id"):
        return result["task_id"]
    return None


def _video_status_url(video_id):
    """Official recommended status endpoint: GET /agnesapi?video_id=<ID>"""
    base = get_base_url()
    # /v1 -> root host, then /agnesapi?video_id=
    root = base.rsplit("/v1", 1)[0]
    return f"{root}/agnesapi?video_id={video_id}"


def cmd_video(args):
    """Create video generation task (official agnes-video-v2.0)."""
    models = [args.model] if args.model else MODELS_VIDEO
    result = _try_models(
        models,
        lambda m: _build_video_payload(args, m),
        lambda: f"{get_base_url()}/videos",
        timeout=60,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.wait:
        video_id = _get_video_id(result)
        if video_id:
            print(f"\n--- Polling video task: {video_id} ---", file=sys.stderr)
            final = _poll_video(video_id, interval=args.poll_interval, max_wait=args.max_wait)
            if final:
                print("\n--- Final Result ---", file=sys.stderr)
                video_url = final.get("url") or _extract_video_url(final)
                if video_url:
                    final["video_url"] = video_url
                if video_url and args.download:
                    out_dir = _ensure_output_dir()
                    filename = f"agnes_video_{_timestamp_str()}.mp4"
                    filepath = out_dir / filename
                    _download_file(video_url, str(filepath))
                    final["local_path"] = str(filepath)
                    print(f"\nVideo downloaded to: {filepath}", file=sys.stderr)
                # Keep model_used from create response if polling result lacks it
                if "model_used" in result and "model_used" not in final:
                    final["model_used"] = result["model_used"]
                print(json.dumps(final, ensure_ascii=False, indent=2))
        else:
            print("  [warn] No video_id in response, skipping polling.", file=sys.stderr)


def cmd_video_status(args):
    """Query video task status (official /agnesapi?video_id=<ID>)."""
    video_id = args.video_id
    url = _video_status_url(video_id)
    try:
        result = _make_request(url, method="GET", timeout=30)
    except APIError as e:
        print(json.dumps(e.body, ensure_ascii=False, indent=2))
        sys.exit(1)

    if result.get("status") == "completed":
        video_url = result.get("url") or _extract_video_url(result)
        if video_url:
            result["video_url"] = video_url
            if args.download:
                out_dir = _ensure_output_dir()
                filename = f"agnes_video_{_timestamp_str()}.mp4"
                filepath = out_dir / filename
                _download_file(video_url, str(filepath))
                result["local_path"] = str(filepath)

    print(json.dumps(result, ensure_ascii=False, indent=2))


def _extract_video_url(result):
    """Extract video URL from result (official: metadata.url on completion)."""
    if result.get("metadata") and result["metadata"].get("url"):
        return result["metadata"]["url"]
    if result.get("url"):
        return result["url"]
    if result.get("remixed_from_video_id") and str(result["remixed_from_video_id"]).startswith("http"):
        return result["remixed_from_video_id"]
    return None


def _poll_video(video_id, interval=3, max_wait=300):
    """Poll video task until completion or timeout (official endpoint)."""
    elapsed = 0
    while elapsed < max_wait:
        url = _video_status_url(video_id)
        try:
            result = _make_request(url, method="GET", timeout=30)
        except APIError as e:
            print(f"  [poll error] HTTP {e.status}: {e.message}", file=sys.stderr)
            time.sleep(interval)
            elapsed += interval
            continue

        status = result.get("status", "unknown")
        progress = result.get("progress", 0)
        print(f"  [{elapsed}s] status={status} progress={progress}%", file=sys.stderr)

        if status == "completed":
            return result
        elif status == "failed":
            print(f"  Task failed: {result.get('error', 'unknown error')}", file=sys.stderr)
            return result

        time.sleep(interval)
        elapsed += interval

    print(f"  Timeout after {max_wait}s", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Vision / image recognition (agnes-2.0-flash -> agnes-1.5-flash)
# ---------------------------------------------------------------------------

def _build_vision_payload(args, model):
    """Build chat-completions payload for the given model."""
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})

    user_content = [{"type": "text", "text": args.prompt}]

    images = args.image.split(",") if isinstance(args.image, str) else args.image
    for img in images:
        img = img.strip()
        if not img:
            continue
        if os.path.isfile(img):
            data_uri = _file_to_data_uri(img)
            user_content.append({"type": "image_url", "image_url": {"url": data_uri}})
        else:
            user_content.append({"type": "image_url", "image_url": {"url": img}})

    messages.append({"role": "user", "content": user_content})

    payload = {"model": model, "messages": messages}
    if args.temperature is not None:
        payload["temperature"] = args.temperature
    if args.max_tokens:
        payload["max_tokens"] = args.max_tokens
    # Thinking mode is only supported by 2.0-flash; drop it when falling back to 1.5
    if args.thinking and model == MODEL_VISION:
        payload["chat_template_kwargs"] = {"enable_thinking": True}

    return payload


def cmd_vision(args):
    """Analyze image content with model fallback (2.0 -> 1.5)."""
    models = [args.model] if args.model else MODELS_VISION
    result = _try_models(
        models,
        lambda m: _build_vision_payload(args, m),
        lambda: f"{get_base_url()}/chat/completions",
        timeout=120,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        description="让文本模型拥有多模态的技能 — Agnes AI Media API Client (image / video / vision, auto model fallback)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- set-key ---
    p_key = subparsers.add_parser("set-key", help="Save your Agnes AI API key to .env file")
    p_key.add_argument("api_key", help="Your API key (e.g. sk-xxxxx)")
    p_key.set_defaults(func=cmd_set_key)

    # --- image (text-to-image) ---
    p_img = subparsers.add_parser("image", help="Text-to-image generation (agnes-image-2.1-flash, fallback 2.0-flash)")
    p_img.add_argument("--prompt", "-p", required=True, help="Image description prompt")
    p_img.add_argument("--size", "-s", default="1024x1024", help="Output size: 1K/2K/3K/4K or WxH (default: 1024x1024)")
    p_img.add_argument("--ratio", "-r", help="Aspect ratio: 1:1, 3:4, 4:3, 16:9, 9:16, 2:3, 3:2, 21:9")
    p_img.add_argument("--model", "-m", help=f"Force model (default: auto fallback {MODEL_IMAGE} -> {MODEL_IMAGE_ALT})")
    p_img.add_argument("--return-base64", action="store_true", help="Return base64 instead of URL")
    p_img.add_argument("--download", "-d", action="store_true", help="Download image to local directory")
    p_img.set_defaults(func=cmd_image)

    # --- image-edit (image-to-image) ---
    p_edit = subparsers.add_parser("image-edit", help="Image editing/transformation (auto model fallback)")
    p_edit.add_argument("--prompt", "-p", required=True, help="Editing instruction")
    p_edit.add_argument("--image", "-i", required=True, help="Input image URL(s) or local path(s), comma-separated")
    p_edit.add_argument("--size", "-s", default="1024x1024", help="Output size (default: 1024x1024)")
    p_edit.add_argument("--ratio", "-r", help="Aspect ratio")
    p_edit.add_argument("--model", "-m", help=f"Force model (default: auto fallback {MODEL_IMAGE} -> {MODEL_IMAGE_ALT})")
    p_edit.add_argument("--format", "-f", default="url", choices=["url", "b64_json"], help="Response format (default: url)")
    p_edit.add_argument("--download", "-d", action="store_true", help="Download result to local directory")
    p_edit.set_defaults(func=cmd_image_edit)

    # --- video (official agnes-video-v2.0, docs: agnes-video-v20) ---
    p_vid = subparsers.add_parser("video", help="Create video generation task (official agnes-video-v2.0)")
    p_vid.add_argument("--prompt", "-p", required=True, help="Video content description")
    p_vid.add_argument("--mode", default="text", choices=["text", "keyframe"],
                       help="Generation mode: text / keyframe (default: text)")
    p_vid.add_argument("--seconds", type=int, default=5, help="Video duration in seconds -> num_frames (8n+1 rule), max ~18s (default: 5)")
    p_vid.add_argument("--aspect-ratio", help="Aspect ratio: 16:9, 9:16, 1:1, 4:3, 3:4, 21:9")
    p_vid.add_argument("--seed", type=int, help="Random seed for reproducibility")
    p_vid.add_argument("--negative-prompt", help="Negative prompt: what to avoid in the video")
    p_vid.add_argument("--model", "-m", help=f"Force model (default: {MODEL_VIDEO})")

    # keyframe mode params (official: extra_body.image + extra_body.mode="keyframes")
    p_vid.add_argument("--first-frame", help="First frame image URL (keyframe mode)")
    p_vid.add_argument("--last-frame", help="Last frame image URL (keyframe mode)")

    # image-to-video (official: `image` field, single public URL)
    p_vid.add_argument("--images", help="Input image URL for image-to-video (text mode) or keyframes (keyframe mode)")

    # polling options
    p_vid.add_argument("--wait", "-w", action="store_true", help="Auto-poll until task completes")
    p_vid.add_argument("--poll-interval", type=int, default=3, help="Poll interval in seconds (default: 3)")
    p_vid.add_argument("--max-wait", type=int, default=300, help="Max wait time in seconds (default: 300)")
    p_vid.add_argument("--download", "-d", action="store_true", help="Download video when completed")
    p_vid.set_defaults(func=cmd_video)

    # --- video-status (query task) ---
    p_status = subparsers.add_parser("video-status", help="Query video task status (official /agnesapi?video_id=<ID>)")
    p_status.add_argument("--video-id", "-v", required=True, help="Video task ID (use video_id from create response)")
    p_status.add_argument("--download", "-d", action="store_true", help="Download video if completed")
    p_status.set_defaults(func=cmd_video_status)

    # --- vision (image recognition) ---
    p_vis = subparsers.add_parser("vision", help="Analyze/recognize image content (agnes-2.0-flash, fallback 1.5-flash)")
    p_vis.add_argument("--prompt", "-p", required=True, help="Question or instruction about the image")
    p_vis.add_argument("--image", "-i", required=True, help="Image URL(s) or local path(s), comma-separated")
    p_vis.add_argument("--model", "-m", help=f"Force model (default: auto fallback {MODEL_VISION} -> {MODEL_VISION_ALT})")
    p_vis.add_argument("--system", "-s", help="System prompt")
    p_vis.add_argument("--temperature", type=float, help="Sampling temperature")
    p_vis.add_argument("--max-tokens", type=int, help="Max output tokens")
    p_vis.add_argument("--thinking", action="store_true", help="Enable thinking/reasoning mode (2.0-flash only)")
    p_vis.set_defaults(func=cmd_vision)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
