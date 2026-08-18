# Agnes AI API 完整参考

## 基础配置

| 项目 | 值 |
|------|-----|
| Base URL | `https://apihub.agnes-ai.com/v1` |
| 认证方式 | Bearer Token |
| 认证头 | `Authorization: Bearer YOUR_API_KEY` |
| 兼容协议 | OpenAI v1 兼容 |
| API Key 获取 | https://platform.agnes-ai.com → 设置 → API 密钥 |

## 模型总览（主模型 + 自动降级备用）

| 模型 ID | 类型 | 端点 | 角色 | 上下文窗口 | 最大输出 |
|---------|------|------|------|-----------|---------|
| `agnes-image-2.1-flash` | 图像生成 | `/v1/images/generations` | 生图主模型 | - | - |
| `agnes-image-2.0-flash` | 图像生成 | `/v1/images/generations` | 生图备用 | - | - |
| `agnes-video-v2.0` | 视频生成 | `/v1/videos` | 视频模型（官方） | - | - |
| `agnes-video-2.5` | 视频生成 | `/v1/videos` | 实验性（仅 --model 手动指定） | - | - |
| `agnes-2.0-flash` | 视觉识图 | `/v1/chat/completions` | 识图主模型 | 512K | 65.5K |
| `agnes-1.5-flash` | 视觉识图(速度优先) | `/v1/chat/completions` | 识图备用 | 256K | 64K |

**模型自动降级**：主模型不可用时自动切换备用模型（生图 2.1→2.0，识图 2.0→1.5）。视频仅使用官方 `agnes-video-v2.0`（此前 `agnes-video-2.5` 无官方文档、实际请求失败，已弃用为实验性）。响应带 `model_used` 字段。可用 `--model` 强制指定。

## API Key 配置

API Key 存储在 `{SKILL_ROOT}/scripts/.env` 文件中：

```
AGNES_API_KEY=sk-xxxxxxxx
```

通过 `set-key` 命令自动写入：

```bash
python agnes_api.py set-key sk-xxxxxxxx
```

所有命令自动从 .env 读取 Key，无需手动传入。

## 自动重试与模型降级机制

**第 1 层：请求重试（同一模型）**
- 可重试：429（频率限制）、500（服务器错误）、503（服务繁忙）、网络超时 — 指数退避重试
- 不可重试：401（认证失败）、400（参数错误非模型相关）— 立即失败
- 重试间隔：2s → 5s → 10s → 20s → 30s（指数退避），最多 5 次

**第 2 层：模型降级（切换备用模型）**
- 当前模型重试 5 次仍失败，或错误与模型相关（不存在/不支持/404/500）→ 自动切换备用模型
- 生图：`agnes-image-2.1-flash` → `agnes-image-2.0-flash`
- 视频：仅官方 `agnes-video-v2.0`（v2.5 已弃用）
- 识图：`agnes-2.0-flash` → `agnes-1.5-flash`（降级自动关闭 Thinking）
- 备用模型也失败才向用户报错；响应 JSON 带 `model_used` 字段

---

## 一、图像生成 API

### 端点

```
POST https://apihub.agnes-ai.com/v1/images/generations
```

### 文生图参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | `agnes-image-2.1-flash` |
| `prompt` | string | 是 | 文本描述 |
| `size` | string | 是 | 输出尺寸层级 `1K`/`2K`/`3K`/`4K` 或精确 `WxH` |
| `ratio` | string | 否 | 宽高比，默认 `1:1` |
| `return_base64` | boolean | 否 | `true` 时返回 base64 |
| `extra_body.response_format` | string | 否 | `url` 或 `b64_json` |

### 图生图参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | `agnes-image-2.1-flash` |
| `prompt` | string | 是 | 编辑/变换指令 |
| `size` | string | 是 | 输出尺寸 |
| `extra_body.image` | string[] | 是 | 输入图片 URL 或 Data URI 数组 |
| `extra_body.response_format` | string | 否 | `url` 或 `b64_json` |

