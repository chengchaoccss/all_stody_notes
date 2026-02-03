package com.example.spatialperformancetest

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.xr.compose.platform.LocalSession
import androidx.xr.compose.platform.LocalSpatialCapabilities
import androidx.xr.compose.spatial.Subspace
import androidx.xr.compose.subspace.SpatialPanel
import androidx.xr.compose.subspace.layout.SubspaceModifier
import androidx.xr.compose.subspace.layout.height
import androidx.xr.compose.subspace.layout.width
import com.example.spatialperformancetest.ui.theme.SpatialPerformanceTestTheme
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    companion object {
        private const val TAG = "SpatialPerfTest"
    }

    private lateinit var fpsMonitor: FPSMonitor
    private var modelManager: ModelManager? = null
    private var benchmarkManager: BenchmarkManager? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        Log.d(TAG, "MainActivity onCreate")

        // Initialize FPS monitor
        fpsMonitor = FPSMonitor { fps ->
            Log.d(TAG, "Current FPS: $fps")
        }

        setContent {
            SpatialPerformanceTestTheme {
                SpatialPerformanceApp(
                    fpsMonitor = fpsMonitor,
                    onModelManagerCreated = { manager ->
                        modelManager = manager
                        // Create benchmark manager when model manager is available
                        benchmarkManager = BenchmarkManager(fpsMonitor, manager)
                    },
                    getBenchmarkManager = { benchmarkManager }
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        fpsMonitor.start()
        Log.d(TAG, "FPS monitoring started")
    }

    override fun onPause() {
        super.onPause()
        fpsMonitor.stop()
        benchmarkManager?.stopBenchmark()
        Log.d(TAG, "FPS monitoring stopped")
    }

    override fun onDestroy() {
        super.onDestroy()
        benchmarkManager?.destroy()
        modelManager?.clearAllModels()
        Log.d(TAG, "All models cleared")
    }
}

@Composable
fun SpatialPerformanceApp(
    fpsMonitor: FPSMonitor,
    onModelManagerCreated: (ModelManager) -> Unit,
    getBenchmarkManager: () -> BenchmarkManager?
) {
    val spatialCapabilities = LocalSpatialCapabilities.current

    if (spatialCapabilities.isSpatialUiEnabled) {
        // Running in XR mode - use spatial UI
        SpatialContent(fpsMonitor, onModelManagerCreated, getBenchmarkManager)
    } else {
        // Fallback for non-XR mode
        NonSpatialContent(fpsMonitor, onModelManagerCreated, getBenchmarkManager)
    }
}

@Composable
fun SpatialContent(
    fpsMonitor: FPSMonitor,
    onModelManagerCreated: (ModelManager) -> Unit,
    getBenchmarkManager: () -> BenchmarkManager?
) {
    val session = LocalSession.current

    // Create ModelManager when session is available
    val modelManager = remember(session) {
        session?.let {
            ModelManager(it).also { manager ->
                onModelManagerCreated(manager)
            }
        }
    }

    Subspace {
        // Main control panel
        SpatialPanel(
            SubspaceModifier
                .width(700.dp)
                .height(800.dp)
        ) {
            ControlPanelContent(
                modelManager = modelManager,
                fpsMonitor = fpsMonitor,
                getBenchmarkManager = getBenchmarkManager
            )
        }
    }
}

@Composable
fun NonSpatialContent(
    fpsMonitor: FPSMonitor,
    onModelManagerCreated: (ModelManager) -> Unit,
    getBenchmarkManager: () -> BenchmarkManager?
) {
    // Fallback UI for non-XR devices - still show the control panel
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        ControlPanelContent(
            modelManager = null,
            fpsMonitor = fpsMonitor,
            getBenchmarkManager = getBenchmarkManager
        )
    }
}

