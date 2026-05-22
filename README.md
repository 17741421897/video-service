# video-service

Wan2.1 文生视频 HTTP API（ComfyUI 引擎 + `run.py` 源码启动）。

## 目录

```
video-service/
  run.py, server.py, …    API
  ComfyUI/                引擎 + models（自备）
  start.bat / start.sh
  MODELS.md
  config.env.example
```

## 启动

- Windows：`start.bat`
- Linux：`bash start.sh`

环境变量（可选）：`VIDEO_SERVICE_PYTHON`、`COMFY_PYTHON`、`ENGINE_ROOT` — 见 `config.env.example`。

## 接口

```
POST http://127.0.0.1:8080/v1/video
{"prompt":"一只猫在海边","duration":10,"fps":24,"resolution":"480p","aspect_ratio":"16:9","steps":28,"cfg_scale":7,"motion":"medium","quality":"pro","style_preset":"cinematic","custom_style":"","seed":42}
```

| 字段 | 说明 |
|------|------|
| `duration` | 时长（秒）1–30 → `num_frames` |
| `fps` | 帧率 8–60 → `CreateVideo.fps` |
| `resolution` | `480p`(推荐,832×480) / `720p` / `1080p` / `2k` / `4k` → 宽高 |
| `aspect_ratio` | `16:9` / `9:16` / `1:1` / `21:9` |
| `steps` | 采样步数 8–120（标准模式上限 28） |
| `cfg_scale` | CFG 1–20 → `WanVideoSampler.cfg` |
| `motion` | `low` / `medium` / `high` → `shift` |
| `quality` | `standard` / `pro` |
| `style_preset` | 编辑器风格预设 → 追加正向提示词 |
| `custom_style` | 自定义风格标签 |
| `negative` | 负向提示词 |
| `seed` | 随机种子（可选） |

### 图生视频 `POST /v1/video/i2v`

在以上字段基础上增加：

| 字段 | 说明 |
|------|------|
| `image_base64` | 参考图 Base64（必填），可带 `data:image/png;base64,` 前缀 |