### 响应格式

```json
{
  "created": 1780000000,
  "data": [
    {
      "url": "https://storage.googleapis.com/agnes-aigc/xxx.png",
      "b64_json": null,
      "revised_prompt": null
    }
  ]
}
```

### 尺寸参考表

| 比例 | 1K | 2K | 3K | 4K |
|------|-----|-----|-----|-----|
| 1:1 | 1024×1024 | 2048×2048 | 3072×3072 | 4096×4096 |
| 3:4 | 864×1152 | 1728×2304 | 2592×3456 | 3456×4608 |
| 4:3 | 1152×864 | 2304×1728 | 3456×2592 | 4608×3456 |
| 16:9 | 1312×736 | 2624×1472 | 3936×2208 | 5248×2944 |
| 9:16 | 736×1312 | 1472×2624 | 2208×3936 | 2944×5248 |
| 2:3 | 832×1248 | 1664×2496 | 2496×3744 | 3328×4992 |
| 3:2 | 1248×832 | 2496×1664 | 3744×2496 | 4992×3328 |
| 21:9 | 1568×672 | 3136×1344 | 4704×2016 | 6272×2688 |

### 注意事项

- `response_format` 必须放在 `extra_body` 内，不能放在请求体顶层
- 图生图不需要传 `tags: ["img2img"]`
- 输入图片 URL 必须公开可访问，或使用 Data URI Base64
- 建议客户端超时设置 60s-360s
- 纯文生图时不要传 `extra_body.response_format`（可能报错）

---

## 二、视频生成 V2.0 API（官方）

官方文档：https://www.agnes-ai.com/zh-Hans/docs/agnes-video-v20

### 创建任务

```
POST https://apihub.agnes-ai.com/v1/videos
```

### 请求头

```
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

### 通用参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | `agnes-video-v2.0` |
| `prompt` | string | 是 | 视频内容描述 |
| `image` | string | 否 | 图生视频使用的图片 URL |
| `mode` | string | 否 | 生成模式，例如 `ti2vid` 或 `keyframes` |
| `height` | integer | 否 | 视频高度，默认 `768` |
| `width` | integer | 否 | 视频宽度，默认 `1152` |
| `num_frames` | integer | 否 | 视频帧数，必须 `≤ 441` 且遵循 `8n + 1` 规则 |
| `frame_rate` | number | 否 | 帧率，支持 `1–60` |
| `num_inference_steps` | integer | 否 | 推理步数 |
| `seed` | integer | 否 | 随机种子，用于可复现结果 |
| `negative_prompt` | string | 否 | 反向提示词，描述需要避免的内容 |
| `extra_body.image` | array | 否 | 关键帧模式下的输入图片 URL 数组 |
| `extra_body.mode` | string | 否 | 附加模式设置，例如 `keyframes` |

### 官方示例

**文生视频：**
```bash
curl -X POST https://apihub.agnes-ai.com/v1/videos \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "agnes-video-v2.0",
    "prompt": "A cinematic shot of a cat walking on the beach at sunset, soft ocean waves, warm golden lighting, realistic motion",
    "height": 768,
    "width": 1152,
    "num_frames": 121,
    "frame_rate": 24
  }'