@Composable
fun ControlPanelContent(
    modelManager: ModelManager?,
    fpsMonitor: FPSMonitor,
    getBenchmarkManager: () -> BenchmarkManager?
) {
    var modelCount by remember { mutableStateOf("10") }
    var isLoading by remember { mutableStateOf(false) }
    var loadedCount by remember { mutableIntStateOf(0) }
    var currentFps by remember { mutableDoubleStateOf(0.0) }
    var selectedTab by remember { mutableIntStateOf(0) }

    // Benchmark state
    val benchmarkManager = getBenchmarkManager()
    val benchmarkState by benchmarkManager?.benchmarkState?.collectAsState()
        ?: remember { mutableStateOf(BenchmarkState()) }

    // Subscribe to FPS updates
    LaunchedEffect(fpsMonitor) {
        fpsMonitor.setFpsCallback { fps ->
            currentFps = fps
        }
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.surface.copy(alpha = 0.95f),
        shape = MaterialTheme.shapes.large
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp)
        ) {
            // Title
            Text(
                text = "Spatial Performance Test",
                style = MaterialTheme.typography.headlineMedium,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.padding(bottom = 8.dp)
            )

            // FPS Display Card
            FpsDisplayCard(currentFps = currentFps, loadedCount = loadedCount)

            Spacer(modifier = Modifier.height(12.dp))

            // Tab Row
            TabRow(
                selectedTabIndex = selectedTab,
                modifier = Modifier.fillMaxWidth()
            ) {
                Tab(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    text = { Text("Manual Test") }
                )
                Tab(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    text = { Text("Auto Benchmark") }
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Content based on selected tab
            when (selectedTab) {
                0 -> ManualTestTab(
                    modelManager = modelManager,
                    modelCount = modelCount,
                    onModelCountChange = { modelCount = it },
                    isLoading = isLoading,
                    onLoadingChange = { isLoading = it },
                    loadedCount = loadedCount,
                    onLoadedCountChange = { loadedCount = it }
                )
                1 -> BenchmarkTab(
                    benchmarkManager = benchmarkManager,
                    benchmarkState = benchmarkState,
                    onLoadedCountChange = { loadedCount = it }
                )
            }
        }
    }
}

@Composable
fun FpsDisplayCard(currentFps: Double, loadedCount: Int) {
    val fpsColor = when {
        currentFps >= 90 -> Color(0xFF4CAF50) // Green
        currentFps >= 60 -> Color(0xFFFFC107) // Yellow
        currentFps >= 30 -> Color(0xFFFF9800) // Orange
        else -> Color(0xFFF44336) // Red
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = "FPS",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "%.1f".format(currentFps),
                    style = MaterialTheme.typography.headlineLarge,
                    fontWeight = FontWeight.Bold,
                    color = fpsColor
                )
            }

            Divider(
                modifier = Modifier
                    .height(50.dp)
                    .width(1.dp),
                color = MaterialTheme.colorScheme.outline
            )

            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = "Models",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "$loadedCount",
                    style = MaterialTheme.typography.headlineLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            Divider(
                modifier = Modifier
                    .height(50.dp)
                    .width(1.dp),
                color = MaterialTheme.colorScheme.outline
            )

            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = "Target",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = "90",
                    style = MaterialTheme.typography.headlineLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.secondary
                )
            }
        }
    }
}

