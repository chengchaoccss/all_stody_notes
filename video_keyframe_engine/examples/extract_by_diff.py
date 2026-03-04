"""
示例：帧差法提取关键帧。

检测画面内容突变（如场景切换、闪烁）。

用法:
    python examples/extract_by_diff.py <视频路径> [阈值] [最小间隔秒]
    python examples/extract_by_diff.py test_video.mp4 0.15 0.5
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keyframe_extractor import KeyframeExtractor


def main():
    if len(sys.argv) < 2:
        print("用法: python examples/extract_by_diff.py <视频路径> [阈值] [最小间隔秒]")
        sys.exit(1)

    video_path = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15
    min_interval = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
    output_dir = "output/frame_diff"

    ke = KeyframeExtractor(video_path)

    info = ke.video_info
    print(f"视频: {info.path}")
    print(f"分辨率: {info.width}x{info.height}, FPS: {info.fps:.1f}, 时长: {info.duration_sec:.1f}s")
    print(f"帧差法参数: threshold={threshold}, min_interval={min_interval}s")
    print()

    result = ke.extract_by_frame_diff(output_dir, threshold=threshold, min_interval_sec=min_interval)

    print(f"提取完成: {result.total_frames} 帧")
    print(f"输出目录: {result.output_dir}")
    print(f"时间戳: {result.timestamps}")
    print()
    for path in result.frame_paths:
        print(f"  {os.path.basename(path)}")


if __name__ == "__main__":
    main()
