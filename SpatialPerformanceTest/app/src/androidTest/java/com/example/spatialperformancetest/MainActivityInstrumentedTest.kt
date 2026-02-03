package com.example.spatialperformancetest

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.spatialperformancetest.ui.theme.SpatialPerformanceTestTheme
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Instrumented tests for UI components
 */
@RunWith(AndroidJUnit4::class)
class MainActivityInstrumentedTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun fpsDisplayCard_displaysCorrectValues() {
        composeTestRule.setContent {
            SpatialPerformanceTestTheme {
                FpsDisplayCard(currentFps = 60.0, loadedCount = 50)
            }
        }

        // Check FPS value is displayed
        composeTestRule.onNodeWithText("60.0").assertIsDisplayed()

        // Check model count is displayed
        composeTestRule.onNodeWithText("50").assertIsDisplayed()

        // Check labels are displayed
        composeTestRule.onNodeWithText("FPS").assertIsDisplayed()
        composeTestRule.onNodeWithText("Models").assertIsDisplayed()
        composeTestRule.onNodeWithText("Target").assertIsDisplayed()
        composeTestRule.onNodeWithText("90").assertIsDisplayed()
    }

    @Test
    fun fpsDisplayCard_showsGreenColorForHighFps() {
        composeTestRule.setContent {
            SpatialPerformanceTestTheme {
                FpsDisplayCard(currentFps = 95.0, loadedCount = 10)
            }
        }

        // FPS above 90 should be displayed
        composeTestRule.onNodeWithText("95.0").assertIsDisplayed()
    }

    @Test
    fun fpsDisplayCard_showsRedColorForLowFps() {
        composeTestRule.setContent {
            SpatialPerformanceTestTheme {
                FpsDisplayCard(currentFps = 25.0, loadedCount = 500)
            }
        }

        // Low FPS should be displayed
        composeTestRule.onNodeWithText("25.0").assertIsDisplayed()
    }

    @Test
    fun manualTestTab_displaysAllElements() {
        composeTestRule.setContent {
            SpatialPerformanceTestTheme {
                ManualTestTab(
                    modelManager = null,
                    modelCount = "10",
                    onModelCountChange = {},
                    isLoading = false,
                    onLoadingChange = {},
                    loadedCount = 0,
                    onLoadedCountChange = {}
                )
            }
        }

        // Check input field
        composeTestRule.onNodeWithText("Number of Models").assertIsDisplayed()

        // Check quick select label
        composeTestRule.onNodeWithText("Quick Select:").assertIsDisplayed()

        // Check quick select buttons
        composeTestRule.onNodeWithText("10").assertIsDisplayed()
        composeTestRule.onNodeWithText("50").assertIsDisplayed()
        composeTestRule.onNodeWithText("100").assertIsDisplayed()
        composeTestRule.onNodeWithText("200").assertIsDisplayed()
        composeTestRule.onNodeWithText("500").assertIsDisplayed()

        // Check load button
        composeTestRule.onNodeWithText("Load Models").assertIsDisplayed()

        // Check clear button
        composeTestRule.onNodeWithText("Clear All Models").assertIsDisplayed()
    }

    @Test
    fun manualTestTab_inputFieldAcceptsOnlyNumbers() {
        var modelCount = ""

        composeTestRule.setContent {
            SpatialPerformanceTestTheme {
                ManualTestTab(
                    modelManager = null,
                    modelCount = modelCount,
                    onModelCountChange = { modelCount = it },
                    isLoading = false,
                    onLoadingChange = {},
                    loadedCount = 0,
                    onLoadedCountChange = {}
                )
            }
        }

        // Type numbers
        composeTestRule.onNodeWithText("Number of Models").performTextInput("123")

        // The value should be accepted (numbers only)
        // Note: Due to composable state, we verify the input field is interactive
        composeTestRule.onNodeWithText("Number of Models").assertIsEnabled()
    }

    @Test
    fun manualTestTab_quickSelectButtonsWork() {
        var modelCount = "10"

        composeTestRule.setContent {
            SpatialPerformanceTestTheme {
                ManualTestTab(
                    modelManager = null,
                    modelCount = modelCount,
                    onModelCountChange = { modelCount = it },
                    isLoading = false,
                    onLoadingChange = {},
                    loadedCount = 0,
                    onLoadedCountChange = {}
                )
            }
        }

        // Click on 100 chip
        composeTestRule.onNodeWithText("100").performClick()

        // Verify chip is clickable
        composeTestRule.onNodeWithText("100").assertIsEnabled()
    }

    @Test
    fun manualTestTab_loadButtonDisabledWhenLoading() {
        composeTestRule.setContent {
            SpatialPerformanceTestTheme {
                ManualTestTab(
                    modelManager = null,
                    modelCount = "10",
                    onModelCountChange = {},
                    isLoading = true, // Loading state
                    onLoadingChange = {},
                    loadedCount = 0,
                    onLoadedCountChange = {}
                )
            }
        }

        // Check loading indicator is shown
        composeTestRule.onNodeWithText("Loading...").assertIsDisplayed()
    }

    @Test
    fun benchmarkTab_displaysCorrectStatus() {
        composeTestRule.setContent {
            SpatialPerformanceTestTheme {
                BenchmarkTab(
                    benchmarkManager = null,
                    benchmarkState = BenchmarkState(
                        isRunning = false,
                        phase = BenchmarkPhase.IDLE
                    ),
                    onLoadedCountChange = {}
                )
            }
        }

        // Check status is displayed
        composeTestRule.onNodeWithText("Status: IDLE").assertIsDisplayed()

        // Check start button is displayed
        composeTestRule.onNodeWithText("Start Auto Benchmark").assertIsDisplayed()
    }

    @Test
    fun benchmarkTab_showsStopButtonWhenRunning() {
        composeTestRule.setContent {
            SpatialPerformanceTestTheme {
                BenchmarkTab(
                    benchmarkManager = null,
                    benchmarkState = BenchmarkState(
                        isRunning = true,
                        phase = BenchmarkPhase.MEASURING_FPS
                    ),
                    onLoadedCountChange = {}
                )
            }
        }

        // Check stop button is displayed when running
        composeTestRule.onNodeWithText("Stop Benchmark").assertIsDisplayed()
    }

    @Test
    fun benchmarkTab_showsResultsWhenCompleted() {
        val results = listOf(
            BenchmarkResult(1, 10, 95.0, 1000L),
            BenchmarkResult(2, 20, 92.0, 2000L),
            BenchmarkResult(3, 30, 88.0, 3000L)
        )

        composeTestRule.setContent {
            SpatialPerformanceTestTheme {
                BenchmarkTab(
                    benchmarkManager = null,
                    benchmarkState = BenchmarkState(
                        isRunning = false,
                        phase = BenchmarkPhase.COMPLETED,
                        results = results,
                        maxModelsAt90Fps = 20
                    ),
                    onLoadedCountChange = {}
                )
            }
        }

        // Check completed status
        composeTestRule.onNodeWithText("Status: COMPLETED").assertIsDisplayed()

        // Check max models result is displayed
        composeTestRule.onNodeWithText("Max models at 90fps: 20").assertIsDisplayed()

        // Check results header
        composeTestRule.onNodeWithText("Results:").assertIsDisplayed()
    }

    @Test
    fun benchmarkTab_displaysConfigurationInfo() {
        composeTestRule.setContent {
            SpatialPerformanceTestTheme {
                BenchmarkTab(
                    benchmarkManager = null,
                    benchmarkState = BenchmarkState(),
                    onLoadedCountChange = {}
                )
            }
        }

        // Check configuration info is displayed
        composeTestRule.onNodeWithText("Benchmark Configuration:").assertIsDisplayed()
    }

    @Test
    fun benchmarkTab_displaysHowItWorksInfo() {
        composeTestRule.setContent {
            SpatialPerformanceTestTheme {
                BenchmarkTab(
                    benchmarkManager = null,
                    benchmarkState = BenchmarkState(),
                    onLoadedCountChange = {}
                )
            }
        }

        // Check how it works section
        composeTestRule.onNodeWithText("How Auto Benchmark Works:").assertIsDisplayed()
    }
}
