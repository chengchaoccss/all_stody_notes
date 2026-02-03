# Spatial Performance Test

一个基于 Android XR SDK 的空间性能测试应用，使用 Kotlin + Jetpack Compose 开发。

## 功能特性

### 手动测试模式
- 🎮 **空间面板界面**: 在 XR 环境中显示控制面板
- 🔢 **自定义模型数量**: 输入指定数量的整数，加载对应数量的3D模型
- 🐔 **3D模型排列**: 模型按 X、Y、Z 三个方向的3D网格排列
- 📊 **实时帧率监控**: 实时显示当前 FPS 并在日志中打印
- ⚡ **快速选择**: 预设常用数量按钮（10、50、100、200、500）

### 自动Benchmark模式
- 🤖 **自动性能测试**: 自动每2分钟增加模型数量
- 🎯 **90fps阈值检测**: 当帧率低于90fps时自动停止
- 📈 **结果记录**: 记录每次迭代的模型数量和FPS
- 📋 **详细报告**: 在日志中输出完整的性能测试报告

## 项目结构

```
SpatialPerformanceTest/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/example/spatialperformancetest/
│   │   │   │   ├── MainActivity.kt          # 主活动，XR会话管理
│   │   │   │   ├── FPSMonitor.kt             # 帧率监控类
│   │   │   │   ├── ModelManager.kt           # 3D模型管理类
│   │   │   │   ├── BenchmarkManager.kt       # 自动Benchmark管理
│   │   │   │   └── ui/theme/
│   │   │   │       ├── Theme.kt              # 主题配置
│   │   │   │       └── Typography.kt         # 字体配置
│   │   │   ├── assets/models/
│   │   │   │   ├── chicken.glb               # 小鸡/鸭子3D模型
│   │   │   │   ├── duck.glb                  # 备用模型
│   │   │   │   └── box.glb                   # 简单方块模型
│   │   │   ├── res/
│   │   │   │   └── ...                       # 资源文件
│   │   │   └── AndroidManifest.xml           # 应用清单
│   │   ├── test/                             # 单元测试
│   │   │   └── java/com/example/spatialperformancetest/
│   │   │       ├── FPSMonitorTest.kt
│   │   │       ├── BenchmarkManagerTest.kt
│   │   │       └── GridCalculatorTest.kt
│   │   └── androidTest/                      # 功能测试
│   │       └── java/com/example/spatialperformancetest/
│   │           └── MainActivityInstrumentedTest.kt
│   └── build.gradle.kts                      # 模块构建配置
├── build.gradle.kts                          # 项目构建配置
├── settings.gradle.kts                       # 项目设置
├── gradlew                                   # Gradle Wrapper (Unix)
├── gradlew.bat                               # Gradle Wrapper (Windows)
└── README.md
```

## 技术栈

- **Kotlin** - 主要编程语言
- **Jetpack Compose** - 现代 UI 框架
- **Android XR SDK** - 空间计算 SDK
  - `androidx.xr.compose` - XR Compose 扩展
  - `androidx.xr.scenecore` - 场景核心库
  - `androidx.xr.arcore` - AR 核心库
- **Choreographer** - 用于精确的帧率监控
- **Kotlin Coroutines** - 异步编程
- **JUnit 4 & Mockito** - 单元测试
- **Espresso & Compose Test** - UI测试

## 使用方法

### 1. 构建项目

```bash
# 编译调试版本
./gradlew assembleDebug

# 编译发布版本
./gradlew assembleRelease
```

### 2. 运行测试

```bash
# 运行单元测试
./gradlew test

# 运行功能测试 (需要连接设备或模拟器)
./gradlew connectedAndroidTest
```

### 3. 安装应用

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### 4. 运行应用

在 Android XR 设备上启动应用：

#### 手动测试模式
1. 选择 "Manual Test" 标签页
2. 输入要加载的模型数量（或使用快速选择按钮）
3. 点击 "Load Models" 按钮
4. 观察空间中的3D模型排列
5. 查看面板上的实时 FPS 显示

#### 自动Benchmark模式
1. 选择 "Auto Benchmark" 标签页
2. 点击 "Start Auto Benchmark" 按钮
3. 系统会自动：
   - 从10个模型开始
   - 每2分钟增加10个模型
   - 当FPS低于90时停止
