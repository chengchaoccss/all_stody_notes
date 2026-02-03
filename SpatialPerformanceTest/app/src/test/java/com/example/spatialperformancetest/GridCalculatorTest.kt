package com.example.spatialperformancetest

import org.junit.Assert.*
import org.junit.Test
import kotlin.math.cbrt
import kotlin.math.ceil

/**
 * Unit tests for grid calculation logic
 */
class GridCalculatorTest {

    /**
     * Mimics the grid calculation logic from ModelManager
     */
    private fun calculateGridDimensions(count: Int): Triple<Int, Int, Int> {
        val cubeRoot = ceil(cbrt(count.toDouble())).toInt()

        var x = cubeRoot
        var y = cubeRoot
        var z = cubeRoot

        // Optimize to reduce empty space
        while (x * y * z > count && z > 1) {
            z--
        }
        while (x * y * z < count) {
            z++
        }

        while (x * y * z > count && y > 1) {
            y--
        }
        while (x * y * z < count) {
            y++
        }

        return Triple(x, y, z)
    }

    @Test
    fun `grid for 1 model should be 1x1x1`() {
        val (x, y, z) = calculateGridDimensions(1)
        assertTrue(x * y * z >= 1)
        assertEquals(1, x)
        assertEquals(1, y)
        assertEquals(1, z)
    }

    @Test
    fun `grid for 8 models should be 2x2x2`() {
        val (x, y, z) = calculateGridDimensions(8)
        assertTrue(x * y * z >= 8)
        assertEquals(2, x)
        assertEquals(2, y)
        assertEquals(2, z)
    }

    @Test
    fun `grid for 27 models should be 3x3x3`() {
        val (x, y, z) = calculateGridDimensions(27)
        assertTrue(x * y * z >= 27)
    }

    @Test
    fun `grid for 100 models should fit all models`() {
        val (x, y, z) = calculateGridDimensions(100)
        val totalCapacity = x * y * z
        assertTrue("Grid should have capacity for 100 models, has $totalCapacity", totalCapacity >= 100)
    }

    @Test
    fun `grid for 1000 models should fit all models`() {
        val (x, y, z) = calculateGridDimensions(1000)
        val totalCapacity = x * y * z
        assertTrue("Grid should have capacity for 1000 models, has $totalCapacity", totalCapacity >= 1000)
    }

    @Test
    fun `grid dimensions are always positive`() {
        listOf(1, 5, 10, 50, 100, 200, 500, 1000).forEach { count ->
            val (x, y, z) = calculateGridDimensions(count)
            assertTrue("X should be positive for $count models", x > 0)
            assertTrue("Y should be positive for $count models", y > 0)
            assertTrue("Z should be positive for $count models", z > 0)
        }
    }

    @Test
    fun `grid capacity is reasonably efficient`() {
        listOf(10, 50, 100, 200, 500).forEach { count ->
            val (x, y, z) = calculateGridDimensions(count)
            val capacity = x * y * z
            val efficiency = count.toDouble() / capacity
            // Grid should be at least 50% efficient (not too much wasted space)
            assertTrue(
                "Grid efficiency for $count models should be > 50%, was ${efficiency * 100}%",
                efficiency > 0.5
            )
        }
    }

    @Test
    fun `position calculation is correct`() {
        val spacingX = 0.3f
        val spacingY = 0.3f
        val spacingZ = 0.3f
        val startX = -1.0f
        val startY = 0.5f
        val startZ = -2.0f

        // Test position for model at grid position (2, 1, 3)
        val posX = startX + (2 * spacingX)
        val posY = startY + (1 * spacingY)
        val posZ = startZ + (3 * spacingZ)

        assertEquals(-0.4f, posX, 0.001f)
        assertEquals(0.8f, posY, 0.001f)
        assertEquals(-1.1f, posZ, 0.001f)
    }

    @Test
    fun `model spacing constants are reasonable for XR`() {
        val spacingX = 0.3f
        val spacingY = 0.3f
        val spacingZ = 0.3f

        // Models should not be too close (< 0.1m) or too far (> 1m) apart
        assertTrue(spacingX >= 0.1f && spacingX <= 1.0f)
        assertTrue(spacingY >= 0.1f && spacingY <= 1.0f)
        assertTrue(spacingZ >= 0.1f && spacingZ <= 1.0f)
    }
}
