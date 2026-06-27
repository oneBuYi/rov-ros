#!/usr/bin/env python3
"""
PC 端 UDP 视频流接收测试工具。

支持从 Jetson 的 h264_udp_node（RTP H.264）或 camera_pub_node（MJPEG）
接收视频流，使用 OpenCV 解码并实时显示。

用法:
    # 接收 H.264 RTP 流（与 h264_udp_node 配合）
    python3 udp_video_receiver.py

    # 接收 MJPEG 流（与 camera_pub_node 配合）
    python3 udp_video_receiver.py --type mjpeg

    # 自定义地址和端口
    python3 udp_video_receiver.py --host 192.168.3.11 --port 5600 --type h264
"""

import argparse
import sys
import time

import cv2


def _mjpeg_pipeline(host: str, port: int) -> str:
    """MJPEG 裸流接收 pipeline。"""
    return (
        f'udpsrc address={host} port={port} '
        f'caps="image/jpeg,width=640,height=480,framerate=15/1" ! '
        f'multipartdemux ! '
        f'jpegdec ! '
        f'videoconvert ! '
        f'video/x-raw,format=BGR ! '
        f'appsink drop=true max-buffers=2'
    )


def _h264_pipeline(host: str, port: int) -> str:
    """H.264 RTP 流接收 pipeline。"""
    return (
        f'udpsrc address={host} port={port} '
        f'caps="application/x-rtp,media=video,payload=96,encoding-name=H264" ! '
        f'rtph264depay ! '
        f'h264parse ! '
        f'avdec_h264 ! '
        f'videoconvert ! '
        f'video/x-raw,format=BGR ! '
        f'appsink drop=true max-buffers=2'
    )


def build_pipeline(stream_type: str, host: str, port: int) -> str:
    """根据流类型构建 GStreamer pipeline 字符串。"""
    if stream_type == 'h264':
        return _h264_pipeline(host, port)
    elif stream_type == 'mjpeg':
        return _mjpeg_pipeline(host, port)
    else:
        raise ValueError(f'Unknown stream type: {stream_type}')


def main():
    parser = argparse.ArgumentParser(
        description='PC 端 UDP 视频流接收播放工具')
    parser.add_argument(
        '--type', choices=['h264', 'mjpeg'], default='h264',
        help='流类型: h264 (默认, 对应 h264_udp_node) 或 mjpeg (对应 camera_pub_node)')
    parser.add_argument(
        '--host', default='0.0.0.0',
        help='监听地址 (默认: 0.0.0.0)')
    parser.add_argument(
        '--port', type=int, default=5600,
        help='UDP 端口 (默认: 5600)')
    parser.add_argument(
        '--no-display', action='store_true',
        help='仅接收不显示（测试带宽/延迟用）')
    args = parser.parse_args()

    pipeline = build_pipeline(args.type, args.host, args.port)
    print(f'[{args.type.upper()}] Opening: udp://{args.host}:{args.port}')
    print(f'Pipeline: {pipeline}')

    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print(f'ERROR: Failed to open {args.type.upper()} stream', file=sys.stderr)
        sys.exit(1)

    print(f'Connected. Press q to quit, s to save screenshot.')

    frame_count = 0
    fps_start = time.time()
    fps_frames = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            frame_count += 1
            fps_frames += 1

            # 每秒输出一次帧率统计
            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                fps = fps_frames / elapsed
                print(f'\rFrames: {frame_count:6d}  FPS: {fps:5.1f}', end='', flush=True)
                fps_frames = 0
                fps_start = time.time()

            if args.no_display:
                continue

            cv2.imshow(f'ROV {args.type.upper()} Stream', frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                filename = f'screenshot_{time.strftime("%Y%m%d_%H%M%S")}.jpg'
                cv2.imwrite(filename, frame)
                print(f'\nScreenshot saved: {filename}')

    except KeyboardInterrupt:
        pass
    finally:
        print(f'\nTotal frames: {frame_count}')
        cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
