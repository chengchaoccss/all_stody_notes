package com.example.spatialperformancetest

import org.junit.Assert.*
import org.junit.Test

/**
 * Unit tests for BenchmarkManager related classes
 */
class BenchmarkManagerTest {

    @Test
    fun `BenchmarkResult stores correct values`() {
        val result = BenchmarkResult(
            iteration = 1,
            modelCount = 100,
            averageFps = 60.0,
            timestamp = 1234567890L
        )

        assertEquals(1, result.iteration)
        assertEquals(100, result.modelCount)
        assertEquals(60.0, result.averageFps, 0.001)
        assertEquals(1234567890L, result.timestamp)
    }

    @Test
    fun `BenchmarkResult equals and hashCode work correctly`() {
        val result1 = BenchmarkResult(1, 100, 60.0, 1234567890L)
        val result2 = BenchmarkResult(1, 100, 60.0, 1234567890L)
        val result3 = BenchmarkResult(2, 200, 55.0, 1234567891L)

        assertEquals(result1, result2)
        assertEquals(result1.hashCode(), result2.hashCode())
        assertNotEquals(result1, result3)
    }

    @Test
    fun `BenchmarkState default values are correct`() {
        val state = BenchmarkState()

        assertFalse(state.isRunning)
        assertEquals(0, state.currentModelCount)
        assertEquals(0.0, state.currentFps, 0.001)
        assertEquals(BenchmarkPhase.IDLE, state.phase)
        assertTrue(state.results.isEmpty())
        assertEquals(0, state.maxModelsAt90Fps)
        assertEquals(0L, state.timeToNextIteration)
        assertNull(state.errorMessage)
    }

    @Test
    fun `BenchmarkState copy works correctly`() {
        val state = BenchmarkState()
        val updatedState = state.copy(
            isRunning = true,
            currentModelCount = 50,
            phase = BenchmarkPhase.LOADING_MODELS
        )

        assertTrue(updatedState.isRunning)
        assertEquals(50, updatedState.currentModelCount)
        assertEquals(BenchmarkPhase.LOADING_MODELS, updatedState.phase)
        // Unchanged values
        assertEquals(0.0, updatedState.currentFps, 0.001)
        assertTrue(updatedState.results.isEmpty())
    }

    @Test
    fun `BenchmarkPhase enum has all expected values`() {
        val phases = BenchmarkPhase.values()

        assertEquals(8, phases.size)
        assertTrue(phases.contains(BenchmarkPhase.IDLE))
        assertTrue(phases.contains(BenchmarkPhase.INITIALIZING))
        assertTrue(phases.contains(BenchmarkPhase.LOADING_MODELS))
        assertTrue(phases.contains(BenchmarkPhase.MEASURING_FPS))
        assertTrue(phases.contains(BenchmarkPhase.WAITING))
        assertTrue(phases.contains(BenchmarkPhase.COMPLETED))
        assertTrue(phases.contains(BenchmarkPhase.STOPPED))
        assertTrue(phases.contains(BenchmarkPhase.ERROR))
    }

    @Test
    fun `BenchmarkManager constants have correct values`() {
        assertEquals(90.0, BenchmarkManager.TARGET_FPS, 0.001)
        assertEquals(2 * 60 * 1000L, BenchmarkManager.INTERVAL_MS)
        assertEquals(10, BenchmarkManager.MODEL_INCREMENT)
        assertEquals(10, BenchmarkManager.INITIAL_MODEL_COUNT)
        assertEquals(5000L, BenchmarkManager.FPS_SAMPLE_DURATION_MS)
        assertEquals(100L, BenchmarkManager.FPS_SAMPLE_INTERVAL_MS)
    }

    @Test
    fun `BenchmarkState with results list`() {
        val results = listOf(
            BenchmarkResult(1, 10, 90.0, 1000L),
            BenchmarkResult(2, 20, 85.0, 2000L),
            BenchmarkResult(3, 30, 75.0, 3000L)
        )

        val state = BenchmarkState(
            isRunning = false,
            currentModelCount = 30,
            currentFps = 75.0,
            phase = BenchmarkPhase.COMPLETED,
            results = results,
            maxModelsAt90Fps = 20
        )

        assertEquals(3, state.results.size)
        assertEquals(20, state.maxModelsAt90Fps)
        assertEquals(BenchmarkPhase.COMPLETED, state.phase)
    }

    @Test
    fun `BenchmarkResult with high FPS should pass 90fps threshold`() {
        val result = BenchmarkResult(1, 50, 95.0, System.currentTimeMillis())
        assertTrue(result.averageFps >= BenchmarkManager.TARGET_FPS)
    }

    @Test
    fun `BenchmarkResult with low FPS should fail 90fps threshold`() {
        val result = BenchmarkResult(1, 200, 85.0, System.currentTimeMillis())
        assertFalse(result.averageFps >= BenchmarkManager.TARGET_FPS)
    }
}
