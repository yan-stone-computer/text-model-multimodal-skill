---
name: text-model-multimodal-skill
title: "让文本模型拥有多模态的技能 - Image/Video/Vision"
description: "让文本模型更伟大：多模态觉醒工具。当用户需要生图（文生图/图生图）、生视频（文生视频/图生视频/关键帧动画）、识图（图像理解/OCR/图表分析），或希望给 DeepSeek 等纯文本模型增加视觉与创作能力时使用。接入 Agnes AI 免费 API，零依赖 Python 脚本，自动重试 5 次 + 模型自动降级。"
summary: "Agnes AI API skill for image generation, video generation, and image recognition. Supports agnes-image-2.1-flash, agnes-video-v2.0 (official), and agnes-2.0-flash vision. Auto-retry (5x) + model fallback. 100% free."
read_when:
  - User wants to generate images from text prompts
  - User wants to edit/transform existing images
  - User wants to generate videos (text-to-video, image-to-video, keyframe)
  - User wants to analyze/recognize/describe image content
  - User wants to give a text-only LLM (DeepSeek, MiMo, GLM, Qwen, Kimi...) multimodal abilities
  - User wants to use Agnes AI for any media generation or vision task
  - User mentions Agnes AI, agnes-image, agnes-video, or agnes-flash
  - User provides an Agnes AI API key and wants to save/use it
---

# 让文本模型拥有多模态的技能（让文本模型拥有多模态的技能 AI Media Skill）

接入 Agnes AI API，提供生图、视频生成、图像识别三大能力。兼容 OpenAI 接口格式，当前免费。
让 DeepSeek 等纯文本模型拥有眼睛与双手——多模态觉醒。

> **跨平台部署**：本 skill 同时支持 WorkBuddy、Claude Code、Cursor、Trae、Windsurf、GitHub Copilot、OpenCode。
> 各平台配置文件见仓库根目录：`AGENTS.md`（通用）、`CLAUDE.md`、`cursorrules`、`trae/rules/`、`windsurfrules`、`github/copilot-instructions.md`。
> 一键安装：`./install.sh --platform <平台名> [--api-key sk-xxx]`

## ⚠️ 使用前强制检查 API Key（必须执行）

**执行任何 `image` / `image-edit` / `video` / `video-status` / `vision` 命令之前，必须先检查 API Key 是否已配置。**

1. 检查 `{SKILL_ROOT}/scripts/.env` 文件中 `AGNES_API_KEY=` 后面是否已有值（`sk-xxx` 开头）
2. **若未配置** → **先停下来提醒用户**，不要直接执行命令：
   - 提醒语：**「使用前需要先填写 Agnes AI 的 API Key，请提供你的 API Key（免费获取）。」**
   - 告知获取地址：**https://platform.agnes-ai.com/settings/apiKeys**（注册即可免费获取，无需信用卡）
   - 用户提供 Key 后，用 `set-key` 命令保存，再继续执行用户原本的请求
3. **若已配置** → 正常执行用户请求

> 判断依据：`AGNES_API_KEY=sk-` 后面有内容 = 已配置；为空或整行缺失 = 未配置。
> 注意：不要向用户展示完整的已保存 Key，只显示前几位+后几位即可。

## 首次使用：保存 API Key

当用户提供 API Key 时，**立即**用 `set-key` 命令保存到 .env 文件，后续所有命令自动读取。

```bash
PYTHON SCRIPT set-key sk-用户的密钥
```

保存后无需再手动传 Key，脚本自动从 `{SKILL_ROOT}/scripts/.env` 读取。

**获取 API Key**：https://platform.agnes-ai.com/settings/apiKeys（免费，无需信用卡）

## 模型清单（主模型 + 自动降级备用）

| 能力 | 主模型 | 备用模型（自动降级） | 端点 |
|------|--------|---------------------|------|
| 生图 | `agnes-image-2.1-flash` | `agnes-image-2.0-flash` | `/v1/images/generations` |
| 视频 | `agnes-video-v2.0`（官方） | —（仅官方模型） | `/v1/videos` |
| 识图 | `agnes-2.0-flash` | `agnes-1.5-flash` | `/v1/chat/completions` |

**模型自动降级**：主模型不可用时（网络错误、429/500/503、模型不存在等），脚本**自动切换到备用模型**继续，无需用户干预。响应 JSON 中带 `model_used` 字段标注实际使用的模型。可用 `--model` 参数强制指定某个模型。全部模型失败才报错。

## 脚本位置

```
{SKILL_ROOT}/scripts/agnes_api.py    # 主脚本
{SKILL_ROOT}/scripts/.env            # API Key 存储（自动生成）
```

下文用 `PYTHON` 代指 Python 解释器路径，`SCRIPT` 代指脚本绝对路径。

## 能力一：生图（agnes-image-2.1-flash）

