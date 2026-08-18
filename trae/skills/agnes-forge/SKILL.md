---
name: text-model-multimodal-skill
description: 让文本模型更伟大：让文本模型拥有多模态的技能，基于 Agnes AI API（当前免费）。当用户需要生成图片、编辑图片、生成视频、识别/分析图片内容，或希望给 DeepSeek、MiMo、GLM、Qwen、Kimi 等纯文本模型增加视觉与创作能力时使用。支持文生图、图生图、文生视频、图生视频、关键帧动画、图像识别。脚本零依赖，自动重试 5 次 + 模型自动降级（主模型不可用自动切换备用免费模型），兼容 OpenAI 接口。
---

# 让文本模型拥有多模态的技能

本技能让纯文本模型（DeepSeek、MiMo、GLM、Qwen、Kimi 等）获得多模态能力——生图、生视频、识图。通过一个零依赖的 Python 脚本接入 Agnes AI API（当前免费），提供三大能力：

| 能力 | 主模型 | 备用模型（自动降级） | 说明 |
|------|--------|---------------------|------|
| 生图 | `agnes-image-2.1-flash` | `agnes-image-2.0-flash` | 文生图、图生图编辑、多图组合 |
| 视频 | `agnes-video-v2.0`（官方） | —（仅官方模型） | 文生视频、图生视频、关键帧动画 |
| 识图 | `agnes-2.0-flash` | `agnes-1.5-flash` | 图像理解、OCR、图表分析、截图分析 |

**模型自动降级**：主模型不可用时（网络错误、429/500/503、模型不存在等），脚本自动切换到备用模型继续，无需用户干预。响应 JSON 带 `model_used` 字段标注实际使用的模型。可用 `--model` 参数强制指定模型。全部模型失败才报错。

## 描述

本技能将 Agnes AI 的多模态能力封装为简单的命令行操作，让 AI 智能体可以生成和编辑图片、生成视频、分析图像内容。所有模型在 beta 期间免费，无需信用卡。

## 使用场景

- 用户要求"生成/画/创建一张图" → 使用 `image` 命令
- 用户要求"把这张图改成 X 风格/编辑图片" → 使用 `image-edit` 命令
- 用户要求"生成一个视频" → 使用 `video` 命令
- 用户要求"描述/识别/分析这张图片" → 使用 `vision` 命令
- 用户提供了 Agnes AI 的 API Key → 使用 `set-key` 命令保存
- 用户提到 Agnes AI、生图、视频生成、图像识别等关键词

**不要使用本技能的场景：** 与图片/视频/图像分析无关的普通问答、代码编写、文档撰写等任务。

## 路径说明（重要）

本技能的核心脚本位于技能目录下的 `scripts/agnes_api.py`。调用前必须先解析出脚本的**绝对路径**，不能用相对路径，因为终端当前工作目录不一定是技能目录。

- 技能根目录：`SKILL.md` 所在目录，记为 `{SKILL_ROOT}`
- 脚本绝对路径：`{SKILL_ROOT}/scripts/agnes_api.py`

执行命令前，先确定 `{SKILL_ROOT}` 的真实值（即 `SKILL.md` 文件所在目录的完整路径），再执行。下文统一用 `python {SCRIPT}` 代指 `python {SKILL_ROOT}/scripts/agnes_api.py`。

## 指令

### 0. 使用前强制检查 API Key（必须执行）

**执行任何生图/生视频/识图命令之前，必须先检查 API Key 是否已配置：**

1. 检查 `scripts/.env` 中 `AGNES_API_KEY=` 是否已有值（`sk-xxx` 开头）
2. **若未配置** → **先停下来提醒用户**，不要直接执行命令：
   - 提醒用户：**「使用前需要先填写 Agnes AI 的 API Key（免费获取）。」**
   - 获取地址：**https://platform.agnes-ai.com/settings/apiKeys**
   - 用户提供 Key 后，执行 `set-key` 保存，再继续用户原本的请求
3. 若已配置 → 正常执行

### 0.1 保存 API Key

当用户提供 API Key 时，立即执行：

```bash
python {SCRIPT} set-key sk-用户的密钥
```

Key 自动写入 `scripts/.env`，后续所有命令自动读取，无需再传。

获取 API Key：https://platform.agnes-ai.com/settings/apiKeys（免费，无需信用卡）

### 1. 文生图

```bash
python {SCRIPT} image --prompt "图片描述" --size 2K --ratio 1:1 --download
```

- `--prompt`（必填）：图片描述，建议结构 `[主体]+[场景]+[风格]+[光线]+[构图]+[质量]`
- `--size`：`1K`/`2K`/`3K`/`4K` 或 `WxH`（默认 `1024x1024`）
- `--ratio`：`1:1`/`16:9`/`9:16`/`4:3`/`3:4`/`2:3`/`3:2`/`21:9`
- `--download`：下载到桌面（可用环境变量 `AGNES_OUTPUT_DIR` 自定义）

