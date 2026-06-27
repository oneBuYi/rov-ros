# Camera UDP Stream Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `camera_pub_node` 增加 UDP 视频流输出，通过 GStreamer tee 在解码前分流 MJPEG 帧发送到网络。

**Architecture:** 修改 `_gst_pipeline` 在 `nvv4l2decoder` 前插入 `tee` 元件，当 `gcs_url` 非空时创建第二个分支（`queue → multipartmux → udpsink`），发送摄像头原始 MJPEG 帧。不影响现有 BGR→ROS topic 分支。

**Tech Stack:** Python 3.8, GStreamer 1.0 (gst-python), ROS2 Foxy

## Global Constraints

- GStreamer pipeline 必须在 Jetson Nano 上使用 NVV4L2 硬件加速
- `gcs_url` 参数名和格式与 MAVROS `gcs_url` 保持一致（`udp-b://` / `udp://`）
- 向后兼容：`gcs_url` 为空时不创建 UDP 分支
- UDP 使用 `sync=false` 避免阻塞

---

### Task 1: Add `_parse_gcs_url` function

**Files:**
- Modify: `src/rov_sensor/rov_sensor/camera_pub_node.py` — add function after `_gst_pipeline`, before `CameraPubNode`

**Interfaces:**
- Produces: `_parse_gcs_url(url: str) -> tuple[str, int, bool]` — returns `(host, port, is_broadcast)`, raises `ValueError` on invalid URL format

- [ ] **Step 1: Add import and function**

Add `import re` at top of file, then add `_parse_gcs_url` after `_gst_pipeline`:

```python
import re


def _parse_gcs_url(url: str):
    """Parse MAVROS-style gcs_url for GStreamer udpsink.

    Formats:
      udp-b://@host:port  → broadcast (host=255.255.255.255)
      udp-b://@:port      → broadcast (host=255.255.255.255)
      udp://host:port     → unicast to host

    Returns (host, port, is_broadcast).
    """
    m = re.match(r'(udp-b?)://(?:@)?([^:]*):(\d+)', url)
    if not m:
        raise ValueError(f'Invalid gcs_url: {url}')

    scheme = m.group(1)      # 'udp-b' or 'udp'
    bind_addr = m.group(2)   # host part (may be empty, e.g. '@:5600')
    port = int(m.group(3))

    is_broadcast = scheme == 'udp-b'
    host = '255.255.255.255' if is_broadcast else (bind_addr or '127.0.0.1')

    return host, port, is_broadcast
```

- [ ] **Step 2: Quick smoke test in Python REPL**

```bash
python3 -c "
import re, sys
sys.path.insert(0, 'src/rov_sensor/rov_sensor')
from camera_pub_node import _parse_gcs_url
# Test broadcast with bind address
h, p, b = _parse_gcs_url('udp-b://@0.0.0.0:5600')
assert h == '255.255.255.255' and p == 5600 and b == True, f'FAIL: {h} {p} {b}'
# Test broadcast without bind address
h, p, b = _parse_gcs_url('udp-b://@:5600')
assert h == '255.255.255.255' and p == 5600 and b == True, f'FAIL: {h} {p} {b}'
# Test unicast
h, p, b = _parse_gcs_url('udp://192.168.1.100:5600')
assert h == '192.168.1.100' and p == 5600 and b == False, f'FAIL: {h} {p} {b}'
# Test invalid
try:
    _parse_gcs_url('invalid')
    assert False, 'Should have raised'
except ValueError:
    pass
print('All assertions passed')
"
```

Expected: `All assertions passed`

- [ ] **Step 3: Commit**