### 文生图

```bash
PYTHON SCRIPT image --prompt "描述文字" --size "1024x1024" --download
```

**参数：**
- `--prompt` (必填): 图片描述，支持中英文
- `--size`: 输出尺寸 `1K`/`2K`/`3K`/`4K` 或 `WxH`（默认 `1024x1024`）
- `--ratio`: 宽高比 `1:1`/`3:4`/`4:3`/`16:9`/`9:16`/`2:3`/`3:2`/`21:9`
- `--return-base64`: 返回 base64 而非 URL
- `--download`: 下载到桌面（可用环境变量 `AGNES_OUTPUT_DIR` 自定义）

**尺寸参考：**

| 比例 | 1K | 2K | 4K |
|------|-----|-----|-----|
| 1:1 | 1024×1024 | 2048×2048 | 4096×4096 |
| 16:9 | 1312×736 | 2624×1472 | 5248×2944 |
| 9:16 | 736×1312 | 1472×2624 | 2944×5248 |

**提示词结构：** `[主体] + [场景/背景] + [风格] + [光线] + [构图] + [质量要求]`

### 图生图 / 图片编辑

```bash
PYTHON SCRIPT image-edit --prompt "编辑指令" --image "图片URL或本地路径" --size "1024x1024" --download
```

**参数：**
- `--prompt` (必填): 编辑/变换指令
- `--image` (必填): 输入图片 URL 或本地路径，多图逗号分隔
- `--size`: 输出尺寸
- `--format`: `url` 或 `b64_json`（默认 `url`）
- `--download`: 下载结果到本地

**注意：**
- 输入图片支持公网 URL 和本地文件路径（自动转 base64）
- `response_format` 已由脚本放入 `extra_body`，无需手动处理
- 多图合成时在 prompt 中描述各图的组合关系

## 能力二：视频生成（agnes-video-v2.0，官方文档）

严格按官方文档实现（https://www.agnes-ai.com/zh-Hans/docs/agnes-video-v20）。支持 `text`（文生视频/图生视频）、`keyframe`（关键帧动画）两种模式。异步任务，创建后轮询。

### 文生视频

```bash
PYTHON SCRIPT video --prompt "视频描述" --mode text --seconds 5 --aspect-ratio 16:9 --wait --download
```

### 图生视频

```bash
PYTHON SCRIPT video --prompt "描述哪些内容运动" --mode text --images "图片URL" --wait --download
```

### 关键帧动画

```bash
PYTHON SCRIPT video --prompt "关键帧之间的过渡描述" --mode keyframe --first-frame "首帧URL" --last-frame "尾帧URL" --wait --download
```

**通用参数：**
- `--prompt` (必填): 视频内容描述
- `--mode`: `text`/`keyframe`（默认 `text`）
- `--seconds`: 目标时长（默认 5，自动转 `num_frames`，遵循 8n+1 规则，最长约 18 秒）
- `--aspect-ratio`: `16:9`/`9:16`/`1:1`/`4:3`/`3:4`/`21:9`（自动映射为 `width`/`height`）
- `--seed`: 随机种子（可复现结果）
- `--negative-prompt`: 反向提示词，描述要避免的内容

**模式专用参数：**

| 模式 | 专用参数 | 官方字段 |
|------|---------|---------|
| `text`（图生视频） | `--images` | `image`（单张公开图片 URL） |
| `keyframe` | `--first-frame` / `--last-frame` | `extra_body.image`（数组）+ `extra_body.mode="keyframes"` |

### 查询视频状态

视频生成是异步任务。加 `--wait` 自动轮询，或手动查询（官方推荐端点）：

```bash
PYTHON SCRIPT video-status --video-id "video_xxx" --download
```

**画幅与像素（`width`/`height`）：**

| aspect_ratio | 输出像素 | 推荐场景 |
|-------------|---------|---------|
| 16:9 | 1280×720 | 横版视频（默认 1152×768） |
| 9:16 | 720×1280 | 移动端短视频 |
| 1:1 | 1024×1024 | 社交媒体 |
| 4:3 | 1024×768 | 传统横版 |
| 3:4 | 768×1024 | 竖版展示 |
| 21:9 | 1680×720 | 超宽银幕 |

**时长控制（官方规则）：** `seconds = num_frames / frame_rate`，`num_frames` 必须 ≤441 且遵循 8n+1。推荐：约 3 秒=81 帧、约 5 秒=121 帧、约 10 秒=241 帧、约 18 秒=441 帧（帧率 24）。

## 能力三：图像识别（agnes-2.0-flash）

使用多模态聊天接口分析图片内容。支持本地图片和 URL。

```bash
PYTHON SCRIPT vision --prompt "描述这张图片" --image "图片URL或本地路径"
```

