# Wan2.1 GGUF 模型说明

本服务（`video-service`）当前工作流面向 **Wan2.1 文生视频 1.3B** 量化版，需 **同时** 准备以下 **3 个文件**（约 8GB）：

| 类型 | 相对路径（引擎 `ComfyUI/models/` 下） | 示例文件名 |
|------|--------------------------------------|------------|
| 扩散模型 | `diffusion_models/` | `Wan2.1-T2V-1.3B-Q4_K_M.gguf` |
| 文本编码器 | `text_encoders/` | `umt5-xxl-enc-fp8_e4m3fn.safetensors` |
| VAE | `vae/` | `Wan2_1_VAE_bf16.safetensors` |

## 引擎依赖

- 放在 **`video-service/ComfyUI/models/`** 下对应子目录
- 自定义节点：**ComfyUI-GGUF**、**ComfyUI-WanVideoWrapper**

## 硬件建议

- NVIDIA GPU，显存建议 ≥12GB（如 RTX 3090）

## 图生视频（I2V）

- 路由：`POST /v1/video/i2v` 或 `POST /video/i2v`
- 请求体在文生视频字段基础上增加 **`image_base64`**（PNG/JPEG 的 Base64，可带 `data:image/...;base64,` 前缀）
- 工作流：`workflow_i2v.json`（`WanVideoImageToVideoEncode` + 参考图）
- 当前仍使用 **Wan2.1-T2V-1.3B** 权重做图生，效果不如专用 I2V 模型；若需更好图生效果可自备 Wan I2V 权重并改 `workflow_i2v.json` 中的模型名

## 其它视频后端

若使用 **stable-diffusion.cpp** 的 `sd-server` 等，权重与路径以该工具文档为准（**不是** 上表三个固定文件名）。HTTP 路由通常为 `/video/t2v`，与本服务的 `/v1/video` 不同。