```bash
git add src/rov_sensor/rov_sensor/camera_pub_node.py
git commit -m "feat: add _parse_gcs_url for MAVROS-style UDP URL parsing

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Modify `_gst_pipeline` to accept `gcs_url`

**Files:**
- Modify: `src/rov_sensor/rov_sensor/camera_pub_node.py` — `_gst_pipeline` function

**Interfaces:**
- Consumes: `_parse_gcs_url(url: str) -> tuple[str, int, bool]` (from Task 1)
- Produces: `_gst_pipeline(device: str, width: int, height: int, framerate: int, gcs_url: str) -> str`

- [ ] **Step 1: Modify `_gst_pipeline` signature and body**

Replace the existing `_gst_pipeline` function (lines 16–28) with:

```python
def _gst_pipeline(device: str, width: int, height: int,
                  framerate: int, gcs_url: str) -> str:
    """Build GStreamer pipeline with optional UDP video stream.

    When gcs_url is non-empty, inserts a tee before the hardware decoder
    and sends the original MJPEG frames over UDP via a second branch.
    """
    base = (
        f'v4l2src device={device} io-mode=2 ! '
        f'image/jpeg, width={width}, height={height}, framerate={framerate}/1 ! '
    )

    # BGR → ROS topic branch (always present)
    bgr_branch = (
        f'nvv4l2decoder mjpeg=1 ! '
        f'nvvidconv ! '
        f'video/x-raw, format=I420 ! '
        f'videoconvert ! '
        f'video/x-raw, format=BGR ! '
        f'appsink drop=true max-buffers=2'
    )

    if not gcs_url:
        return base + bgr_branch

    # Parse gcs_url for UDP branch
    host, port, is_broadcast = _parse_gcs_url(gcs_url)

    udp_branch = (
        f'queue ! '
        f'multipartmux boundary=frame ! '
        f'udpsink host={host} port={port} sync=false'
    )

    return (
        f'{base}'
        f'tee name=t ! '
        f'queue ! {bgr_branch} '
        f't. ! {udp_branch}'
    )
```

- [ ] **Step 2: Verify empty gcs_url produces original pipeline**

```bash
python3 -c "
import sys
sys.path.insert(0, 'src/rov_sensor/rov_sensor')
from camera_pub_node import _gst_pipeline
# Empty gcs_url should produce original pipeline (no tee, no udpsink)
p = _gst_pipeline('/dev/video0', 640, 480, 15, '')
assert 'tee' not in p, f'FAIL: tee found when gcs_url is empty: {p}'
assert 'udpsink' not in p, f'FAIL: udpsink found when gcs_url is empty: {p}'
assert 'nvv4l2decoder' in p, f'FAIL: no decoder in pipeline'
print('Empty gcs_url OK')
"
```

Expected: `Empty gcs_url OK`

- [ ] **Step 3: Verify non-empty gcs_url produces tee pipeline**

```bash
python3 -c "
import sys
sys.path.insert(0, 'src/rov_sensor/rov_sensor')
from camera_pub_node import _gst_pipeline
p = _gst_pipeline('/dev/video0', 640, 480, 15, 'udp-b://@0.0.0.0:5600')
assert 'tee name=t' in p, f'FAIL: no tee in pipeline: {p}'
assert 'multipartmux boundary=frame' in p, f'FAIL: no multipartmux'
assert 'udpsink host=255.255.255.255 port=5600 sync=false' in p, f'FAIL: wrong udpsink'
assert 'nvv4l2decoder' in p, f'FAIL: no decoder in pipeline'
print('UDP pipeline OK')
print(p)
"
```

Expected: `UDP pipeline OK` followed by full pipeline string

- [ ] **Step 4: Commit**

```bash
git add src/rov_sensor/rov_sensor/camera_pub_node.py
git commit -m "feat: add tee-based UDP video stream to camera GStreamer pipeline

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Wire `gcs_url` parameter into `CameraPubNode`

**Files:**
- Modify: `src/rov_sensor/rov_sensor/camera_pub_node.py` — `CameraPubNode.__init__`

**Interfaces:**
- Consumes: `_gst_pipeline(device, width, height, framerate, gcs_url)` (from Task 2)

- [ ] **Step 1: Declare `gcs_url` parameter and pass to pipeline**

In `CameraPubNode.__init__`, add `gcs_url` to `declare_parameters` and extract it, then pass to `_gst_pipeline`. The parameter block (lines 37–46) becomes:

```python
        self.declare_parameters(
            namespace='',
            parameters=[
                ('device', '/dev/video0'),
                ('width', 640),
                ('height', 480),
                ('framerate', 15),
                ('publish_rate', 15.0),
                ('gcs_url', ''),
            ],
        )

        device = self.get_parameter('device').value
        width = self.get_parameter('width').value
        height = self.get_parameter('height').value
        framerate = self.get_parameter('framerate').value
        publish_rate = self.get_parameter('publish_rate').value
        gcs_url = self.get_parameter('gcs_url').value
```

And the pipeline construction line (line 54) becomes:

```python
        pipeline = _gst_pipeline(device, width, height, framerate, gcs_url)
```

- [ ] **Step 2: Add gcs_url error handling**