**参数：**
- `--prompt` (必填): 关于图片的问题或指令
- `--image` (必填): 图片 URL 或本地路径，多图逗号分隔
- `--model`: 默认 `agnes-2.0-flash`，也支持 `agnes-1.5-flash`（速度优先）
- `--system`: 系统提示词
- `--temperature`: 采样温度
- `--max-tokens`: 最大输出 token 数
- `--thinking`: 启用 Thinking 推理模式（适合复杂分析）

**识图能力：** 截图分析、图像描述、视觉问答、信息提取与结构化、OCR、图表理解等。

> **💡 遇到「智能体无法识别图片」怎么办？**
> 如果用户直接把图片**粘贴或拖进对话**，而当前智能体（如 DeepSeek 等纯文本模型）提示「无法查看/识别图片」——**不要放弃，改用下面两种方式**：
> 1. **图片本地路径**：让用户提供图片的文件路径（如 `C:\Users\用户名\Desktop\照片.png`）
> 2. **图片网址**：让用户提供图片的公网 URL（如 `https://example.com/photo.png`）
>
> 拿到路径或网址后，用 `vision --image <路径或网址>` 即可正常识别图片内容（脚本自动处理本地路径转 base64）。生图编辑（`image-edit`）、图生视频（`video --images`）同样支持路径/网址方式绕过智能体无法直接看图的问题。

## 自动重试与模型降级机制

所有 API 请求自带 **5 次重试 + 模型自动降级**：

**第 1 层：请求重试（同一模型）**
- **可重试错误**（429 频率限制、500 服务器错误、503 服务繁忙、网络超时）：自动等待后重试
  - 重试间隔：2s → 5s → 10s → 20s → 30s（指数退避）
- **立即失败**（401 认证失败、400 参数错误非模型相关）：不重试、不降级

**第 2 层：模型降级（切换备用模型）**
- 当前模型重试 5 次仍失败，或报错与模型相关（模型不存在/不支持/404/500）→ **自动切换备用模型**：
  - 生图：`agnes-image-2.1-flash` → `agnes-image-2.0-flash`
  - 识图：`agnes-2.0-flash` → `agnes-1.5-flash`（降级时自动关闭 Thinking）
  - 视频：仅官方 `agnes-video-v2.0`（此前 `agnes-video-2.5` 无官方文档、实际请求失败，已弃用）
- 备用模型也失败才向用户报错
- 响应 JSON 带 `model_used` 字段标注实际使用的模型

## 工作流程指南

### 用户首次提供 API Key
1. 执行 `set-key` 命令保存到 .env
2. 告知用户已保存成功，后续无需再传

### 生成图片
1. 确认需求（文生图/图生图，尺寸比例）
2. 构造高质量 prompt
3. 执行 `image` 或 `image-edit`，加 `--download`
4. 提取返回 JSON 中的 `data[0].url` 或 `data[0].local_path`
5. 用 `present_files` 展示图片

### 生成视频
1. 确认需求（text 文生视频/图生视频，或 keyframe 关键帧动画）
2. 构造 prompt（官方结构：[主体]+[动作]+[场景]+[镜头运动]+[光线]+[风格]）
3. 执行 `video`，加 `--wait --download`
4. 视频生成通常 1-3 分钟，告知用户耐心等待
5. 完成后用 `present_files` 展示视频
5. 完成后用 `present_files` 展示视频

### 识别图片
1. 获取图片（URL 或本地路径）
2. 构造分析指令
3. 执行 `vision` 命令
4. 提取 `choices[0].message.content` 回复用户

## 重要注意事项

1. **API Key 安全**：.env 文件不应提交到公开仓库，输出中不暴露完整 Key
2. **图片 URL**：必须是公开可访问的 HTTPS URL
3. **本地图片**：脚本自动转 base64 Data URI
4. **视频生成**：异步任务，`--wait` 自动轮询，默认超时 300 秒；最终视频 URL 在 `metadata.url`
5. **官方 V2.0 规则**：`num_frames` ≤441 且遵循 8n+1；图生视频用 `image` 字段，关键帧用 `extra_body.image` + `extra_body.mode="keyframes"`；状态查询用 `GET /agnesapi?video_id=<ID>`
6. **视频状态查询**：创建响应中的 `video_id` 是官方推荐 ID，优先使用

## 错误处理

| HTTP 状态码 | 原因 | 是否重试 | 处理方式 |
|------------|------|---------|---------|
| 400 | 参数错误 | 否 | 检查请求参数和模式匹配 |
| 401 | API Key 无效 | 否 | 重新执行 `set-key` |
| 404 | 任务不存在 | 否 | 确认 video_id 正确 |
| 429 | 频率限制 | 是 | 自动退避重试 |
| 500 | 服务器错误 | 是 | 自动重试 |
| 503 | 服务繁忙 | 是 | 自动重试 |
| 网络超时 | 网络问题 | 是 | 自动重试 |