```

**图生视频：**
```json
{
  "model": "agnes-video-v2.0",
  "prompt": "The woman slowly turns around and looks back at the camera",
  "image": "https://example.com/image.png",
  "num_frames": 121,
  "frame_rate": 24
}
```

**关键帧动画：**
```json
{
  "model": "agnes-video-v2.0",
  "prompt": "Generate a smooth cinematic transition between the keyframes",
  "extra_body": {
    "image": [
      "https://example.com/keyframe1.png",
      "https://example.com/keyframe2.png"
    ],
    "mode": "keyframes"
  },
  "num_frames": 121,
  "frame_rate": 24
}
```

### 查询任务（官方推荐）

```
GET https://apihub.agnes-ai.com/agnesapi?video_id=<VIDEO_ID>
```

兼容旧版：
```
GET https://apihub.agnes-ai.com/v1/videos/<TASK_ID>
```

### 创建任务响应

```json
{
  "id": "task_YOUR_TASK_ID",
  "task_id": "task_YOUR_TASK_ID",
  "video_id": "video_YOUR_VIDEO_ID",
  "object": "video",
  "model": "agnes-video-v2.0",
  "status": "queued",
  "progress": 0,
  "created_at": 1780457477,
  "seconds": "10.0",
  "size": "1280x768"
}
```

**注意：** 推荐使用 `video_id` 获取视频结果（官方推荐方式）。

### 完成响应（视频 URL 在 `metadata.url`）

```json
{
  "id": "task_YOUR_TASK_ID",
  "video_id": "task_YOUR_TASK_ID",
  "task_id": "task_YOUR_TASK_ID",
  "object": "video",
  "model": "agnes-video-v2.0",
  "status": "completed",
  "progress": 100,
  "created_at": 1784530473,
  "completed_at": 1784530510,
  "seconds": "1.0",
  "size": "832x448",
  "metadata": {
    "size_mapping": {
      "adjusted": true,
      "height": 448,
      "message": "Input size 1024x576 was mapped to nearest preset 480p/16:9 (832x448)",
      "ratio": "16:9",
      "requested_height": 576,
      "requested_width": 1024,
      "resolution": "480p",
      "width": 832
    },
    "url": "https://platform-outputs.agnes-ai.space/videos/agnes-video-v2.0/task_YOUR_TASK_ID.mp4"
  }
}
```

### 参数标准化

`width`/`height`/宽高比不匹配时自动映射到最近的标准档位：`480p`/`720p`/`1080p`。

| 宽高比 | 推荐场景 |
|--------|---------|
| 16:9 | 横版视频、产品演示、YouTube 风格 |
| 9:16 | 竖版短视频、TikTok / Reels / Shorts |
| 1:1 | 方形视频、社交媒体信息流 |
| 4:3 | 传统横版格式 |
| 3:4 | 竖版演示、肖像/产品为主 |

### 时长控制（官方规则）

```
seconds = num_frames / frame_rate
```

`num_frames` 必须 ≤ 441 且遵循 `8n + 1`：

| 目标时长 | 推荐参数 |
|---------|---------|
| 约 3 秒 | `num_frames: 81`, `frame_rate: 24` |
| 约 5 秒 | `num_frames: 121`, `frame_rate: 24` |
| 约 10 秒 | `num_frames: 241`, `frame_rate: 24` |
| 约 18 秒 | `num_frames: 441`, `frame_rate: 24` |

### 推荐参数

- 标准视频生成：`width: 1152`, `height: 768`, `num_frames: 121`, `frame_rate: 24`
- 更流畅运动：`frame_rate: 24` 或 `30`
- 可复现结果：设置固定 `seed`
- 关键帧过渡：`extra_body.mode: "keyframes"`
- 避免不需要的内容：`negative_prompt`

### 任务状态

| 状态 | 说明 |
|------|------|
| `queued` | 任务正在队列中等待 |
| `in_progress` | 视频正在生成 |
| `completed` | 视频生成成功（URL 在 `metadata.url`） |
| `failed` | 视频生成失败 |

---

## 三、视觉识图 API

### Chat Completions 端点

```
POST https://apihub.agnes-ai.com/v1/chat/completions
```

### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | `agnes-2.0-flash` 或 `agnes-1.5-flash` |
| `messages` | array | 是 | 消息数组 |
| `temperature` | number | 否 | 采样温度 |
| `top_p` | number | 否 | 核采样 |
| `max_tokens` | integer | 否 | 最大输出 token 数 |
| `chat_template_kwargs` | object | 否 | 扩展字段（启用 Thinking） |

### 多模态消息格式（识图）

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "描述这张图片的内容"},
    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
  ]
}
```

