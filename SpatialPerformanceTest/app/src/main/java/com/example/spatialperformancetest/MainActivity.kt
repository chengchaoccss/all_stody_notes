package com.example.spatialperformancetest

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.xr.compose.platform.LocalSession
import androidx.xr.compose.platform.LocalSpatialCapabilities
import androidx.xr.compose.spatial.Subspace
import androidx.xr.compose.subspace.SpatialPanel
import androidx.xr.compose.subspace.layout.SubspaceModifier
import androidx.xr.compose.subspace.layout.height
import androidx.xr.compose.subspace.layout.width
import androidx.xr.scenecore.Session
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
                    }
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
        Log.d(TAG, "FPS monitoring stopped")
    }

    override fun onDestroy() {
        super.onDestroy()
        modelManager?.clearAllModels()
        Log.d(TAG, "All models cleared")
    }
}

@Composable
fun SpatialPerformanceApp(
    fpsMonitor: FPSMonitor,
    onModelManagerCreated: (ModelManager) -> Unit
) {
    val spatialCapabilities = LocalSpatialCapabilities.current

    if (spatialCapabilities.isSpatialUiEnabled) {
        // Running in XR mode - use spatial UI
        SpatialContent(fpsMonitor, onModelManagerCreated)
    } else {
        // Fallback for non-XR mode
        NonSpatialContent(fpsMonitor)
    }
}

@Composable
fun SpatialContent(
    fpsMonitor: FPSMonitor,
    onModelManagerCreated: (ModelManager) -> Unit
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
                .width(600.dp)
                .height(400.dp)
        ) {
            ControlPanelContent(
                modelManager = modelManager,
                fpsMonitor = fpsMonitor
            )
        }
    }
}

@Composable
fun NonSpatialContent(fpsMonitor: FPSMonitor) {
    // Fallback UI for non-XR devices
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text(
                text = "Spatial Performance Test",
                style = MaterialTheme.typography.headlineMedium
            )
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "This app requires an XR device to run properly.",
                style = MaterialTheme.typography.bodyLarge
            )
            Text(
                text = "Please run on Android XR compatible device.",
                style = MaterialTheme.typography.bodyMedium
            )
        }
    }
}

@Composable
fun ControlPanelContent(
    modelManager: ModelManager?,
    fpsMonitor: FPSMonitor
) {
    var modelCount by remember { mutableStateOf("10") }
    var isLoading by remember { mutableStateOf(false) }
    var loadedCount by remember { mutableIntStateOf(0) }
    var currentFps by remember { mutableStateOf("--") }

    // Subscribe to FPS updates
    LaunchedEffect(fpsMonitor) {
        fpsMonitor.setFpsCallback { fps ->
            currentFps = String.format("%.1f", fps)
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
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Title
            Text(
                text = "🐔 Spatial Performance Test",
                style = MaterialTheme.typography.headlineMedium,
                color = MaterialTheme.colorScheme.primary
            )

            Spacer(modifier = Modifier.height(8.dp))

            // FPS Display
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Current FPS:",
                        style = MaterialTheme.typography.titleMedium
                    )
                    Text(
                        text = currentFps,
                        style = MaterialTheme.typography.headlineSmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }

            // Loaded models count
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.secondaryContainer
                )
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Loaded Models:",
                        style = MaterialTheme.typography.titleMedium
                    )
                    Text(
                        text = "$loadedCount",
                        style = MaterialTheme.typography.headlineSmall,
                        color = MaterialTheme.colorScheme.secondary
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Input field
            OutlinedTextField(
                value = modelCount,
                onValueChange = { newValue ->
                    // Only allow digits
                    if (newValue.all { it.isDigit() } || newValue.isEmpty()) {
                        modelCount = newValue
                    }
                },
                label = { Text("Number of Models") },
                placeholder = { Text("Enter model count (e.g., 100)") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                enabled = !isLoading
            )

            // Load button
            Button(
                onClick = {
                    val count = modelCount.toIntOrNull() ?: 0
                    if (count > 0 && modelManager != null) {
                        isLoading = true
                        CoroutineScope(Dispatchers.Main).launch {
                            modelManager.loadModels(count) { currentLoaded ->
                                loadedCount = currentLoaded
                            }
                            isLoading = false
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
                    loadedCount = 0
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isLoading && loadedCount > 0
            ) {
                Text("Clear All Models")
            }

            // Info text
            Text(
                text = "Models will be arranged in a 3D grid (X, Y, Z)",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
