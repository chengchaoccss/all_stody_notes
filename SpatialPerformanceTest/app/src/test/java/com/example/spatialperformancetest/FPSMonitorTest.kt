package com.example.spatialperformancetest

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for FPSMonitor class
 */
class FPSMonitorTest {

    @Test
    fun `FPSStats default values are zero`() {
        val stats = FPSMonitor.FPSStats(
            averageFps = 0.0,
            minFps = 0.0,
            maxFps = 0.0,
            avgFrameTimeMs = 0.0
        )

        assertEquals(0.0, stats.averageFps, 0.001)
        assertEquals(0.0, stats.minFps, 0.001)
        assertEquals(0.0, stats.maxFps, 0.001)
        assertEquals(0.0, stats.avgFrameTimeMs, 0.001)
    }

    @Test
    fun `FPSStats with valid values`() {
        val stats = FPSMonitor.FPSStats(
            averageFps = 60.0,
            minFps = 55.0,
            maxFps = 65.0,
            avgFrameTimeMs = 16.67
        )

        assertEquals(60.0, stats.averageFps, 0.001)
        assertEquals(55.0, stats.minFps, 0.001)
        assertEquals(65.0, stats.maxFps, 0.001)
        assertEquals(16.67, stats.avgFrameTimeMs, 0.001)
    }

    @Test
    fun `FPSStats equals and hashCode work correctly`() {
        val stats1 = FPSMonitor.FPSStats(60.0, 55.0, 65.0, 16.67)
        val stats2 = FPSMonitor.FPSStats(60.0, 55.0, 65.0, 16.67)
        val stats3 = FPSMonitor.FPSStats(30.0, 25.0, 35.0, 33.33)

        assertEquals(stats1, stats2)
        assertEquals(stats1.hashCode(), stats2.hashCode())
        assertNotEquals(stats1, stats3)
    }

    @Test
    fun `FPSStats toString contains all values`() {
        val stats = FPSMonitor.FPSStats(60.0, 55.0, 65.0, 16.67)
        val string = stats.toString()

        assertTrue(string.contains("60.0"))
        assertTrue(string.contains("55.0"))
        assertTrue(string.contains("65.0"))
        assertTrue(string.contains("16.67"))
    }

    @Test
    fun `FPSStats copy works correctly`() {
        val stats = FPSMonitor.FPSStats(60.0, 55.0, 65.0, 16.67)
        val copied = stats.copy(averageFps = 90.0)

        assertEquals(90.0, copied.averageFps, 0.001)
        assertEquals(55.0, copied.minFps, 0.001)
        assertEquals(65.0, copied.maxFps, 0.001)
        assertEquals(16.67, copied.avgFrameTimeMs, 0.001)
    }
}
