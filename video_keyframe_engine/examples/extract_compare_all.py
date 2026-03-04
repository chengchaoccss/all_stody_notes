"""
示例：对同一视频运行所有算法并对比结果。

一次性运行四种提取模式，打印对比表格。

用法:
    python examples/extract_compare_all.py <视频路径>
    python examples/extract_compare_all.py test_video.mp4
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from keyframe_extractor import KeyframeExtractor


def main():
    if len(sys.argv) < 2:
        print("用法: python examples/extract_compare_all.py <视频路径>")
        sys.exit(1)

    video_path = sys.argv[1]

    ke = KeyframeExtractor(video_path)
    info = ke.video_info
    print(f"视频: {info.path}")
    print(f"分辨率: {info.width}x{info.height}, FPS: {info.fps:.1f}, 时长: {info.duration_sec:.1f}s")
    print(f"编码: {info.codec}, 总帧数: {info.total_frames}")
    print("=" * 70)

    tasks = [
        ("时间采样 (2s间隔)", lambda: ke.extract_by_time("output/cmp_time", interval_sec=2.0)),
        ("帧差法 (t=0.15)", lambda: ke.extract_by_frame_diff("output/cmp_diff", threshold=0.15, min_interval_sec=0.5)),
        ("光流法 (t=0.02)", lambda: ke.extract_by_optical_flow("output/cmp_flow", threshold=0.02, min_interval_sec=1.0)),
        ("场景检测 (t=0.3)", lambda: ke.extract_by_scene_detect("output/cmp_scene", threshold=0.3, min_interval_sec=1.0)),
    ]

    results = []
    for name, fn in tasks:
        print(f"\n▶ {name} ...")
        t0 = time.time()
        result = fn()
        elapsed = time.time() - t0
        results.append((name, result, elapsed))
        print(f"  完成: {result.total_frames} 帧, 耗时: {elapsed:.2f}s")

    # 对比表格
    print("\n" + "=" * 70)
    print(f"{'算法':<20} {'帧数':>6} {'耗时':>8} {'时间戳'}")
    print("-" * 70)
    for name, result, elapsed in results:
        ts_str = ", ".join(f"{t:.1f}" for t in result.timestamps)
        print(f"{name:<20} {result.total_frames:>6} {elapsed:>7.2f}s  [{ts_str}]")
    print("=" * 70)


if __name__ == "__main__":
    main()
