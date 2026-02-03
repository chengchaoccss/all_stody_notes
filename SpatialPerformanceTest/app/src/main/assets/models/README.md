# 3D Models Directory

## Required Model

Place your 3D model file here:
- **chicken.glb** - The main chicken model used for performance testing

## Model Requirements

1. **Format**: GLB (Binary glTF)
2. **Recommended polygon count**: 500-5000 triangles for performance testing
3. **Scale**: Model should be roughly 1 meter in size (will be scaled by the app)

## Getting Sample Models

You can download free GLB models from:
- [Sketchfab](https://sketchfab.com/) - Search for "chicken" and download GLB format
- [Google Poly](https://poly.pizza/) - Free low-poly models
- [Khronos glTF Sample Models](https://github.com/KhronosGroup/glTF-Sample-Models)

## Alternative: Create a Simple Model

If you don't have a chicken model, you can:
1. Use any GLB model and rename it to `chicken.glb`
2. Create a simple box/cube model using Blender and export as GLB
3. Use online tools like [https://www.creators3d.com/](https://www.creators3d.com/)

## Notes

- The app will log warnings if the model file is not found
- Performance testing results may vary based on model complexity
- Lower polygon models will allow loading more instances before frame rate drops
