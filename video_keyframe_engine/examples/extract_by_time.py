"""
示例：按时间间隔提取关键帧。

用法:
    python examples/extract_by_time.py <视频路径> [间隔秒数]
    python examples/extract_by_time.py test_video.mp4 2
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keyframe_extractor import KeyframeExtractor


def main():
    if len(sys.argv) < 2:
        print("用法: python examples/extract_by_time.py <视频路径> [间隔秒数]")
        sys.exit(1)

    video_path = sys.argv[1]
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    output_dir = "output/time_sampling"

    ke = KeyframeExtractor(video_path)

    # 打印视频信息
    info = ke.video_info
    print(f"视频: {info.path}")
    print(f"分辨率: {info.width}x{info.height}, FPS: {info.fps:.1f}, 时长: {info.duration_sec:.1f}s")
    print(f"采样间隔: {interval}s")
    print()

    result = ke.extract_by_time(output_dir, interval_sec=interval)

    print(f"提取完成: {result.total_frames} 帧")
    print(f"输出目录: {result.output_dir}")
    print(f"时间戳: {result.timestamps}")
    print()
    for path in result.frame_paths:
        print(f"  {os.path.basename(path)}")


if __name__ == "__main__":
    main()
