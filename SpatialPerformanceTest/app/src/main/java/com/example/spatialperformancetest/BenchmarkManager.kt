package com.example.spatialperformancetest

import android.util.Log
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Benchmark Manager for automated performance testing.
 * Automatically increases model count every 2 minutes until FPS drops below 90.
 */
class BenchmarkManager(
    private val fpsMonitor: FPSMonitor,
    private val modelManager: ModelManager?
) {
    companion object {
        private const val TAG = "BenchmarkManager"

        // Benchmark configuration
        const val TARGET_FPS = 90.0
        const val INTERVAL_MS = 2 * 60 * 1000L // 2 minutes
        const val MODEL_INCREMENT = 10 // Add 10 models each interval
        const val INITIAL_MODEL_COUNT = 10
        const val FPS_SAMPLE_DURATION_MS = 5000L // Sample FPS for 5 seconds before deciding
        const val FPS_SAMPLE_INTERVAL_MS = 100L
    }

    // Benchmark state
    private val _benchmarkState = MutableStateFlow(BenchmarkState())
    val benchmarkState: StateFlow<BenchmarkState> = _benchmarkState.asStateFlow()

    private var benchmarkJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    /**
     * Start the automated benchmark test
     */
    fun startBenchmark() {
        if (_benchmarkState.value.isRunning) {
            Log.w(TAG, "Benchmark is already running")
            return
        }

        Log.i(TAG, "========================================")
        Log.i(TAG, "Starting Automated Benchmark")
        Log.i(TAG, "Target FPS: $TARGET_FPS")
        Log.i(TAG, "Interval: ${INTERVAL_MS / 1000}s")
        Log.i(TAG, "Model Increment: $MODEL_INCREMENT")
        Log.i(TAG, "========================================")

        _benchmarkState.value = BenchmarkState(
            isRunning = true,
            currentModelCount = 0,
            currentFps = 0.0,
            phase = BenchmarkPhase.INITIALIZING,
            results = mutableListOf()
        )

        benchmarkJob = scope.launch {
            runBenchmark()
        }
    }

    /**
     * Stop the benchmark test
     */
    fun stopBenchmark() {
        Log.i(TAG, "Stopping benchmark...")
        benchmarkJob?.cancel()
        benchmarkJob = null

        _benchmarkState.value = _benchmarkState.value.copy(
            isRunning = false,
            phase = BenchmarkPhase.STOPPED
        )

        printFinalResults()
    }

    /**
     * Main benchmark loop
     */
    private suspend fun runBenchmark() {
        var currentCount = INITIAL_MODEL_COUNT
        var iteration = 0

        try {
            while (_benchmarkState.value.isRunning) {
                iteration++

                Log.i(TAG, "----------------------------------------")
                Log.i(TAG, "Benchmark Iteration #$iteration")
                Log.i(TAG, "Loading $currentCount models...")
                Log.i(TAG, "----------------------------------------")

                // Update state - loading phase
                _benchmarkState.value = _benchmarkState.value.copy(
                    phase = BenchmarkPhase.LOADING_MODELS,
                    currentModelCount = currentCount
                )

                // Clear existing models and load new count
                modelManager?.clearAllModels()
                delay(500) // Allow cleanup

                // Load models
                modelManager?.loadModels(currentCount) { loaded ->
                    _benchmarkState.value = _benchmarkState.value.copy(
                        currentModelCount = loaded
                    )
                }

                // Update state - measuring phase
                _benchmarkState.value = _benchmarkState.value.copy(
                    phase = BenchmarkPhase.MEASURING_FPS
                )

                // Wait for rendering to stabilize
                delay(2000)

                // Sample FPS over the duration
                val averageFps = sampleFps()

                Log.i(TAG, "Model Count: $currentCount | Average FPS: %.2f".format(averageFps))

                // Record result
                val result = BenchmarkResult(
                    iteration = iteration,
                    modelCount = currentCount,
                    averageFps = averageFps,
                    timestamp = System.currentTimeMillis()
                )

                val updatedResults = _benchmarkState.value.results.toMutableList()
                updatedResults.add(result)

                _benchmarkState.value = _benchmarkState.value.copy(
                    currentFps = averageFps,
                    results = updatedResults
                )

                // Check if FPS dropped below target
                if (averageFps < TARGET_FPS) {
                    Log.i(TAG, "========================================")
                    Log.i(TAG, "BENCHMARK COMPLETE!")
                    Log.i(TAG, "FPS dropped below $TARGET_FPS at $currentCount models")
                    Log.i(TAG, "Final FPS: %.2f".format(averageFps))
                    Log.i(TAG, "========================================")

                    _benchmarkState.value = _benchmarkState.value.copy(
                        isRunning = false,
                        phase = BenchmarkPhase.COMPLETED,
                        maxModelsAt90Fps = currentCount - MODEL_INCREMENT
                    )

                    printFinalResults()
                    return
                }

                // Update state - waiting phase
                _benchmarkState.value = _benchmarkState.value.copy(
                    phase = BenchmarkPhase.WAITING
                )

                // Wait for 2 minutes before next iteration
                Log.i(TAG, "Waiting ${INTERVAL_MS / 1000} seconds before next iteration...")

                val waitStartTime = System.currentTimeMillis()
                while (System.currentTimeMillis() - waitStartTime < INTERVAL_MS) {
                    if (!_benchmarkState.value.isRunning) return

                    val remaining = INTERVAL_MS - (System.currentTimeMillis() - waitStartTime)
                    _benchmarkState.value = _benchmarkState.value.copy(
                        timeToNextIteration = remaining
                    )
                    delay(1000)
                }

                // Increase model count for next iteration
                currentCount += MODEL_INCREMENT
            }
        } catch (e: CancellationException) {
            Log.d(TAG, "Benchmark cancelled")
        } catch (e: Exception) {
            Log.e(TAG, "Benchmark error: ${e.message}", e)
            _benchmarkState.value = _benchmarkState.value.copy(
                isRunning = false,
                phase = BenchmarkPhase.ERROR,
                errorMessage = e.message
            )
        }
    }

    /**
     * Sample FPS over a duration and return the average
     */
    private suspend fun sampleFps(): Double {
        val samples = mutableListOf<Double>()
        val startTime = System.currentTimeMillis()

        while (System.currentTimeMillis() - startTime < FPS_SAMPLE_DURATION_MS) {
            samples.add(fpsMonitor.getCurrentFps())
            delay(FPS_SAMPLE_INTERVAL_MS)
        }

        return if (samples.isNotEmpty()) {
            samples.average()
        } else {
            fpsMonitor.getCurrentFps()
        }
    }

    /**
     * Print final benchmark results to log
     */
    private fun printFinalResults() {
        val state = _benchmarkState.value
        val results = state.results

        Log.i(TAG, "")
        Log.i(TAG, "╔══════════════════════════════════════════════════════════════╗")
        Log.i(TAG, "║              BENCHMARK RESULTS SUMMARY                       ║")
        Log.i(TAG, "╠══════════════════════════════════════════════════════════════╣")
        Log.i(TAG, "║ Target FPS: $TARGET_FPS                                              ║")
        Log.i(TAG, "║ Max Models at ${TARGET_FPS}fps: ${state.maxModelsAt90Fps}                              ║")
        Log.i(TAG, "╠══════════════════════════════════════════════════════════════╣")
        Log.i(TAG, "║  Iteration  │  Models  │    FPS                              ║")
        Log.i(TAG, "╠══════════════════════════════════════════════════════════════╣")

        results.forEach { result ->
            val fpsStr = "%.2f".format(result.averageFps)
            val indicator = if (result.averageFps >= TARGET_FPS) "✓" else "✗"
            Log.i(TAG, "║     ${result.iteration.toString().padStart(2)}      │   ${result.modelCount.toString().padStart(4)}   │  $fpsStr $indicator                     ║")
        }

        Log.i(TAG, "╚══════════════════════════════════════════════════════════════╝")
        Log.i(TAG, "")
    }

    /**
     * Clean up resources
     */
    fun destroy() {
        benchmarkJob?.cancel()
        scope.cancel()
    }
}

/**
 * Benchmark state data class
 */
data class BenchmarkState(
    val isRunning: Boolean = false,
    val currentModelCount: Int = 0,
    val currentFps: Double = 0.0,
    val phase: BenchmarkPhase = BenchmarkPhase.IDLE,
    val results: List<BenchmarkResult> = emptyList(),
    val maxModelsAt90Fps: Int = 0,
    val timeToNextIteration: Long = 0,
    val errorMessage: String? = null
)

/**
 * Benchmark phase enum
 */
enum class BenchmarkPhase {
    IDLE,
    INITIALIZING,
    LOADING_MODELS,
    MEASURING_FPS,
    WAITING,
    COMPLETED,
    STOPPED,
    ERROR
}

/**
 * Individual benchmark result
 */
data class BenchmarkResult(
    val iteration: Int,
    val modelCount: Int,
    val averageFps: Double,
    val timestamp: Long
)