### 响应格式

```json
{
  "id": "chatcmpl_xxx",
  "object": "chat.completion",
  "created": 1774432125,
  "model": "agnes-2.0-flash",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "生成的文本内容..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 35,
    "completion_tokens": 58,
    "total_tokens": 93
  }
}
```

### Thinking 模式

```json
{
  "model": "agnes-2.0-flash",
  "messages": [{"role": "user", "content": "..."}],
  "chat_template_kwargs": {"enable_thinking": true}
}
```

### 模型对比

| 维度 | agnes-1.5-flash | agnes-2.0-flash |
|------|----------------|----------------|
| 侧重 | 速度、成本 | 推理、Agent、编程 |
| 多模态识图 | 支持 | 支持 |
| Thinking 模式 | 不支持 | 支持 |
| 工具调用 | 不支持 | 支持 |
| 上下文窗口 | 256K | 512K |
| 最大输出 | 64K | 65.5K |

### 其他兼容端点

**Responses API:**
```
POST https://apihub.agnes-ai.com/v1/responses
```

**Messages API（Anthropic 兼容）:**
```
POST https://apihub.agnes-ai.com/v1/messages
```
认证头不同：`x-api-key: YOUR_API_KEY` + `anthropic-version: 2023-06-01`

---

## 四、错误码

| HTTP 状态码 | 说明 | 是否重试 | 处理方式 |
|------------|------|---------|---------|
| 400 | 请求参数无效 | 否 | 检查参数和模式匹配 |
| 401 | 未授权 | 否 | 重新执行 set-key |
| 403 | 无权限 | 否 | 检查密钥状态和模型权限 |
| 404 | 任务/视频未找到 | 否 | 确认 ID 正确 |
| 429 | 请求频率超限 | 是 | 自动退避重试 |
| 500 | 服务器内部错误 | 是 | 自动重试 |
| 503 | 服务繁忙 | 是 | 自动重试 |
| 网络超时 | 网络问题 | 是 | 自动重试 |

---

## 五、定价

| 模型 | 标准价格 | 当前价格 |
|------|---------|---------|
| agnes-image-2.1-flash | $0.003/图 | **免费** |
| agnes-image-2.0-flash | — | **免费** |
| agnes-video-v2.0 | $0.005/秒 | **免费**（$0/秒） |
| agnes-2.0-flash | $0.03-$0.15/1M tokens | **免费** |
| agnes-1.5-flash | $0.07-$0.15/1M tokens | **免费** |

---

## 六、Python SDK 示例

### 使用 OpenAI 兼容库

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-your-key",
    base_url="https://apihub.agnes-ai.com/v1"
)

# 多模态识图
response = client.chat.completions.create(
    model="agnes-2.0-flash",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "描述这张图片"},
            {"type": "image_url", "image_url": {"url": "https://example.com/img.jpg"}}
        ]
    }]
)

# 文生图
response = client.images.generate(
    model="agnes-image-2.1-flash",
    prompt="一只柴犬在樱花树下",
    size="1024x1024"
)

# 图生图
response = client.images.generate(
    model="agnes-image-2.1-flash",
    prompt="改成水彩画风格",
    size="1024x768",
    extra_body={
        "image": ["https://example.com/photo.png"],
        "response_format": "url"
    }
)

# 视频生成 V2.0（异步，官方文档：agnes-video-v20）
video = client.videos.create(
    model="agnes-video-v2.0",
    prompt="猫在海滩上散步",
    width=1152,
    height=768,
    num_frames=121,
    frame_rate=24,
)
# 轮询（推荐用 video_id 查询）
while video.status not in ("completed", "failed"):
    import time; time.sleep(3)
    video = client.videos.retrieve(video.id)
# 视频 URL 在 metadata.url
print(video.metadata.url if hasattr(video, "metadata") else video.url)
```
