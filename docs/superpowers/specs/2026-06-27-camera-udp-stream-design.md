# Camera UDP Stream Design

**Date**: 2026-06-27
**Status**: Approved
**Context**: 在现有 `camera_pub_node` 中增加 UDP 视频流输出，使 PC 端可直接通过 UDP 接收视频流进行目标识别。

## Overview

在 `camera_pub_node` 的 GStreamer pipeline 中增加 `tee` 分流，将摄像头原始 MJPEG 帧通过 UDP 对外发送，不影响现有 ROS2 topic 发布和 Web 上位机显示。

## Architecture

```
USB 摄像头（MJPEG）
  → v4l2src
    → image/jpeg
      → tee name=t
        ├─ queue → nvv4l2decoder → ... → appsink → cv2 → /rov/camera/image_raw（现有路径，不变）
        └─ queue → multipartmux boundary="frame" → udpsink（新增，gcs_url 非空时启用）
```

### 关键设计决策

1. **在解码前分流**：tee 位于 `nvv4l2decoder` 之前，发送的是摄像头原始 MJPEG 帧，零额外 CPU 编码开销
2. **multipartmux 包装**：使用 MIME boundary 将每帧 JPEG 包装为 MJPEG 流，与 `/api/video/stream` 格式一致，PC 端可用 OpenCV 或 ffplay 直接接收
3. **向后兼容**：`gcs_url` 为空时完全不创建 UDP 分支，行为与当前版本一致

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `gcs_url` | string | `""` | UDP 视频流地址，格式与 MAVROS 一致<br>`udp-b://@host:port` — 广播模式<br>`udp://host:port` — 单播模式<br>空字符串禁用 UDP 流 |
| `device` | string | `/dev/video0` | （现有参数，不变） |
| `width` | int | `640` | （现有参数，不变） |
| `height` | int | `480` | （现有参数，不变） |
| `framerate` | int | `15` | （现有参数，不变） |
| `publish_rate` | float | `15.0` | （现有参数，不变） |

注：当前不增加 `jpeg_quality` 参数，因为 tee 发送的是摄像头原始画质。后续如需可控质量可加 re-encode 分支。

## URL Parsing

从 `udp-b://@0.0.0.0:5600` 解析：

| URL 模式 | 解析结果 | udpsink host |
|----------|---------|-------------|
| `udp-b://@0.0.0.0:5600` | broadcast，port 5600 | `255.255.255.255` |
| `udp-b://@:5600` | broadcast，port 5600 | `255.255.255.255` |
| `udp://192.168.1.100:5600` | unicast，target 192.168.1.100:5600 | `192.168.1.100` |

## Implementation

### 文件变更

| 文件 | 变更 |
|------|------|
| `src/rov_sensor/rov_sensor/camera_pub_node.py` | 增加 `gcs_url` 参数声明、URL 解析、GStreamer tee 分支构建 |
| `src/rov_bringup/launch/rov.launch.py` | 为 camera_pub_node 添加 `gcs_url` 参数 |
| `docs/commands.md` | 添加 UDP 视频流接收测试命令 |

### 关键实现点

1. **GStreamer tee 管道构建**：
   ```python
   def _gst_pipeline(device, width, height, framerate, gcs_url):
       base = (
           f'v4l2src device={device} io-mode=2 ! '
           f'image/jpeg, width={width}, height={height}, framerate={framerate}/1 ! '
       )
       if gcs_url:
           host, port, is_broadcast = _parse_gcs_url(gcs_url)
           return (
               base +
               f'tee name=t ! queue ! nvv4l2decoder mjpeg=1 ! nvvidconv ! '
               f'video/x-raw, format=I420 ! videoconvert ! '
               f'video/x-raw, format=BGR ! appsink drop=true max-buffers=2 '
               f't. ! queue ! multipartmux boundary=frame ! '
               f'udpsink host={host} port={port} sync=false'
           )
       else:
           return base + (
               f'nvv4l2decoder mjpeg=1 ! nvvidconv ! '
               f'video/x-raw, format=I420 ! videoconvert ! '
               f'video/x-raw, format=BGR ! appsink drop=true max-buffers=2'
           )
   ```

2. **URL 解析函数**：
   ```python
   def _parse_gcs_url(url: str) -> tuple:
       """Parse 'udp-b://@host:port' or 'udp://host:port'.
       Returns (host, port, is_broadcast).
       """
       # ...
   ```

### PC 端接收

```bash
# OpenCV 接收
python3 -c "
import cv2
cap = cv2.VideoCapture('udp://@0.0.0.0:5600')
# or: cap = cv2.VideoCapture('udp://@:5600?overrun_nonfatal=1&fifo_size=50000000')
while True:
    ret, frame = cap.read()
    if ret:
        cv2.imshow('ROV Camera', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
"

# ffplay 测试
ffplay -fflags nobuffer -flags low_delay udp://0.0.0.0:5600
```

## Error Handling

| 场景 | 行为 |
|------|------|
| `gcs_url` 为空 | 不创建 UDP 分支，完全向后兼容 |
| `gcs_url` 格式无效 | 日志警告，禁用 UDP，ROS topic 仍正常工作 |
| 摄像头打开失败 | 不创建任何 pipeline（与现有行为一致） |
| UDP 端口被占用 | GStreamer 启动时出错，节点初始化失败 |
| PC 未监听 | UDP 包照常发出，不阻塞（`sync=false`） |

## Testing

1. 不设 `gcs_url`（空字符串）→ 确认 ROS topic 正常发布，无 UDP 发送
2. 设置 `gcs_url: 'udp-b://@0.0.0.0:5600'` → PC 端 `ffplay udp://0.0.0.0:5600` 确认画面正常显示
3. Web GCS MJPEG 流仍正常 → `/api/video/stream` 不受影响
4. 格式错误的 `gcs_url: 'invalid'` → 日志警告，ROS topic 仍正常
