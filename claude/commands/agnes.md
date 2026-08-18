---
description: Generate images, videos, or analyze images using Agnes AI
allowed-tools: Bash, Read
---

# 让文本模型拥有多模态的技能 Slash Command

Based on the user's request, use the 让文本模型拥有多模态的技能 CLI tool (`scripts/agnes_api.py`) to:

1. **Generate image:** `python scripts/agnes_api.py image --prompt "$ARGUMENTS" --size 2K --download`
2. **Edit image:** `python scripts/agnes_api.py image-edit --prompt "$ARGUMENTS" --image <path> --download`
3. **Generate video:** `python scripts/agnes_api.py video --prompt "$ARGUMENTS" --mode text --seconds 5 --wait --download`
4. **Analyze image:** `python scripts/agnes_api.py vision --prompt "$ARGUMENTS" --image <path>`

Parse the JSON output and present results. If no API key is set, ask user for it and run `python scripts/agnes_api.py set-key sk-xxx`.
