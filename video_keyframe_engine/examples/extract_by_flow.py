"""
示例：光流法提取关键帧。

检测运动强度突变（如物体突然移动、镜头快速切换）。

用法:
    python examples/extract_by_flow.py <视频路径> [阈值] [最小间隔秒]
    python examples/extract_by_flow.py test_video.mp4 0.02 1
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keyframe_extractor import KeyframeExtractor


def main():
    if len(sys.argv) < 2:
        print("用法: python examples/extract_by_flow.py <视频路径> [阈值] [最小间隔秒]")
        sys.exit(1)

    video_path = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.02
    min_interval = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    output_dir = "output/optical_flow"

    ke = KeyframeExtractor(video_path)

    info = ke.video_info
    print(f"视频: {info.path}")
    print(f"分辨率: {info.width}x{info.height}, FPS: {info.fps:.1f}, 时长: {info.duration_sec:.1f}s")
    print(f"光流法参数: threshold={threshold}, min_interval={min_interval}s")
    print()

    result = ke.extract_by_optical_flow(output_dir, threshold=threshold, min_interval_sec=min_interval)

    print(f"提取完成: {result.total_frames} 帧")
    print(f"输出目录: {result.output_dir}")
    print(f"时间戳: {result.timestamps}")
    print()
    for path in result.frame_paths:
        print(f"  {os.path.basename(path)}")


if __name__ == "__main__":
    main()
