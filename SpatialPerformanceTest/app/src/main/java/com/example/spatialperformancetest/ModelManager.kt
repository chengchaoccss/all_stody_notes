package com.example.spatialperformancetest

import android.util.Log
import androidx.xr.scenecore.Entity
import androidx.xr.scenecore.GltfModel
import androidx.xr.scenecore.GltfModelEntity
import androidx.xr.scenecore.Session
import androidx.xr.runtime.math.Pose
import androidx.xr.runtime.math.Vector3
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlin.math.cbrt
import kotlin.math.ceil

/**
 * Manages 3D model loading and spatial arrangement for performance testing.
 * Models are arranged in a 3D grid pattern along X, Y, Z axes.
 */
class ModelManager(private val session: Session) {

    companion object {
        private const val TAG = "ModelManager"

        // Model spacing in meters
        private const val MODEL_SPACING_X = 0.3f
        private const val MODEL_SPACING_Y = 0.3f
        private const val MODEL_SPACING_Z = 0.3f

        // Starting position offset from user (meters)
        private const val START_OFFSET_X = -1.0f
        private const val START_OFFSET_Y = 0.5f
        private const val START_OFFSET_Z = -2.0f

        // Model scale
        private const val MODEL_SCALE = 0.1f

        // Chicken model asset path
        private const val CHICKEN_MODEL_PATH = "models/chicken.glb"
    }

    private val loadedEntities = mutableListOf<GltfModelEntity>()
    private var chickenModel: GltfModel? = null

    /**
     * Load specified number of models and arrange them in a 3D grid
     * @param count Number of models to load
     * @param onProgress Callback with current loaded count
     */
    suspend fun loadModels(count: Int, onProgress: (Int) -> Unit) {
        Log.i(TAG, "Starting to load $count models...")
        val startTime = System.currentTimeMillis()

        withContext(Dispatchers.Main) {
            try {
                // Load the chicken model if not already loaded
                if (chickenModel == null) {
                    Log.d(TAG, "Loading chicken model from assets...")
                    chickenModel = loadChickenModel()

                    if (chickenModel == null) {
                        Log.e(TAG, "Failed to load chicken model, using procedural fallback")
                    }
                }

                // Calculate grid dimensions
                val gridSize = calculateGridDimensions(count)
                Log.d(TAG, "Grid dimensions: ${gridSize.x} x ${gridSize.y} x ${gridSize.z}")

                var loadedCount = 0

                // Create entities in a 3D grid pattern
                for (z in 0 until gridSize.z) {
                    for (y in 0 until gridSize.y) {
                        for (x in 0 until gridSize.x) {
                            if (loadedCount >= count) break

                            val position = Vector3(
                                START_OFFSET_X + (x * MODEL_SPACING_X),
                                START_OFFSET_Y + (y * MODEL_SPACING_Y),
                                START_OFFSET_Z + (z * MODEL_SPACING_Z)
                            )

                            val entity = createModelEntity(position, loadedCount)
                            if (entity != null) {
                                loadedEntities.add(entity)
                            }

                            loadedCount++
                            onProgress(loadedCount)

                            // Log progress every 10 models
                            if (loadedCount % 10 == 0) {
                                Log.d(TAG, "Loaded $loadedCount / $count models")
                            }
                        }
                        if (loadedCount >= count) break
                    }
                    if (loadedCount >= count) break
                }

                val endTime = System.currentTimeMillis()
                val duration = endTime - startTime

                Log.i(TAG, "========================================")
                Log.i(TAG, "Model loading complete!")
                Log.i(TAG, "Total models loaded: $loadedCount")
                Log.i(TAG, "Time taken: ${duration}ms")
                Log.i(TAG, "Average: ${if (loadedCount > 0) duration / loadedCount else 0}ms per model")
                Log.i(TAG, "========================================")

            } catch (e: Exception) {
                Log.e(TAG, "Error loading models: ${e.message}", e)
            }
        }
    }

    /**
     * Load the chicken GLB model from assets
     */
    private suspend fun loadChickenModel(): GltfModel? {
        return try {
            // Try to load from assets
            val model = GltfModel.create(session, CHICKEN_MODEL_PATH)
            Log.d(TAG, "Chicken model loaded successfully")
            model.await()
        } catch (e: Exception) {
            Log.w(TAG, "Could not load chicken model from assets: ${e.message}")
            Log.d(TAG, "Will use procedural geometry instead")
            null
        }
    }

    /**
     * Create a model entity at the specified position
     */
    private suspend fun createModelEntity(position: Vector3, index: Int): GltfModelEntity? {
        return try {
            val model = chickenModel
            if (model != null) {
                // Create entity from loaded model
                val entity = GltfModelEntity.create(session, model)

                // Set position using Pose
                val pose = Pose(
                    position,
                    androidx.xr.runtime.math.Quaternion(0f, 0f, 0f, 1f)
                )
                entity.setPose(pose)

                // Set scale
                entity.setScale(MODEL_SCALE)

                Log.v(TAG, "Created model entity #$index at (${position.x}, ${position.y}, ${position.z})")
                entity
            } else {
                // Create a simple placeholder if model loading failed
                createPlaceholderEntity(position, index)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error creating model entity #$index: ${e.message}")
            null
        }
    }

    /**
     * Create a placeholder entity when the main model is not available
     */
    private suspend fun createPlaceholderEntity(position: Vector3, index: Int): GltfModelEntity? {
        // In a real implementation, you might create a simple box or sphere here
        // For now, we'll try to create from an embedded simple model
        return try {
            // Try to load a built-in or simple placeholder model
            val placeholderModel = GltfModel.create(session, "models/placeholder.glb")
            val model = placeholderModel.await()
            val entity = GltfModelEntity.create(session, model)

            val pose = Pose(
                position,
                androidx.xr.runtime.math.Quaternion(0f, 0f, 0f, 1f)
            )
            entity.setPose(pose)
            entity.setScale(MODEL_SCALE)

            entity
        } catch (e: Exception) {
            Log.w(TAG, "Could not create placeholder entity: ${e.message}")
            null
        }
    }

    /**
     * Calculate grid dimensions for arranging models in 3D space
     * Tries to create a roughly cubic arrangement
     */
    private fun calculateGridDimensions(count: Int): GridDimensions {
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

        return GridDimensions(x, y, z)
    }

    /**
     * Clear all loaded models
     */
    fun clearAllModels() {
        Log.i(TAG, "Clearing ${loadedEntities.size} models...")

        loadedEntities.forEach { entity ->
            try {
                entity.dispose()
            } catch (e: Exception) {
                Log.e(TAG, "Error disposing entity: ${e.message}")
            }
        }
        loadedEntities.clear()

        Log.i(TAG, "All models cleared")
    }

    /**
     * Get the current number of loaded models
     */
    fun getLoadedModelCount(): Int = loadedEntities.size

    /**
     * Data class for grid dimensions
     */
    private data class GridDimensions(val x: Int, val y: Int, val z: Int)
}
