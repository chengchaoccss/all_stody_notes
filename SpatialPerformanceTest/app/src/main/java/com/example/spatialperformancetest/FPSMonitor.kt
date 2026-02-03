package com.example.spatialperformancetest

import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.Choreographer

/**
 * FPS Monitor class that tracks frame rate and logs it periodically.
 * Uses Choreographer to accurately measure frame rendering times.
 */
class FPSMonitor(
    private val logCallback: ((Double) -> Unit)? = null
) : Choreographer.FrameCallback {

    companion object {
        private const val TAG = "FPSMonitor"
        private const val LOG_INTERVAL_MS = 1000L // Log FPS every second
        private const val FRAME_TIME_SMOOTHING = 0.1 // Smoothing factor for FPS calculation
    }

    private val choreographer: Choreographer = Choreographer.getInstance()
    private val handler: Handler = Handler(Looper.getMainLooper())

    private var isRunning = false
    private var lastFrameTimeNanos = 0L
    private var frameCount = 0
    private var smoothedFps = 60.0

    private var fpsCallback: ((Double) -> Unit)? = null

    // Frame time tracking for more accurate FPS
    private val frameTimes = mutableListOf<Long>()
    private val maxFrameTimeSamples = 60

    private val logRunnable = object : Runnable {
        override fun run() {
            if (isRunning) {
                val currentFps = calculateFps()
                Log.i(TAG, "========================================")
                Log.i(TAG, "FPS: %.2f | Frame Count: %d | Smoothed FPS: %.2f".format(currentFps, frameCount, smoothedFps))
                Log.i(TAG, "========================================")

                logCallback?.invoke(smoothedFps)
                fpsCallback?.invoke(smoothedFps)

                frameCount = 0
                handler.postDelayed(this, LOG_INTERVAL_MS)
            }
        }
    }

    /**
     * Set callback for FPS updates (used by UI)
     */
    fun setFpsCallback(callback: (Double) -> Unit) {
        fpsCallback = callback
    }

    /**
     * Start FPS monitoring
     */
    fun start() {
        if (!isRunning) {
            isRunning = true
            lastFrameTimeNanos = System.nanoTime()
            frameCount = 0
            frameTimes.clear()
            choreographer.postFrameCallback(this)
            handler.postDelayed(logRunnable, LOG_INTERVAL_MS)
            Log.d(TAG, "FPS monitoring started")
        }
    }

    /**
     * Stop FPS monitoring
     */
    fun stop() {
        if (isRunning) {
            isRunning = false
            choreographer.removeFrameCallback(this)
            handler.removeCallbacks(logRunnable)
            Log.d(TAG, "FPS monitoring stopped")
        }
    }

    /**
     * Called every frame by Choreographer
     */
    override fun doFrame(frameTimeNanos: Long) {
        if (!isRunning) return

        frameCount++

        // Calculate frame time
        if (lastFrameTimeNanos > 0) {
            val frameTimeMs = (frameTimeNanos - lastFrameTimeNanos) / 1_000_000.0

            // Track frame times for averaging
            frameTimes.add((frameTimeNanos - lastFrameTimeNanos))
            if (frameTimes.size > maxFrameTimeSamples) {
                frameTimes.removeAt(0)
            }

            // Calculate instant FPS and apply smoothing
            val instantFps = 1000.0 / frameTimeMs
            smoothedFps = smoothedFps * (1 - FRAME_TIME_SMOOTHING) + instantFps * FRAME_TIME_SMOOTHING

            // Log warning for dropped frames (frame time > 32ms = below 30fps)
            if (frameTimeMs > 32) {
                Log.w(TAG, "Frame drop detected! Frame time: %.2f ms (%.1f FPS)".format(frameTimeMs, instantFps))
            }
        }

        lastFrameTimeNanos = frameTimeNanos

        // Request next frame
        choreographer.postFrameCallback(this)
    }

    /**
     * Calculate average FPS from recent frame times
     */
    private fun calculateFps(): Double {
        if (frameTimes.isEmpty()) return 0.0

        val avgFrameTimeNanos = frameTimes.average()
        return if (avgFrameTimeNanos > 0) {
            1_000_000_000.0 / avgFrameTimeNanos
        } else {
            0.0
        }
    }

    /**
     * Get current smoothed FPS value
     */
    fun getCurrentFps(): Double = smoothedFps

    /**
     * Get detailed FPS statistics
     */
    fun getStats(): FPSStats {
        if (frameTimes.isEmpty()) {
            return FPSStats(0.0, 0.0, 0.0, 0.0)
        }

        val frameTimesMs = frameTimes.map { it / 1_000_000.0 }
        val avgFrameTime = frameTimesMs.average()
        val minFrameTime = frameTimesMs.minOrNull() ?: 0.0
        val maxFrameTime = frameTimesMs.maxOrNull() ?: 0.0

        return FPSStats(
            averageFps = if (avgFrameTime > 0) 1000.0 / avgFrameTime else 0.0,
            minFps = if (maxFrameTime > 0) 1000.0 / maxFrameTime else 0.0,
            maxFps = if (minFrameTime > 0) 1000.0 / minFrameTime else 0.0,
            avgFrameTimeMs = avgFrameTime
        )
    }

    /**
     * Data class for FPS statistics
     */
    data class FPSStats(
        val averageFps: Double,
        val minFps: Double,
        val maxFps: Double,
        val avgFrameTimeMs: Double
    )
}