@Composable
fun ManualTestTab(
    modelManager: ModelManager?,
    modelCount: String,
    onModelCountChange: (String) -> Unit,
    isLoading: Boolean,
    onLoadingChange: (Boolean) -> Unit,
    loadedCount: Int,
    onLoadedCountChange: (Int) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Input field
        OutlinedTextField(
            value = modelCount,
            onValueChange = { newValue ->
                if (newValue.all { it.isDigit() } || newValue.isEmpty()) {
                    onModelCountChange(newValue)
                }
            },
            label = { Text("Number of Models") },
            placeholder = { Text("Enter model count (e.g., 100)") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !isLoading
        )

        // Quick select buttons
        Text(
            text = "Quick Select:",
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            listOf("10", "50", "100", "200", "500").forEach { count ->
                FilterChip(
                    selected = modelCount == count,
                    onClick = { onModelCountChange(count) },
                    label = { Text(count) },
                    enabled = !isLoading
                )
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Load button
        Button(
            onClick = {
                val count = modelCount.toIntOrNull() ?: 0
                if (count > 0 && modelManager != null) {
                    onLoadingChange(true)
                    CoroutineScope(Dispatchers.Main).launch {
                        modelManager.clearAllModels()
                        modelManager.loadModels(count) { currentLoaded ->
                            onLoadedCountChange(currentLoaded)
                        }
                        onLoadingChange(false)
                    }
                }
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            enabled = !isLoading && modelCount.isNotEmpty() && modelManager != null
        ) {
            if (isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(24.dp),
                    color = MaterialTheme.colorScheme.onPrimary
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Loading...")
            } else {
                Text("Load Models")
            }
        }

        // Clear button
        OutlinedButton(
            onClick = {
                modelManager?.clearAllModels()
                onLoadedCountChange(0)
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading && loadedCount > 0
        ) {
            Text("Clear All Models")
        }

        // Info card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.tertiaryContainer
            )
        ) {
            Column(
                modifier = Modifier.padding(12.dp)
            ) {
                Text(
                    text = "How it works:",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "- Models are arranged in a 3D grid (X, Y, Z)\n" +
                            "- Watch the FPS counter as models load\n" +
                            "- Target: 90 FPS for smooth XR experience",
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }
    }
}

@Composable
fun BenchmarkTab(
    benchmarkManager: BenchmarkManager?,
    benchmarkState: BenchmarkState,
    onLoadedCountChange: (Int) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Benchmark status card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = when (benchmarkState.phase) {
                    BenchmarkPhase.COMPLETED -> MaterialTheme.colorScheme.primaryContainer
                    BenchmarkPhase.ERROR -> MaterialTheme.colorScheme.errorContainer
                    BenchmarkPhase.IDLE, BenchmarkPhase.STOPPED -> MaterialTheme.colorScheme.surfaceVariant
                    else -> MaterialTheme.colorScheme.secondaryContainer
                }
            )
        ) {
            Column(
                modifier = Modifier.padding(16.dp)
            ) {
                Text(
                    text = "Status: ${benchmarkState.phase.name}",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )

                if (benchmarkState.isRunning) {
                    Spacer(modifier = Modifier.height(8.dp))
                    LinearProgressIndicator(
                        modifier = Modifier.fillMaxWidth()
                    )

                    if (benchmarkState.timeToNextIteration > 0) {
                        Text(
                            text = "Next iteration in: ${benchmarkState.timeToNextIteration / 1000}s",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }

                if (benchmarkState.phase == BenchmarkPhase.COMPLETED) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Max models at 90fps: ${benchmarkState.maxModelsAt90Fps}",
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.primary
                    )
                }

                benchmarkState.errorMessage?.let { error ->
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Error: $error",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error
                    )
                }
            }
        }

        // Configuration info
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant
            )
        ) {
            Column(
                modifier = Modifier.padding(12.dp)
            ) {
                Text(
                    text = "Benchmark Configuration:",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "- Target FPS: ${BenchmarkManager.TARGET_FPS}\n" +
                            "- Interval: ${BenchmarkManager.INTERVAL_MS / 1000}s (2 minutes)\n" +
                            "- Model increment: +${BenchmarkManager.MODEL_INCREMENT} per iteration\n" +
                            "- Starting models: ${BenchmarkManager.INITIAL_MODEL_COUNT}",
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }

        // Start/Stop button
        if (benchmarkState.isRunning) {
            Button(
                onClick = { benchmarkManager?.stopBenchmark() },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.error
                )
            ) {
                Text("Stop Benchmark")
            }
        } else {
            Button(
                onClick = {
                    benchmarkManager?.startBenchmark()
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                enabled = benchmarkManager != null
            ) {
                Text("Start Auto Benchmark")
            }
        }

        // Results table
        if (benchmarkState.results.isNotEmpty()) {
            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(12.dp)
                ) {
                    Text(
                        text = "Results:",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    // Header row
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "#",
                            style = MaterialTheme.typography.labelMedium,
                            modifier = Modifier.weight(0.15f)
                        )
                        Text(
                            text = "Models",
                            style = MaterialTheme.typography.labelMedium,
                            modifier = Modifier.weight(0.35f)
                        )
                        Text(
                            text = "FPS",
                            style = MaterialTheme.typography.labelMedium,
                            modifier = Modifier.weight(0.35f)
                        )
                        Text(
                            text = "Status",
                            style = MaterialTheme.typography.labelMedium,
                            modifier = Modifier.weight(0.15f)
                        )
                    }

                    HorizontalDivider(modifier = Modifier.padding(vertical = 4.dp))

                    // Result rows
                    benchmarkState.results.forEach { result ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "${result.iteration}",
                                style = MaterialTheme.typography.bodySmall,
                                modifier = Modifier.weight(0.15f)
                            )
                            Text(
                                text = "${result.modelCount}",
                                style = MaterialTheme.typography.bodySmall,
                                modifier = Modifier.weight(0.35f)
                            )
                            Text(
                                text = "%.1f".format(result.averageFps),
                                style = MaterialTheme.typography.bodySmall,
                                color = if (result.averageFps >= BenchmarkManager.TARGET_FPS)
                                    Color(0xFF4CAF50) else Color(0xFFF44336),
                                modifier = Modifier.weight(0.35f)
                            )
                            Text(
                                text = if (result.averageFps >= BenchmarkManager.TARGET_FPS) "OK" else "X",
                                style = MaterialTheme.typography.bodySmall,
                                color = if (result.averageFps >= BenchmarkManager.TARGET_FPS)
                                    Color(0xFF4CAF50) else Color(0xFFF44336),
                                modifier = Modifier.weight(0.15f)
                            )
                        }
                    }
                }
            }
        }

        // Info text
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.tertiaryContainer
            )
        ) {
            Column(
                modifier = Modifier.padding(12.dp)
            ) {
                Text(
                    text = "How Auto Benchmark Works:",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "1. Starts with ${BenchmarkManager.INITIAL_MODEL_COUNT} models\n" +
                            "2. Measures average FPS for 5 seconds\n" +
                            "3. Waits 2 minutes between iterations\n" +
                            "4. Adds ${BenchmarkManager.MODEL_INCREMENT} models each iteration\n" +
                            "5. Stops when FPS drops below ${BenchmarkManager.TARGET_FPS}",
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }
    }
}
