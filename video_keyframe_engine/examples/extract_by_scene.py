"""
示例：场景检测提取关键帧。

基于 HSV 颜色直方图的 Bhattacharyya 距离检测场景切换。
对光照变化不敏感（去掉了 V 通道），专注颜色分布变化。

用法:
    python examples/extract_by_scene.py <视频路径> [阈值] [最小间隔秒]
    python examples/extract_by_scene.py test_video.mp4 0.3 1
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keyframe_extractor import KeyframeExtractor


def main():
    if len(sys.argv) < 2:
        print("用法: python examples/extract_by_scene.py <视频路径> [阈值] [最小间隔秒]")
        sys.exit(1)

    video_path = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.3
    min_interval = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    output_dir = "output/scene_detect"

    ke = KeyframeExtractor(video_path)

    info = ke.video_info
    print(f"视频: {info.path}")
    print(f"分辨率: {info.width}x{info.height}, FPS: {info.fps:.1f}, 时长: {info.duration_sec:.1f}s")
    print(f"场景检测参数: threshold={threshold}, min_interval={min_interval}s")
    print()

    result = ke.extract_by_scene_detect(output_dir, threshold=threshold, min_interval_sec=min_interval)

    print(f"提取完成: {result.total_frames} 帧")
    print(f"输出目录: {result.output_dir}")
    print(f"时间戳: {result.timestamps}")
    print()
    for path in result.frame_paths:
        print(f"  {os.path.basename(path)}")


if __name__ == "__main__":
    main()