执行后提取返回 JSON 中的 `data[0].url` 或 `data[0].local_path` 展示给用户。

### 2. 图生图 / 图片编辑

```bash
python {SCRIPT} image-edit --prompt "编辑指令" --image "图片URL或本地路径" --download
```

- 支持多图：逗号分隔，如 `--image "a.jpg,b.jpg"`
- 本地图片自动转 base64，无需上传

### 3. 视频生成（异步，1-3 分钟，官方 agnes-video-v2.0）

严格按官方文档：https://www.agnes-ai.com/zh-Hans/docs/agnes-video-v20

```bash
# 文生视频
python {SCRIPT} video --prompt "视频描述" --mode text --seconds 5 --aspect-ratio 16:9 --wait --download

# 图生视频（官方 image 字段）
python {SCRIPT} video --prompt "描述哪些内容运动" --mode text --images "图片URL" --wait --download

# 关键帧动画（官方 extra_body.image + mode="keyframes"）
python {SCRIPT} video --prompt "过渡描述" --mode keyframe --first-frame "首帧URL" --last-frame "尾帧URL" --wait --download
```

- 必须加 `--wait` 自动轮询，`--download` 保存到本地
- `--seconds` 目标时长（默认 5，自动转 `num_frames`，遵循 8n+1 规则，最长约 18 秒）
- `--aspect-ratio` 支持 `16:9`/`9:16`/`1:1`/`4:3`/`3:4`/`21:9`（自动映射为 `width`/`height`）
- `--negative-prompt`：反向提示词，描述要避免的内容
- 关键帧模式官方字段：`extra_body.image`（数组）+ `extra_body.mode="keyframes"`

### 4. 图像识别

```bash
python {SCRIPT} vision --prompt "描述这张图片" --image "图片URL或本地路径"
```

- 支持多图：逗号分隔
- `--thinking`：启用深度推理（复杂分析）
- `--model agnes-1.5-flash`：速度优先

执行后提取 `choices[0].message.content` 回复用户。

> **💡 用户发图但你看不到？** 如果用户直接粘贴/拖入图片，而你是纯文本模型无法识别——**让用户改为提供图片的本地路径（如 `C:\Users\用户名\Desktop\照片.png`）或网址（如 `https://example.com/photo.png`）**，再用 `vision --image <路径或网址>` 识别。`image-edit`、`video --images` 同样支持路径/网址。

### 5. 查询视频任务状态

```bash
python {SCRIPT} video-status --video-id "video_xxx" --download
```

## 自动重试与模型降级机制

**第 1 层：请求重试（同一模型）**
- 可重试（429/500/503/网络超时）：指数退避 2s→5s→10s→20s→30s，最多 5 次
- 不可重试（401 认证失败、400 参数错误非模型相关）：立即失败

**第 2 层：模型降级（切换备用模型）**
- 当前模型重试 5 次仍失败，或错误与模型相关（不存在/不支持/404/500）→ 自动切换备用模型
- 生图：`agnes-image-2.1-flash` → `agnes-image-2.0-flash`
- 视频：仅官方 `agnes-video-v2.0`（`agnes-video-2.5` 无官方文档、实际请求失败，已弃用）
- 识图：`agnes-2.0-flash` → `agnes-1.5-flash`（降级自动关闭 Thinking）
- 备用模型也失败才向用户报错；响应带 `model_used` 字段

## 示例

用户：帮我生成一张猫的图片
AI：
```bash
python {SCRIPT} image --prompt "一只柴犬在樱花树下，水彩画风格，柔和晨光" --size 2K --download
```
→ 提取 `data[0].local_path` 展示图片

用户：这张图怎么描述的？
AI：
```bash
python {SCRIPT} vision --prompt "详细描述这张图片的内容" --image /path/to/image.jpg
```
→ 提取 `choices[0].message.content` 回复

## 注意事项

1. API Key 安全：`.env` 文件不应提交到公开仓库
2. 图片 URL 必须是公开可访问的 HTTPS URL
3. 视频 V2.0 官方规则：`num_frames` ≤441 且遵循 8n+1；图生视频用 `image` 字段，关键帧用 `extra_body.image` + `extra_body.mode="keyframes"`；状态查询用 `GET /agnesapi?video_id=<ID>`
4. 需要 Python 3.7+，纯标准库无需 pip install
5. 如果命令执行报"找不到脚本"，检查 `{SKILL_ROOT}` 路径是否解析正确

完整 API 参考见 `references/api-reference.md`