4. 查看结果表格和最终报告

## 日志输出

应用会在 Logcat 中输出以下信息：

### FPS 监控日志
```
I/FPSMonitor: ========================================
I/FPSMonitor: FPS: 60.00 | Frame Count: 60 | Smoothed FPS: 59.87
I/FPSMonitor: ========================================
```

### 模型加载日志
```
I/ModelManager: Starting to load 100 models...
I/ModelManager: Grid dimensions: 5 x 5 x 4
I/ModelManager: Loaded 10 / 100 models
...
I/ModelManager: Model loading complete!
I/ModelManager: Total models loaded: 100
I/ModelManager: Time taken: 1250ms
```

### Benchmark 日志
```
I/BenchmarkManager: ========================================
I/BenchmarkManager: Starting Automated Benchmark
I/BenchmarkManager: Target FPS: 90.0
I/BenchmarkManager: Interval: 120s
I/BenchmarkManager: Model Increment: 10
I/BenchmarkManager: ========================================
...
I/BenchmarkManager: ╔══════════════════════════════════════════════════════════════╗
I/BenchmarkManager: ║              BENCHMARK RESULTS SUMMARY                       ║
I/BenchmarkManager: ╠══════════════════════════════════════════════════════════════╣
I/BenchmarkManager: ║ Target FPS: 90.0                                              ║
I/BenchmarkManager: ║ Max Models at 90fps: 150                                      ║
I/BenchmarkManager: ╠══════════════════════════════════════════════════════════════╣
I/BenchmarkManager: ║  Iteration  │  Models  │    FPS                              ║
I/BenchmarkManager: ╠══════════════════════════════════════════════════════════════╣
I/BenchmarkManager: ║      1      │     10   │  120.00 ✓                           ║
I/BenchmarkManager: ║      2      │     20   │  115.00 ✓                           ║
I/BenchmarkManager: ║     ...     │    ...   │  ...                                ║
I/BenchmarkManager: ╚══════════════════════════════════════════════════════════════╝
```

使用以下命令过滤日志：
```bash
adb logcat -s SpatialPerfTest FPSMonitor ModelManager BenchmarkManager
```

## Benchmark 配置

| 参数 | 值 | 说明 |
|------|-----|------|
| TARGET_FPS | 90.0 | 目标帧率阈值 |
| INTERVAL_MS | 120000 (2分钟) | 每次迭代间隔 |
| MODEL_INCREMENT | 10 | 每次增加的模型数量 |
| INITIAL_MODEL_COUNT | 10 | 初始模型数量 |
| FPS_SAMPLE_DURATION_MS | 5000 (5秒) | FPS采样持续时间 |

## 模型排列算法

模型按照立方体网格排列：
- 计算 N 的立方根来确定基础维度
- 模型间距: X=0.3m, Y=0.3m, Z=0.3m
- 起始位置: 用户前方 2 米，略高于视线水平

例如，加载 100 个模型会创建约 5×5×4 的网格排列。

## 性能测试建议

### 手动测试
1. **从少量开始**: 先从 10 个模型开始测试
2. **逐步增加**: 每次增加 20-50 个模型
3. **观察 FPS**: 当 FPS 下降到 90 以下时，记录模型数量
4. **对比测试**: 使用不同复杂度的模型进行对比

### 自动Benchmark
1. 确保设备充满电或连接电源
2. 关闭其他后台应用
3. 在稳定的环境中运行
4. 完整运行直到自动停止

## 3D模型说明

项目包含以下GLB模型（来自 [Khronos glTF-Sample-Assets](https://github.com/KhronosGroup/glTF-Sample-Assets)）：

- **chicken.glb** - 主要测试模型（Duck模型别名）
- **duck.glb** - Khronos官方示例鸭子模型
- **box.glb** - 简单立方体模型（用于基准测试）

## 要求

- Android 14 (API 34) 或更高版本
- Android XR 兼容设备
- Android Studio Hedgehog 或更新版本
- JDK 17

## 许可证

MIT License

## 致谢

- 3D模型来自 [Khronos glTF-Sample-Assets](https://github.com/KhronosGroup/glTF-Sample-Assets)
- Android XR SDK 由 Google 提供