Insert after `gcs_url = self.get_parameter('gcs_url').value`:

```python
        if gcs_url:
            try:
                _parse_gcs_url(gcs_url)
            except ValueError as e:
                self.get_logger().warn(
                    f'Invalid gcs_url "{gcs_url}": {e}. UDP stream disabled.'
                )
                gcs_url = ''
```

- [ ] **Step 3: Add UDP status to startup log**

Replace the startup log line (lines 66–68) with:

```python
        udp_info = f', UDP→{gcs_url}' if gcs_url else ''
        self.get_logger().info(
            f'rov_camera_pub started ({width}x{height}@{framerate}fps, '
            f'publish@{publish_rate:.0f}Hz{udp_info})')
```

- [ ] **Step 4: Quick syntax check**

```bash
python3 -c "import py_compile; py_compile.compile('src/rov_sensor/rov_sensor/camera_pub_node.py', doraise=True); print('Syntax OK')"
```

Expected: `Syntax OK`

- [ ] **Step 5: Commit**

```bash
git add src/rov_sensor/rov_sensor/camera_pub_node.py
git commit -m "feat: wire gcs_url parameter into CameraPubNode with error handling

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Update launch file with `gcs_url` parameter

**Files:**
- Modify: `src/rov_bringup/launch/rov.launch.py` — `camera_pub_node` definition

- [ ] **Step 1: Add `gcs_url` parameter to launch node**

Replace the `camera_pub_node` definition (lines 36–40) with:

```python
    camera_pub_node = Node(
        package='rov_sensor',
        executable='camera_pub_node',
        parameters=[{
            'device': '/dev/video0',
            'width': 640,
            'height': 480,
            'framerate': 15,
            'publish_rate': 15.0,
            'gcs_url': 'udp-b://@0.0.0.0:5600',
        }],
        output='screen',
    )
```

- [ ] **Step 2: Commit**

```bash
git add src/rov_bringup/launch/rov.launch.py
git commit -m "feat: add gcs_url to camera_pub_node launch configuration

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Update docs

**Files:**
- Modify: `docs/commands.md`

- [ ] **Step 1: Add UDP video stream reception commands**

Append to the "调试与测试" section in `docs/commands.md`:

```markdown
# UDP 视频流接收（PC 端）
ffplay -fflags nobuffer -flags low_delay udp://0.0.0.0:5600

# 或通过 OpenCV 接收
python3 -c "
import cv2
cap = cv2.VideoCapture('udp://@0.0.0.0:5600?overrun_nonfatal=1&fifo_size=50000000')
while True:
    ret, frame = cap.read()
    if ret:
        cv2.imshow('ROV Camera', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
"
```

- [ ] **Step 2: Commit**

```bash
git add docs/commands.md
git commit -m "docs: add UDP video stream reception commands

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Build and verify on hardware

**Prerequisites:** Jetson Nano with camera connected, ROS2 workspace sourced.

- [ ] **Step 1: Build the modified packages**

```bash
cd /home/jetson/whj/rov-ros
source /opt/ros/foxy/setup.bash
colcon build --packages-select rov_sensor rov_bringup
source install/setup.bash
```

Expected: Build succeeds with no errors.

- [ ] **Step 2: Run camera_pub_node with default gcs_url (empty, backward compat)**

```bash
# Run without launch file, pass empty gcs_url explicitly
ros2 run rov_sensor camera_pub_node --ros-args -p gcs_url:=''
```

Verify from log: no "UDP→" in startup message, `/rov/camera/image_raw` topic published.

- [ ] **Step 3: Run camera_pub_node with UDP enabled**

```bash
ros2 run rov_sensor camera_pub_node --ros-args -p gcs_url:='udp-b://@0.0.0.0:5600'
```

Verify: `UDP→udp-b://@0.0.0.0:5600` in startup log.

- [ ] **Step 4: Receive UDP stream on the same machine**

In another terminal:

```bash
ffplay -fflags nobuffer -flags low_delay udp://0.0.0.0:5600
```

Expected: Video window shows camera feed with low latency.

- [ ] **Step 5: Verify Web GCS MJPEG stream is unaffected**

Start the full stack and confirm `/api/video/stream` still works in browser.

- [ ] **Step 6: Commit any final adjustments**

```bash
git add -A
git commit -m "chore: final adjustments after hardware verification

Co-Authored-By: Claude <noreply@anthropic.com>"
```
