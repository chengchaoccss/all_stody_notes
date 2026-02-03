# Spatial Performance Test

一个基于 Android XR SDK 的空间性能测试应用，使用 Kotlin + Jetpack Compose 开发。

## 功能特性

- 🎮 **空间面板界面**: 在 XR 环境中显示控制面板
- 🔢 **自定义模型数量**: 输入指定数量的整数，加载对应数量的3D模型
- 🐔 **3D模型排列**: 模型按 X、Y、Z 三个方向的3D网格排列
- 📊 **实时帧率监控**: 实时显示当前 FPS 并在日志中打印
- ⚡ **性能测试**: 通过增加模型数量来测试渲染性能上限

## 项目结构

```
SpatialPerformanceTest/
├── app/
│   ├── src/main/
│   │   ├── java/com/example/spatialperformancetest/
│   │   │   ├── MainActivity.kt          # 主活动，XR会话管理
│   │   │   ├── FPSMonitor.kt             # 帧率监控类
│   │   │   ├── ModelManager.kt           # 3D模型管理类
│   │   │   └── ui/theme/
│   │   │       ├── Theme.kt              # 主题配置
│   │   │       └── Typography.kt         # 字体配置
│   │   ├── assets/models/
│   │   │   └── chicken.glb               # 小鸡3D模型 (需自行添加)
│   │   ├── res/
│   │   │   └── ...                       # 资源文件
│   │   └── AndroidManifest.xml           # 应用清单
│   └── build.gradle.kts                  # 模块构建配置
├── build.gradle.kts                      # 项目构建配置
├── settings.gradle.kts                   # 项目设置
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

## 使用方法

### 1. 准备3D模型

将 GLB 格式的3D模型文件放入：
```
app/src/main/assets/models/chicken.glb
```

### 2. 构建并安装

```bash
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### 3. 运行应用

在 Android XR 设备上启动应用：
1. 输入要加载的模型数量（如 10、50、100）
2. 点击 "Load Models" 按钮
3. 观察空间中的3D模型排列
4. 查看面板上的实时 FPS 显示
5. 在 Logcat 中查看详细的帧率日志

## 日志输出

应用会在 Logcat 中输出以下信息：

```
I/FPSMonitor: ========================================
I/FPSMonitor: FPS: 60.00 | Frame Count: 60 | Smoothed FPS: 59.87
I/FPSMonitor: ========================================
I/ModelManager: Starting to load 100 models...
I/ModelManager: Grid dimensions: 5 x 5 x 4
I/ModelManager: Loaded 10 / 100 models
...
I/ModelManager: ========================================
I/ModelManager: Model loading complete!
I/ModelManager: Total models loaded: 100
I/ModelManager: Time taken: 1250ms
I/ModelManager: Average: 12ms per model
I/ModelManager: ========================================
```

使用以下命令过滤日志：
```bash
adb logcat -s SpatialPerfTest FPSMonitor ModelManager
```

## 模型排列算法

模型按照立方体网格排列：
- 计算 N 的立方根来确定基础维度
- 模型间距: X=0.3m, Y=0.3m, Z=0.3m
- 起始位置: 用户前方 2 米，略高于视线水平

例如，加载 100 个模型会创建约 5×5×4 的网格排列。

## 性能测试建议

1. **从少量开始**: 先从 10 个模型开始测试
2. **逐步增加**: 每次增加 20-50 个模型
3. **观察 FPS**: 当 FPS 下降到 30 以下时，记录模型数量
4. **对比测试**: 使用不同复杂度的模型进行对比
5. **记录结果**: 记录不同模型数量下的 FPS 数据

## 要求

- Android 14 (API 34) 或更高版本
- Android XR 兼容设备
- Android Studio Hedgehog 或更新版本

## 许可证

MIT License
